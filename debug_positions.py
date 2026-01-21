import sqlite3
from datetime import datetime

def check_db():
    try:
        conn = sqlite3.connect('positions.db')
        cursor = conn.cursor()
        
        print("--- Active Positions ---")
        cursor.execute("SELECT * FROM positions WHERE status='open'")
        rows = cursor.fetchall()
        
        if not rows:
            print("No active positions.")
        else:
            for row in rows:
                print(row)
                
        print("\n--- INJUSDT History (Last 5) ---")
        try:
            cursor.execute("SELECT * FROM positions WHERE symbol='INJUSDT' ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
            if not rows:
                print("No history for INJUSDT.")
            for row in rows:
                print(row)
        except sqlite3.OperationalError:
            print("Could not query history (table might differ).")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
