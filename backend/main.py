import hashlib
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_db_connection
from ai_agent import analyze_transaction
from pdf_processor import extract_text_from_pdf

from google_sheets import append_transactions, init_sheet_headers, get_filtered_transactions, get_all_transactions

app = FastAPI(title="RockyMist-I FinMIS API", version="2.0.0")

# --- ON STARTUP ---
@app.on_event("startup")
def on_startup():
    try:
        init_sheet_headers()
        print("✅ Google Sheets initialized successfully")
    except Exception as e:
        print(f"⚠️ Failed to connect to Google Sheets on boot: {e}")

# Allow Frontend to communicate without CORS issues
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---
class LoginRequest(BaseModel):
    username: str
    password: str

class ManualEntryRequest(BaseModel):
    entry_date: str
    active_unit: str
    party: str
    dr_acc: str
    cr_acc: str
    amt: float
    desc: str
    user_id: str

class AIEntryRequest(BaseModel):
    user_input: str
    active_unit: str
    
class AIPostRequest(BaseModel):
    entry_date: str
    active_unit: str
    party: str
    dr_acc: str
    cr_acc: str
    amt: float
    desc: str
    user_id: str

# --- AUTHENTICATION ---
@app.post("/auth/login")
def login(creds: LoginRequest):
    p_hash = hashlib.sha256(creds.password.encode()).hexdigest()
    conn = get_db_connection()
    user = conn.execute("SELECT username, role FROM users WHERE username=? AND password=?", (creds.username, p_hash)).fetchone()
    conn.close()
    
    if user:
        return {"status": "success", "username": user["username"], "role": user["role"]}
    raise HTTPException(status_code=401, detail="Invalid Credentials")

# --- DATA HELPERS ---
@app.get("/data/coa")
def get_coa():
    conn = get_db_connection()
    rows = conn.execute("SELECT account_name FROM coa ORDER BY account_name").fetchall()
    conn.close()
    return {"coa": [r["account_name"] for r in rows]}

@app.get("/data/customers/{cc}")
def get_clients(cc: str):
    conn = get_db_connection()
    rows = conn.execute("SELECT customer_name FROM customers WHERE cost_center=?", (cc,)).fetchall()
    conn.close()
    base = ["General Guest", "Airbnb", "Instagram Ads"]
    return {"customers": base + [r["customer_name"] for r in rows]}

# --- MANUAL TRANSACTIONS ---
@app.post("/transactions/manual")
def post_manual_entry(req: ManualEntryRequest):
    try:
        rows = [
            [req.entry_date, req.active_unit, req.desc, req.dr_acc, req.party, req.amt, 0, "Manual", req.user_id],
            [req.entry_date, req.active_unit, req.desc, req.cr_acc, req.party, 0, req.amt, "Manual", req.user_id]
        ]
        append_transactions(rows)
        return {"status": "success", "message": "Manual Entry Saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- AI & PDF PROCESSING ---
@app.post("/transactions/ai/analyze")
def ai_analyze_transaction(req: AIEntryRequest):
    conn = get_db_connection()
    rows = conn.execute("SELECT account_name FROM coa").fetchall()
    valid_accounts = [r["account_name"] for r in rows]
    conn.close()
    
    res = analyze_transaction(req.user_input, req.active_unit, valid_accounts)
    if "error" in res:
         raise HTTPException(status_code=500, detail=res["error"])
    return res

@app.post("/transactions/ai/post")
def ai_post_transaction(req: AIPostRequest):
    try:
        rows = [
            [req.entry_date, req.active_unit, req.desc, req.dr_acc, req.party, req.amt, 0, "AI Cerebras", req.user_id],
            [req.entry_date, req.active_unit, req.desc, req.cr_acc, req.party, 0, req.amt, "AI Cerebras", req.user_id]
        ]
        append_transactions(rows)
        return {"status": "success"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@app.post("/transactions/pdf-sync")
async def pdf_sync(unit: str = Form(...), file: UploadFile = File(...)):
    """ Uploads a Bank PDF, Extracts text with pdfplumber, and pushes it through Cerebras AI """
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        raw_text = extract_text_from_pdf(temp_path)
        
        # In a generic AI sync, we feed the raw text directly to the agent to propose a batch of transactions.
        # But to prevent timeout and context limits, we instruct the AI to review it as one entity or extract key rows.
        # For this prototype we will ask the AI to summarize the overall statement intent.
        
        conn = get_db_connection()
        rows = conn.execute("SELECT account_name FROM coa").fetchall()
        valid_accs = [r["account_name"] for r in rows]
        conn.close()
        
        prompt = f"Analyze this bank statement: {raw_text[:2000]} (truncated). What is the total received vs sent? Return a JSON with an interpretation."
        
        # Reusing the agent, slightly modified conceptually context
        analysis = analyze_transaction(prompt, unit, valid_accs)
        
        os.remove(temp_path)
        return {"status": "success", "text_preview": raw_text[:500], "ai_analysis": analysis}
        
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

# --- REPORTS (Now powered by Google Sheets) ---
@app.get("/reports/journal")
def get_journal(start: str, end: str, unit: str):
    try:
        txns = get_filtered_transactions(start_date=start, end_date=end, cost_center=unit)
        journal = []
        for t in txns:
            journal.append({
                "date": t.get("Date", ""),
                "description": t.get("Description", ""),
                "account": t.get("Account", ""),
                "party": t.get("Party", ""),
                "debit": float(t.get("Debit", 0) or 0),
                "credit": float(t.get("Credit", 0) or 0),
                "source": t.get("Source", "")
            })
        return {"journal": journal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/cash")
def get_cash_in_hand(end: str):
    try:
        txns = get_filtered_transactions(end_date=end)
        balance = 0.0
        for t in txns:
            if t.get("Account", "") == "Cash in Hand":
                balance += float(t.get("Debit", 0) or 0) - float(t.get("Credit", 0) or 0)
        return {"cash_balance": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/pnl")
def get_pnl(start: str, end: str):
    try:
        conn = get_db_connection()
        inc_accs = [r["account_name"] for r in conn.execute("SELECT account_name FROM coa WHERE account_type='Income'").fetchall()]
        exp_accs = [r["account_name"] for r in conn.execute("SELECT account_name FROM coa WHERE account_type='Expense'").fetchall()]
        conn.close()
        
        txns = get_filtered_transactions(start_date=start, end_date=end)
        revenue = 0.0
        expenses = 0.0
        for t in txns:
            acc = t.get("Account", "")
            dr = float(t.get("Debit", 0) or 0)
            cr = float(t.get("Credit", 0) or 0)
            if acc in inc_accs:
                revenue += cr - dr
            elif acc in exp_accs:
                expenses += dr - cr
        
        return {"revenue": revenue, "expenses": expenses, "net": revenue - expenses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/recent")
def get_recent_transactions():
    """Returns the 20 most recent transactions from Google Sheets"""
    try:
        txns = get_all_transactions()
        recent = txns[-20:] if len(txns) > 20 else txns
        recent.reverse()
        return {"transactions": recent}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
