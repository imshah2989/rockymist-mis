import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
import json
import os
import shutil
from openai import OpenAI
from datetime import datetime

# --- 1. CORE SYSTEM CONFIGURATION ---
st.set_page_config(page_title="RockyMist-I Financial MIS", layout="wide")
DB_PATH = r"G:\My Drive\Obizworks Financial MIS\RockyMist_System.db"
BACKUP_DIR = r"E:\Obizworks\MIS Finance\Backups"
client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")

# --- 2. SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'ai_buffer' not in st.session_state: st.session_state.ai_buffer = None
if 'last_backup' not in st.session_state: st.session_state.last_backup = "Pending"

# --- 3. DATABASE SCHEMA INTEGRITY ---
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, cost_center TEXT, description TEXT, account TEXT, party TEXT, debit REAL, credit REAL, source_tag TEXT, user_id TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS coa (id INTEGER PRIMARY KEY AUTOINCREMENT, account_name TEXT UNIQUE, account_type TEXT, opening_balance REAL DEFAULT 0.0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, cost_center TEXT, type TEXT, opening_balance REAL DEFAULT 0.0, UNIQUE(customer_name, cost_center))''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, email TEXT)''')
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database Initialization Error: {e}")

init_db()

# --- 4. AUTHENTICATION MODULE ---
if not st.session_state.logged_in:
    st.title("🏔️ RockyMist-I Financial MIS")
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Access System"):
            hp = hashlib.sha256(p.encode()).hexdigest()
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, hp))
            res = c.fetchone()
            conn.close()
            if res:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid Username or Password")
    st.stop()

# --- 5. SYSTEM HEADER & AUTO-BACKUP ---
st.title("🏔️ RockyMist-I Financial MIS")
try:
    if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, f"RockyMist_DB_{ts}.db"))
    st.session_state.last_backup = datetime.now().strftime("%Y-%m-%d %H:%M")
except Exception:
    pass

st.sidebar.title(f"👤 {st.session_state.user}")
active_unit = st.sidebar.selectbox("Active Unit", ["RockyMist_I", "RockyMist_II", "Penthouse_Dream"])
st.sidebar.info(f"📂 Last Backup: {st.session_state.last_backup}")

# --- 6. DATA HELPERS ---
def get_coa():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT account_name FROM coa ORDER BY account_name", conn)
    conn.close()
    return df['account_name'].tolist()

def get_custs(cc):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT customer_name FROM customers WHERE cost_center=?", conn, params=(cc,))
    conn.close()
    return ["General Guest", "Airbnb", "Instagram Ads"] + df['customer_name'].tolist()

# --- 7. UI TABS ---
t_entry, t_reports, t_inv, t_admin = st.tabs(["➕ Entry", "📊 Reports", "🧾 Invoicing", "⚙️ Admin"])

# --- TAB: ENTRY ---
with t_entry:
    entry_date = st.date_input("Transaction Date", value=datetime.now())
    m_ai, m_manual = st.tabs(["🧠 AI Smart Entry", "📝 Manual Entry"])
    
    with m_ai:
        u_input = st.text_area("Describe transaction (e.g., Received 10k from guest via IBFT):")
        if st.button("🔍 Analyze Transaction"):
            coa_list = get_coa()
            prompt = f"Unit: {active_unit}. Input: '{u_input}'. Valid Accounts: {coa_list}. Return JSON with keys: description, party, dr, cr, amt, outcome."
            try:
                resp = client.chat.completions.create(model="qwen2.5:3b", messages=[{"role": "user", "content": prompt}])
                st.session_state.ai_buffer = json.loads(resp.choices[0].message.content.strip().replace('```json', '').replace('```', ''))
                st.rerun()
            except Exception as e:
                st.error(f"AI Logic Error: {e}")
        
        if st.session_state.ai_buffer:
            res = st.session_state.ai_buffer
            st.success(f"**Interpretation:** {res.get('outcome', 'Analysis Complete')}")
            if st.button("🗳️ Post AI Entry"):
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                date_str = entry_date.strftime("%Y-%m-%d")
                v = [(date_str, active_unit, res['description'], res['dr'], res['party'], res['amt'], 0, 'AI', st.session_state.user),
                     (date_str, active_unit, res['description'], res['cr'], res['party'], 0, res['amt'], 'AI', st.session_state.user)]
                c.executemany("INSERT INTO ledger (date,cost_center,description,account,party,debit,credit,source_tag,user_id) VALUES (?,?,?,?,?,?,?,?,?)", v)
                conn.commit()
                conn.close()
                st.session_state.ai_buffer = None
                st.success("Entry Posted to G: Drive!")
                time.sleep(1)
                st.rerun()

    with m_manual:
        with st.form("manual_form"):
            c1, c2 = st.columns(2)
            party = c1.selectbox("Party/Client", get_custs(active_unit))
            dr_acc = c1.selectbox("Debit (Increase Asset/Expense)", get_coa())
            cr_acc = c2.selectbox("Credit (Increase Revenue/Liability)", get_coa())
            amt = c2.number_input("Amount (PKR)", min_value=0.0)
            desc = st.text_input("Transaction Details")
            if st.form_submit_button("Post Transaction"):
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                date_str = entry_date.strftime("%Y-%m-%d")
                v = [(date_str, active_unit, desc, dr_acc, party, amt, 0, "Manual", st.session_state.user),
                     (date_str, active_unit, desc, cr_acc, party, 0, amt, "Manual", st.session_state.user)]
                c.executemany("INSERT INTO ledger (date,cost_center,description,account,party,debit,credit,source_tag,user_id) VALUES (?,?,?,?,?,?,?,?,?)", v)
                conn.commit()
                conn.close()
                st.success("Manual Entry Saved!")
                time.sleep(1)
                st.rerun()

# --- TAB: REPORTS (DEBUGGED INDENTATION) ---
with t_reports:
    st.subheader("📊 Financial Reporting")
    r_choice = st.selectbox("Select Report", ["General Journal", "Cash in Hand", "P&L Summary"])
    col_s, col_e = st.columns(2)
    s_date = col_s.date_input("Start Date", value=datetime(2025, 1, 1))
    e_date = col_e.date_input("End Date", value=datetime.now())
    
    conn = sqlite3.connect(DB_PATH)
    if r_choice == "General Journal":
        query = "SELECT date, description, account, debit, credit, party FROM ledger WHERE date BETWEEN ? AND ? AND cost_center=? ORDER BY date DESC"
        df = pd.read_sql_query(query, conn, params=(s_date.strftime("%Y-%m-%d"), e_date.strftime("%Y-%m-%d"), active_unit))
        st.dataframe(df, use_container_width=True)
    elif r_choice == "Cash in Hand":
        query = "SELECT SUM(debit-credit) as balance FROM ledger WHERE account='Cash in Hand' AND date <= ?"
        res = pd.read_sql_query(query, conn, params=(e_date.strftime("%Y-%m-%d"),))
        current_bal = res['balance'][0] if res['balance'][0] else 0.0
        st.metric("Total Cash Position", f"PKR {current_bal:,.2f}")
    elif r_choice == "P&L Summary":
        st.write("Fetching Profit & Loss data...")
        inc = pd.read_sql_query("SELECT SUM(credit-debit) as val FROM ledger WHERE account IN (SELECT account_name FROM coa WHERE account_type='Income') AND date BETWEEN ? AND ?", conn, params=(s_date.strftime("%Y-%m-%d"), e_date.strftime("%Y-%m-%d")))
        exp = pd.read_sql_query("SELECT SUM(debit-credit) as val FROM ledger WHERE account IN (SELECT account_name FROM coa WHERE account_type='Expense') AND date BETWEEN ? AND ?", conn, params=(s_date.strftime("%Y-%m-%d"), e_date.strftime("%Y-%m-%d")))
        rev = inc['val'][0] if inc['val'][0] else 0
        cost = exp['val'][0] if exp['val'][0] else 0
        st.metric("Net Profit/Loss", f"PKR {rev - cost:,.2f}", delta=f"Revenue: {rev:,.0f}")
    conn.close()

# --- TAB: INVOICING ---
with t_inv:
    st.subheader("🧾 Quick Invoice (Tax Compliant)")
    with st.form("invoice_gen"):
        cust = st.selectbox("Guest", get_custs(active_unit))
        base = st.number_input("Base Rent", min_value=0.0)
        tax = st.checkbox("Apply 16% Punjab Sales Tax")
        if st.form_submit_button("Preview Invoice"):
            total = base * 1.16 if tax else base
            st.info(f"Draft Invoice for {cust}: Total PKR {total:,.2f} (Base: {base:,.0f} + Tax: {total-base:,.0f})")

# --- TAB: ADMIN ---
with t_admin:
    st.subheader("⚙️ Chart of Accounts Control")
    conn = sqlite3.connect(DB_PATH)
    df_coa = pd.read_sql_query("SELECT * FROM coa", conn)
    st.dataframe(df_coa, use_container_width=True)
    conn.close()
    if st.button("🔧 Force Database Integrity Check"):
        init_db()
        st.success("Schema synchronized.")