import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1NOASJHIs1AhRBOZCCaXckKx77nTDPsYkbybZRLkfFYo'

# Path to the credentials file
CREDS_PATH = os.path.join(os.getcwd(), "credentials.json")

def get_sheets_service():
    if not os.path.exists(CREDS_PATH):
        raise FileNotFoundError(f"Credentials not found at {CREDS_PATH}")
    
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def init_sheet_headers():
    """ Ensures the active sheet has the correct Ledger headers """
    service = get_sheets_service()
    
    # Check if headers exist by reading the first row
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1!A1:I1'
    ).execute()
    
    values = result.get('values', [])
    
    if not values:
        # Sheet is completely empty, let's write the headers
        headers = [["Date", "Cost Center", "Description", "Account", "Party", "Debit", "Credit", "Source", "User"]]
        body = {'values': headers}
        
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!A1:I1',
            valueInputOption='RAW',
            body=body
        ).execute()

def append_transactions(rows: list):
    """
    Appends a list of rows to the bottom of the Google Sheet.
    rows should be a list of lists: [[col1, col2, ...], [col1, col2, ...]]
    """
    service = get_sheets_service()
    body = {'values': rows}
    
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1!A:I',
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()


def get_all_transactions():
    """
    Reads ALL rows from the Google Sheet and returns them as a list of dicts.
    Headers: Date, Cost Center, Description, Account, Party, Debit, Credit, Source, User
    """
    service = get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1!A:I'
    ).execute()
    
    values = result.get('values', [])
    if len(values) <= 1:
        return []  # Only headers or empty
    
    headers = values[0]
    transactions = []
    for row in values[1:]:
        # Pad row if it has fewer columns than headers
        while len(row) < len(headers):
            row.append('')
        record = dict(zip(headers, row))
        transactions.append(record)
    
    return transactions


def get_filtered_transactions(start_date=None, end_date=None, cost_center=None):
    """
    Reads transactions from Google Sheets and filters by date range and/or cost center.
    Dates should be in 'YYYY-MM-DD' format.
    """
    all_txns = get_all_transactions()
    filtered = []
    
    for txn in all_txns:
        txn_date = txn.get('Date', '')
        txn_cc = txn.get('Cost Center', '')
        
        # Date filtering
        if start_date and txn_date < start_date:
            continue
        if end_date and txn_date > end_date:
            continue
        # Cost center filtering
        if cost_center and txn_cc != cost_center:
            continue
        
        filtered.append(txn)
    
    return filtered
