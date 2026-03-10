import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import json
import os
import shutil
import re
import pdfplumber
import time
from openai import OpenAI
from datetime import datetime

# --- 1. CORE CONFIG & AUTO-BACKUP ---
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
        st.session_state.last_backup = datetime.now().strftime("%b %d, %Y - %H:%M")
        return True
    except: return False

# --- 2. DATABASE INIT ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, cost_center TEXT, description TEXT, account TEXT, party TEXT, debit REAL, credit REAL, source_tag TEXT, user_id TEXT, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS coa (id INTEGER PRIMARY KEY AUTOINCREMENT, account_name TEXT UNIQUE, account_type TEXT, opening_balance REAL DEFAULT 0.0)''')
    conn.commit(); conn.close()

init_db()

# --- 3. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'ai_buffer' not in st.session_state: st.session_state.ai_buffer = None
if 'bank_df' not in st.session_state: st.session_state.bank_df = None

# --- 4. AUTHENTICATION ---
if not st.session_state.logged_in:
    st.title("🏔️ RockyMist-I Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Access System"):
        if u == "admin" and p == "admin123":
            st.session_state.logged_in = True; st.rerun()
    st.stop()

# --- 5. DATA HELPERS ---
def get_coa():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT account_name FROM coa ORDER BY account_name", conn)
    conn.close(); return df['account_name'].tolist()

def post_entry(v_list):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.executemany("INSERT INTO ledger (date, cost_center, description, account, party, debit, credit, source_tag, user_id, notes) VALUES (?,?,?,?,?,?,?,?,?,?)", v_list)
    conn.commit(); conn.close(); perform_auto_backup()

# --- 6. UI LAYOUT ---
st.sidebar.title("🏔️ RockyMist-I")
perform_auto_backup()
st.sidebar.info(f"💾 Last Backup: {st.session_state.get('last_backup', 'Pending')}")
active_unit = st.sidebar.selectbox("Unit", ["Penthouse Dream", "Apartment 1", "Apartment 2"])

t_entry, t_bank, t_reports, t_inv, t_admin = st.tabs(["➕ Entry", "🏦 Bank Sync", "📊 Reports", "🧾 Invoicing", "⚙️ Admin"])

# --- MODULE 1: ENTRY MODULE (RESTORED AI SMART ENTRY) ---
with t_entry:
    m_ai, m_man, m_pdf = st.tabs(["🧠 AI Smart Entry", "📝 Manual Entry", "📄 PDF Receipts"])
    
    with m_ai:
        st.subheader("🧠 Intelligence-Driven Posting")
        raw_text = st.text_area("Describe the transaction (English):", 
                                placeholder="e.g. Received 50,000 from Airbnb for 3 nights in Penthouse Dream.", 
                                height=100)
        
        c1, c2 = st.columns([1, 5])
        if c1.button("🔍 AI Analyze"):
            if raw_text:
                coa_list = get_coa()
                prompt = f"System: RockyMist-I Financial MIS. Context: {active_unit}. Valid COA: {coa_list}. Task: Analyze '{raw_text}'. Identify: Description, Party, Dr Account, Cr Account, Amount, Source (Airbnb/Local). Return JSON ONLY."
                try:
                    resp = client.chat.completions.create(model="qwen2.5:3b", messages=[{"role": "user", "content": prompt}])
                    # Clean response and parse
                    clean_resp = resp.choices[0].message.content.strip().replace('```json', '').replace('```', '')
                    st.session_state.ai_buffer = json.loads(clean_resp)
                    st.rerun()
                except Exception as e: st.error(f"AI Connection Error: {e}")
        
        if c2.button("🧹 Clear Entry"):
            st.session_state.ai_buffer = None; st.rerun()

        # Render AI Results if Buffer is Full
        if st.session_state.ai_buffer:
            res = st.session_state.ai_buffer
            st.divider()
            st.markdown(f"### **AI Analysis Outcome**")
            st.info(f"**Interpretation:** {res.get('description', 'Parsed')} transaction involving **{res.get('party', 'Unknown')}** for **PKR {res.get('amt', 0):,.2f}**.")
            
            with st.form("ai_confirmation_form"):
                col_a, col_b = st.columns(2)
                f_party = col_a.text_input("Verified Party/Client", value=res.get('party', ''))
                f_desc = col_b.text_input("Verified Description", value=res.get('description', ''))
                f_dr = col_a.selectbox("Debit (Target)", get_coa(), index=get_coa().index(res['dr']) if res.get('dr') in get_coa() else 0)
                f_cr = col_b.selectbox("Credit (Source)", get_coa(), index=get_coa().index(res['cr']) if res.get('cr') in get_coa() else 0)
                f_amt = st.number_input("Confirmed Amount (PKR)", value=float(res.get('amt', 0)))
                f_src = st.selectbox("Revenue Source", ["Airbnb/Payoneer", "Local/Social Media", "Instagram Ads", "Personal"], 
                                    index=0 if "Airbnb" in res.get('source', '') else 1)
                
                if st.form_submit_button("🗳️ Post AI Entry to Ledger"):
                    dt = datetime.now().strftime("%Y-%m-%d")
                    post_entry([
                        (dt, active_unit, f_desc, f_dr, f_party, f_amt, 0, f_src, "admin", ""),
                        (dt, active_unit, f_desc, f_cr, f_party, 0, f_amt, f_src, "admin", "")
                    ])
                    st.session_state.ai_buffer = None
                    st.success("✅ AI Transaction Posted Successfully!")
                    time.sleep(1); st.rerun()

    with m_man:
        with st.form("man_f", clear_on_submit=True):
            c1, c2 = st.columns(2)
            dt = c1.date_input("Date")
            p = c1.selectbox("Party/Client", ["Airbnb", "Local Guest", "Instagram Vendor", "Personal stay"])
            dr = c1.selectbox("Debit (Target Account)", get_coa())
            cr = c2.selectbox("Credit (Source Account)", get_coa())
            amt = c2.number_input("Amount (PKR)", min_value=0.0)
            desc = st.text_input("Short Narration")
            if st.form_submit_button("Post Manual Entry"):
                post_entry([(dt.strftime("%Y-%m-%d"), active_unit, desc, dr, p, amt, 0, "Manual", "admin", ""),
                            (dt.strftime("%Y-%m-%d"), active_unit, desc, cr, p, 0, amt, "Manual", "admin", "")])
                st.success("Manual Entry Posted!")

    with m_pdf:
        st.subheader("📄 Receipt PDF Processing")
        up_rec = st.file_uploader("Upload Receipt PDF", type="pdf")
        if up_rec:
            with pdfplumber.open(up_rec) as pdf:
                txt = "".join([pg.extract_text() for pg in pdf.pages])
                amt_m = re.search(r"(?:PKR|Rs\.?)\s?([\d,.]+)", txt)
                amt_found = float(amt_m.group(1).replace(",", "")) if amt_m else 0.0
                st.write(f"**Detected Amount:** {amt_found} PKR")
                if st.button("Stage Receipt for AI"):
                    st.session_state.ai_buffer = {'description': "Bill payment", 'party': "Vendor", 'dr': 'Sundry Items', 'cr': 'Cash in Hand', 'amt': amt_found, 'source': 'Local'}
                    st.rerun()

# --- TAB: BANK SYNC (NO CHANGES) ---
with t_bank:
    st.header("🏦 Bank Statement AI Sync")
    up_bank = st.file_uploader("Upload Statement PDF", type="pdf")
    if up_bank:
        if st.button("Extract Data"):
            data = []
            with pdfplumber.open(up_bank) as pdf:
                for pg in pdf.pages:
                    matches = re.findall(r"(\d{2}[a-zA-Z]{3} \d{4})\s+(.*?)\s*(?:\s+|-\s+|\+\s+)PKR([\d,.]+)", pg.extract_text())
                    for m in matches: data.append({"Date": m[0], "Details": m[1], "Amount": float(m[2].replace(',', ''))})
            st.session_state.bank_df = pd.DataFrame(data)
        if st.session_state.bank_df is not None:
            st.table(st.session_state.bank_df)

# --- TAB: REPORTS (NO CHANGES) ---
with t_reports:
    c1, c2, c3 = st.columns([2,1,1])
    rep = c1.selectbox("Report Type", ["General Journal", "Cash Flow", "ABN Revenue"])
    sd = c2.date_input("Start Date", value=datetime(2025,1,1))
    ed = c3.date_input("End Date")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM ledger WHERE date BETWEEN ? AND ?", conn, params=(sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d")))
    st.dataframe(df, use_container_width=True)
    conn.close()

# --- TAB: INVOICING (NO CHANGES) ---
with t_inv:
    st.subheader("🧾 Hospitality Invoicing")
    inv_guest = st.text_input("Client Name")
    inv_amt = st.number_input("Base Rent", min_value=0.0)
    if st.button("Generate Final Invoice"):
        st.write(f"### Invoice: {inv_guest} | Total: PKR {inv_amt:,.2f}")

# --- TAB: ADMIN (NO CHANGES) ---
with t_admin:
    st.header("⚙️ Admin COA")
    with st.form("add_c"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Account")
        t = c2.selectbox("Type", ["Asset", "Liability", "Revenue", "Expense"])
        b = c3.number_input("Balance")
        if st.form_submit_button("Add Account"):
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("INSERT INTO coa (account_name, account_type, opening_balance) VALUES (?,?,?)", (n, t, b))
            conn.commit(); conn.close(); st.rerun()
    conn = sqlite3.connect(DB_PATH)
    st.table(pd.read_sql_query("SELECT account_name, account_type, opening_balance FROM coa", conn))
    conn.close()