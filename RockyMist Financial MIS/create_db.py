import sqlite3
import hashlib
import os

# --- PATH CONFIGURATION ---
DB_DIR = r"G:\My Drive\Obizworks Financial MIS"
DB_PATH = os.path.join(DB_DIR, "RockyMist_System.db")

def create_system():
    # Ensure the directory exists
    if not os.path.exists(DB_DIR):
        print(f"❌ Error: Directory not found: {DB_DIR}")
        print("Please create the folder in Google Drive first.")
        return

    print(f"🏗️  Creating database at: {DB_PATH}...")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Ledger Table (Transactions)
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

    # 2. Chart of Accounts (COA)
    c.execute('''CREATE TABLE IF NOT EXISTS coa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_name TEXT UNIQUE,
        account_type TEXT,
        opening_balance REAL DEFAULT 0.0
    )''')

    # 3. Customers/Vendors Table
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        cost_center TEXT,
        type TEXT,
        opening_balance REAL DEFAULT 0.0,
        UNIQUE(customer_name, cost_center)
    )''')

    # 4. Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        email TEXT
    )''')

    # 5. Seed Mandatory Hospitality Accounts
    heads = [
        ('Meezan Bank', 'Asset'), ('Payoneer (Airbnb)', 'Asset'), ('Cash in Hand', 'Asset'),
        ('Airbnb Revenue', 'Income'), ('Local/Social Revenue', 'Income'), ('Damage Recovery', 'Income'),
        ('Instagram Marketing', 'Expense'), ('Gas Cylinder Refills', 'Expense'), ('Sundry Items', 'Expense'),
        ('Maintenance - Winter', 'Expense'), ('Accounts Payable', 'Liability'), ('Accounts Receivable', 'Asset'),
        ('Punjab Sales Tax (PST)', 'Liability')
    ]
    for name, atype in heads:
        c.execute("INSERT OR IGNORE INTO coa (account_name, account_type) VALUES (?,?)", (name, atype))

    # 6. Create Default Admin User (Password: admin123)
    hpw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password, role, email) VALUES (?,?,?,?)", 
              ('admin', hpw, 'Admin', 'admin@rockymist.com'))

    conn.commit()
    conn.close()
    print("✅ Database created and initialized successfully!")

if __name__ == "__main__":
    create_system()