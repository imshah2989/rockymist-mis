import sqlite3
import hashlib
import os

# --- PATH CONFIGURATION ---
DB_DIR = r"G:\My Drive\Obizworks Financial MIS"
DB_PATH = os.path.join(DB_DIR, "RockyMist_System.db")

def get_db_connection():
    global DB_PATH
    if not os.path.exists(DB_DIR):
        print(f"⚠️ Warning: G: Drive not found. Falling back to local database.")
        DB_PATH = os.path.join(os.getcwd(), "RockyMist_System.local.db")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        cost_center TEXT,
        description TEXT,
        account TEXT,
        party TEXT,
        debit REAL,
        credit REAL,
        source_tag TEXT,
        user_id TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS coa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_name TEXT UNIQUE,
        account_type TEXT,
        opening_balance REAL DEFAULT 0.0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        cost_center TEXT,
        type TEXT,
        opening_balance REAL DEFAULT 0.0,
        UNIQUE(customer_name, cost_center)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        email TEXT
    )''')

    # Seed Mandatory Hospitality Accounts
    heads = [
        ('Meezan Bank', 'Asset'), ('Payoneer (Airbnb)', 'Asset'), ('Cash in Hand', 'Asset'),
        ('Airbnb Revenue', 'Income'), ('Local/Social Revenue', 'Income'), ('Damage Recovery', 'Income'),
        ('Instagram Marketing', 'Expense'), ('Gas Cylinder Refills', 'Expense'), ('Sundry Items', 'Expense'),
        ('Maintenance - Winter', 'Expense'), ('Accounts Payable', 'Liability'), ('Accounts Receivable', 'Asset'),
        ('Punjab Sales Tax (PST)', 'Liability')
    ]
    for name, atype in heads:
        c.execute("INSERT OR IGNORE INTO coa (account_name, account_type) VALUES (?,?)", (name, atype))

    # Create Default Admin User
    hpw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password, role, email) VALUES (?,?,?,?)", 
              ('admin', hpw, 'Admin', 'admin@rockymist.com'))

    conn.commit()
    conn.close()

# Initialize upon import
try:
    init_db()
except Exception as e:
    print(f"Database initialization deferred/failed: {e}")
