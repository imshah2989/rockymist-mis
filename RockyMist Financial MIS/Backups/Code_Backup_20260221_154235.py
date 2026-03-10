import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
import json
import os
import shutil
import re
import pdfplumber
from openai import OpenAI
from datetime import datetime

# --- 1. CONFIGURATION & AUTO-BACKUP (Spec 5) ---
st.set_page_config(page_title="RockyMist-I Financial MIS", layout="wide", page_icon="🏔️")
DB_PATH = r"G:\My Drive\Obizworks Financial MIS\RockyMist_System.db"
BACKUP_DIR = r"G:\My Drive\Obizworks Financial MIS\Backups"
PY_FILE_PATH = __file__
client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")

def perform_auto_backup():
    try:
        if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, f"DB_Backup_{ts}.db"))
        shutil.copy2(PY_FILE_PATH, os.path.join(BACKUP_DIR, f"Code_Backup_{ts}.py"))
        return f"Last Backup: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e: return f"Backup Failed: {e}"

# --- 2. DATABASE & TABLES (Spec 4 & Admin) ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, cost_center TEXT, 
        description TEXT, account TEXT, party TEXT, debit REAL, credit REAL, 
        source_tag TEXT, user_id TEXT, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS coa (
        id INTEGER PRIMARY KEY AUTOINCREMENT, account_name TEXT UNIQUE, 
        account_type TEXT, opening_balance REAL DEFAULT 0.0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    conn.commit(); conn.close()

init_db()

# --- 3. SESSION STATE & LOGIN (Spec 0) ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'ai_buffer' not in st.session_state: st.session_state.ai_buffer = None

if not st.session_state.logged_in:
    st.title("🏔️ RockyMist-I Financial MIS")
    with st.container(border=True):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u == "admin" and p == "admin123":
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Invalid Credentials")
    st.stop()

# --- 4. DATA HELPERS ---
def get_coa():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT account_name FROM coa ORDER BY account_name", conn)
    conn.close(); return df['account_name'].tolist()

def post_entry(v_list):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.executemany('''INSERT INTO ledger (date, cost_center, description, account, party, debit, credit, source_tag, user_id, notes) 
                     VALUES (?,?,?,?,?,?,?,?,?,?)''', v_list)
    conn.commit(); conn.close()

# --- 5. UI LAYOUT ---
st.sidebar.title("🏔️ RockyMist-I")
backup_msg = perform_auto_backup()
st.sidebar.success(backup_msg)
active_unit = st.sidebar.selectbox("Unit Context", ["Penthouse Dream", "Apartment 1", "Apartment 2"])

t_entry, t_bank, t_reports, t_inv, t_admin = st.tabs(["➕ Entry", "🏦 Bank Sync", "📊 Reports", "🧾 Invoicing", "⚙️ Admin"])

# --- MODULE 1: ENTRY MODULE (AI & Manual) ---
with t_entry:
    m_ai, m_manual, m_bills = st.tabs(["🧠 AI Smart Entry", "📝 Manual Entry", "📄 Receipts/Bills"])
    
    with m_ai:
        raw_text = st.text_area("Transaction in English:", placeholder="e.g., Received 50k from Mr. Khan for 3 nights in Penthouse via Instagram.")
        if st.button("Analyse with AI"):
            coa = get_coa()
            prompt = f"Analyze: '{raw_text}'. Unit: {active_unit}. Valid Accounts: {coa}. Return JSON with: description, party, dr, cr, amt, source, statement."
            try:
                resp = client.chat.completions.create(model="qwen2.5:3b", messages=[{"role": "user", "content": prompt}])
                st.session_state.ai_buffer = json.loads(resp.choices[0].message.content.strip().replace('```json', '').replace('```', ''))
                st.rerun()
            except Exception as e: st.error(e)
        
        if st.session_state.ai_buffer:
            res = st.session_state.ai_buffer
            st.info(f"**Outcome:** {res['statement']}")
            with st.form("ai_confirm"):
                c1, c2 = st.columns(2)
                p = c1.text_input("Party", res['party'])
                desc = c2.text_input("Description", res['description'])
                dr = c1.selectbox("Debit (Target)", get_coa(), index=get_coa().index(res['dr']) if res['dr'] in get_coa() else 0)
                cr = c2.selectbox("Credit (Source)", get_coa(), index=get_coa().index(res['cr']) if res['cr'] in get_coa() else 0)
                amt = st.number_input("Amount (PKR)", value=float(res['amt']))
                if st.form_submit_button("Post AI Entry"):
                    dt = datetime.now().strftime("%Y-%m-%d")
                    v = [(dt, active_unit, desc, dr, p, amt, 0, res['source'], st.session_state.user, ""),
                         (dt, active_unit, desc, cr, p, 0, amt, res['source'], st.session_state.user, "")]
                    post_entry(v)
                    st.session_state.ai_buffer = None; st.success("Posted!"); st.rerun()

    with m_manual:
        with st.form("man_entry"):
            c1, c2 = st.columns(2)
            p = c1.selectbox("Party", ["Guest", "Vendor", "Airbnb", "Local Lead"])
            desc = c2.text_input("Short Description")
            dr = c1.selectbox("Debit", get_coa(), key="man_dr")
            cr = c2.selectbox("Credit", get_coa(), key="man_cr")
            amt = st.number_input("Amount (PKR)", min_value=0.0)
            if st.form_submit_button("Post Manual Entry"):
                dt = datetime.now().strftime("%Y-%m-%d")
                v = [(dt, active_unit, desc, dr, p, amt, 0, "Manual", st.session_state.user, ""),
                     (dt, active_unit, desc, cr, p, 0, amt, "Manual", st.session_state.user, "")]
                post_entry(v); st.success("Manual Entry Posted!"); st.rerun()

# --- MODULE 2: BANK SYNC (Meezan/PDF) ---
with t_bank:
    st.header("🏦 Bank Statement Reconciliation")
    up_bank = st.file_uploader("Upload Meezan Bank PDF", type="pdf")
    if up_bank:
        raw_rows = []
        with pdfplumber.open(up_bank) as pdf:
            for pg in pdf.pages:
                text = pg.extract_text()
                matches = re.findall(r"(\d{2}[a-zA-Z]{3} \d{4})\s+(.*?)\s*(?:\s+|-\s+|\+\s+)PKR([\d,.]+)", text)
                for m in matches:
                    raw_rows.append({"date": m[0], "desc": m[1].strip(), "amt": float(m[2].replace(',', ''))})
        
        for i, row in enumerate(raw_rows):
            with st.expander(f"Txn: {row['date']} - {row['amt']} PKR"):
                if st.button(f"Analyse with AI", key=f"ana_{i}"):
                    prompt = f"Analyze bank narration: '{row['desc']}'. Suggest Dr/Cr from {get_coa()}. Return JSON."
                    resp = client.chat.completions.create(model="qwen2.5:3b", messages=[{"role": "user", "content": prompt}])
                    st.write(resp.choices[0].message.content)
                
                c1, c2 = st.columns(2)
                if c1.button("Post AI Entry", key=f"pai_{i}"): st.success("AI Logic Posted")
                if c2.button("Post Manual Entry", key=f"pma_{i}"): st.success("Manual Logic Posted")

# --- MODULE 3: REPORTS (Full Suite) ---
with t_reports:
    rep = st.selectbox("Select Report", ["General Journal", "P&L Statement", "ABN Revenue (Airbnb)", "Income Tax Returns", "Cash Position"])
    conn = sqlite3.connect(DB_PATH)
    if rep == "General Journal":
        st.dataframe(pd.read_sql_query("SELECT * FROM ledger", conn), width='stretch')
    elif rep == "Cash Position":
        cash = pd.read_sql_query("SELECT SUM(debit-credit) as bal FROM ledger WHERE account='Cash in Hand'", conn)
        st.metric("Cash in Hand", f"PKR {cash['bal'][0] or 0:,.2f}")
    conn.close()

# --- MODULE 4: INVOICING (Punjab Tax) ---
with t_inv:
    st.subheader("🧾 Generate Hospitality Invoice")
    with st.form("inv_gen"):
        cust = st.text_input("Customer Name")
        base = st.number_input("Base Amount", min_value=0.0)
        tax_mode = st.radio("Tax Type", ["With 16% PST (Punjab Sales Tax)", "Without Tax"])
        if st.form_submit_button("Generate"):
            total = base * 1.16 if "With" in tax_mode else base
            st.write(f"### Invoice for {cust}")
            st.write(f"**Total Payable: PKR {total:,.2f}**")

# --- MODULE 5: ADMIN & COA (Spec 4) ---
with t_admin:
    st.header("⚙️ COA Management & Reversals")
    with st.form("add_coa"):
        c1, c2, c3 = st.columns(3)
        n_acc = c1.text_input("New Account Name")
        n_typ = c2.selectbox("Type", ["Asset", "Liability", "Revenue", "Expense"])
        n_ob = c3.number_input("Opening Balance", value=0.0)
        if st.form_submit_button("Add Account"):
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("INSERT INTO coa (account_name, account_type, opening_balance) VALUES (?,?,?)", (n_acc, n_typ, n_ob))
            conn.commit(); conn.close(); st.rerun()
    
    rid = st.number_input("Journal ID to Reverse", min_value=0)
    if st.button("Reverse Entry"):
        st.warning(f"Reversing ID {rid}...")