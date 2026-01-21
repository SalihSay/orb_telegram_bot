import sqlite3
from datetime import datetime

def check_db():
    try:
        conn = sqlite3.connect('positions.db')
        cursor = conn.cursor()
        
        print("--- Active Positions ---")
        try:
            cursor.execute("SELECT * FROM active_positions")
            rows = cursor.fetchall()
            
            if not rows:
                print("No active positions.")
            else:
                for row in rows:
                    print(row)
        except sqlite3.OperationalError as e:
            print(f"Error querying active_positions: {e}")
            
        print("\n--- INJUSDT History (active + closed) ---")
        try:
            print("Active:")
            cursor.execute("SELECT * FROM active_positions WHERE symbol='INJUSDT'")
            rows = cursor.fetchall()
            if not rows:
                print("No active INJ position.")
            for row in rows:
                print(row)
                
            print("Closed (Last 5):")
            cursor.execute("SELECT * FROM closed_positions WHERE symbol='INJUSDT' ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
            if not rows:
                print("No closed history for INJUSDT.")
            for row in rows:
                print(row)
        except sqlite3.OperationalError as e:
            print(f"Error querying history: {e}")
            
        conn.close()
    except Exception as e:
        print(f"Database connection error: {e}")

if __name__ == "__main__":
    check_db()
