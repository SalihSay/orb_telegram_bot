import sqlite3
import pandas as pd
from datetime import datetime

def check_db():
    conn = sqlite3.connect('positions.db')
    cursor = conn.cursor()
    
    print("--- Active Positions ---")
    cursor.execute("SELECT * FROM positions WHERE status='open'")
    rows = cursor.fetchall()
    
    if not rows:
        print("No active positions.")
    else:
        for row in rows:
            # Table structure assumes: id, symbol, entry_price, direction, sl_price, tp1_price, start_time, status, ...
            # Let's inspect columns first to be safe
            print(row)
            
    print("\n--- INJUSDT History (Last 5) ---")
    cursor.execute("SELECT * FROM positions WHERE symbol='INJUSDT' ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check_db()
