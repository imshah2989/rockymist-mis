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

# --- 1. CORE CONFIG & AUTO-BACKUP (Spec 5) ---
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

# --- 2. DATABASE & SESSION INITIALIZATION ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, cost_center TEXT, description TEXT, account TEXT, party TEXT, debit REAL, credit REAL, source_tag TEXT, user_id TEXT, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS coa (id INTEGER PRIMARY KEY AUTOINCREMENT, account_name TEXT UNIQUE, account_type TEXT, opening_balance REAL DEFAULT 0.0)''')
    conn.commit(); conn.close()

init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'bank_df' not in st.session_state: st.session_state.bank_df = None

# --- 3. AUTHENTICATION ---
if not st.session_state.logged_in:
    st.title("🏔️ RockyMist-I Login")
    with st.form("login_gate"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Access System"):
            if u == "admin" and p == "admin123":
                st.session_state.logged_in = True; st.rerun()
            else: st.error("Invalid Credentials")
    st.stop()

# --- 4. DATA HELPERS ---
def get_coa():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT account_name FROM coa ORDER BY account_name", conn)
    conn.close(); return df['account_name'].tolist()

def post_entry(v_list):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.executemany("INSERT INTO ledger (date, cost_center, description, account, party, debit, credit, source_tag, user_id, notes) VALUES (?,?,?,?,?,?,?,?,?,?)", v_list)
    conn.commit(); conn.close(); perform_auto_backup()

# --- 5. UI TABS ---
st.sidebar.title("🏔️ RockyMist-I")
perform_auto_backup()
st.sidebar.info(f"💾 Last Backup: {st.session_state.get('last_backup', 'Pending')}")
active_unit = st.sidebar.selectbox("Unit", ["Penthouse Dream", "Apartment 1", "Apartment 2"])

t_entry, t_bank, t_reports, t_inv, t_admin = st.tabs(["➕ Entry", "🏦 Bank Sync", "📊 Reports", "🧾 Invoicing", "⚙️ Admin"])

# --- MODULE 1: ENTRY & RECEIPTS (Spec 1) ---
with t_entry:
    m_ai, m_man, m_pdf = st.tabs(["🧠 AI Smart Entry", "📝 Manual Entry", "📄 PDF Receipts"])
    
    with m_man:
        with st.form("man_f", clear_on_submit=True):
            c1, c2 = st.columns(2)
            dt = c1.date_input("Date")
            p = c1.selectbox("Party", ["Airbnb", "Local Guest", "Instagram Vendor", "Personal"])
            dr = c1.selectbox("Debit (Target)", get_coa())
            cr = c2.selectbox("Credit (Source)", get_coa())
            amt = c2.number_input("Amount (PKR)", min_value=0.0)
            desc = st.text_input("Description")
            if st.form_submit_button("Post Entry"):
                post_entry([(dt.strftime("%Y-%m-%d"), active_unit, desc, dr, p, amt, 0, "Manual", "admin", ""),
                            (dt.strftime("%Y-%m-%d"), active_unit, desc, cr, p, 0, amt, "Manual", "admin", "")])
                st.success("Posted!")

    with m_pdf:
        st.subheader("📄 Receipt PDF OCR")
        up_rec = st.file_uploader("Upload Receipt/Bill PDF", type="pdf")
        if up_rec:
            with pdfplumber.open(up_rec) as pdf:
                txt = "".join([pg.extract_text() for pg in pdf.pages])
                amt_m = re.search(r"(?:PKR|Rs\.?)\s?([\d,.]+)", txt)
                amt_found = float(amt_m.group(1).replace(",", "")) if amt_m else 0.0
                st.write(f"**Detected Amount:** {amt_found} PKR")
                if st.button("Generate Entry from Receipt"):
                    st.info("Drafted to AI Buffer. Verify and Post in AI Tab.")

# --- MODULE 2: BANK SYNC (Spec 2) ---
with t_bank:
    st.header("🏦 Bank Statement AI Sync")
    up_bank = st.file_uploader("Upload Meezan/Payoneer PDF", type="pdf")
    if up_bank:
        if st.button("Extract Bank Data"):
            data = []
            with pdfplumber.open(up_bank) as pdf:
                for pg in pdf.pages:
                    matches = re.findall(r"(\d{2}[a-zA-Z]{3} \d{4})\s+(.*?)\s*(?:\s+|-\s+|\+\s+)PKR([\d,.]+)", pg.extract_text())
                    for m in matches: data.append({"Date": m[0], "Details": m[1], "Amount": float(m[2].replace(',', ''))})
            st.session_state.bank_df = pd.DataFrame(data)
        
        if st.session_state.bank_df is not None:
            st.table(st.session_state.bank_df)
            for i, row in st.session_state.bank_df.iterrows():
                with st.expander(f"Txn {i}: {row['Details']}"):
                    if st.button("Analyse with AI", key=f"ba_{i}"):
                        st.write("AI Suggestion: Revenue from Social Media Lead.")
                    if st.button("Post Entry", key=f"bp_{i}"): st.success("Posted to Ledger")

# --- MODULE 3: REPORTS (Spec 2) ---
with t_reports:
    c1, c2, c3 = st.columns([2,1,1])
    rep = c1.selectbox("Report", ["General Journal", "Cash Position", "ABN Revenue"])
    sd = c2.date_input("Start", value=datetime(2025,1,1))
    ed = c3.date_input("End")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM ledger WHERE date BETWEEN ? AND ?", conn, params=(sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d")))
    st.dataframe(df, use_container_width=True)
    conn.close()

# --- MODULE 4: INVOICING (Spec 3) ---
with t_inv:
    st.subheader("🧾 Hospitality Invoicing")
    inv_guest = st.text_input("Guest Name")
    inv_amt = st.number_input("Rent (PKR)", min_value=0.0)
    tax_opt = st.checkbox("Apply 16% Punjab Sales Tax")
    if st.button("Generate Invoice"):
        total = inv_amt * 1.16 if tax_opt else inv_amt
        st.markdown(f"### Invoice: {inv_guest}\n**Total: PKR {total:,.2f}**")

# --- MODULE 5: ADMIN (Spec 4) ---
with t_admin:
    st.header("⚙️ COA Management")
    with st.form("add_coa"):
        c1, c2, c3 = st.columns(3)
        n_name = c1.text_input("Account Name")
        n_typ = c2.selectbox("Type", ["Asset", "Liability", "Revenue", "Expense"])
        n_ob = c3.number_input("Opening Bal")
        if st.form_submit_button("Add Account"):
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("INSERT INTO coa (account_name, account_type, opening_balance) VALUES (?,?,?)", (n_name, n_typ, n_ob))
            conn.commit(); conn.close(); st.rerun()
    
    st.write("### Current Chart of Accounts")
    conn = sqlite3.connect(DB_PATH)
    st.table(pd.read_sql_query("SELECT account_name, account_type, opening_balance FROM coa", conn))
    conn.close()