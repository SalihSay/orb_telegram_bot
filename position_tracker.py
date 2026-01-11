"""
Position Tracker - Tracks active positions that user has entered
Uses SQLite for persistence
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path


class PositionTracker:
    def __init__(self, db_path: str = "positions.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                sl_price REAL NOT NULL,
                orb_high REAL,
                orb_low REAL,
                entry_time TEXT NOT NULL,
                confirmed INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS closed_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                close_price REAL NOT NULL,
                profit_percent REAL NOT NULL,
                close_type TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                close_time TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_signal(self, symbol: str, direction: str, entry_price: float, 
                   sl_price: float, orb_high: float = None, orb_low: float = None) -> int:
        """Add a new unconfirmed signal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO active_positions (symbol, direction, entry_price, sl_price, orb_high, orb_low, entry_time, confirmed)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (symbol, direction, entry_price, sl_price, orb_high, orb_low, datetime.now().isoformat()))
        
        position_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return position_id
    
    def confirm_position(self, symbol: str = None, position_id: int = None) -> bool:
        """Confirm user has entered the position"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if position_id:
            cursor.execute('UPDATE active_positions SET confirmed = 1 WHERE id = ?', (position_id,))
        elif symbol:
            cursor.execute('''
                UPDATE active_positions SET confirmed = 1 
                WHERE symbol = ? AND confirmed = 0 
                ORDER BY entry_time DESC LIMIT 1
            ''', (symbol,))
        else:
            # Confirm most recent unconfirmed position
            cursor.execute('''
                UPDATE active_positions SET confirmed = 1 
                WHERE confirmed = 0 
                ORDER BY entry_time DESC LIMIT 1
            ''')
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_confirmed_positions(self) -> List[Dict]:
        """Get all confirmed active positions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, direction, entry_price, sl_price, orb_high, orb_low, entry_time
            FROM active_positions WHERE confirmed = 1
        ''')
        
        positions = []
        for row in cursor.fetchall():
            positions.append({
                'id': row[0],
                'symbol': row[1],
                'direction': row[2],
                'entry_price': row[3],
                'sl_price': row[4],
                'orb_high': row[5],
                'orb_low': row[6],
                'entry_time': row[7]
            })
        
        conn.close()
        return positions
    
    def get_pending_signals(self) -> List[Dict]:
        """Get unconfirmed signals"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, direction, entry_price, sl_price, entry_time
            FROM active_positions WHERE confirmed = 0
        ''')
        
        signals = []
        for row in cursor.fetchall():
            signals.append({
                'id': row[0],
                'symbol': row[1],
                'direction': row[2],
                'entry_price': row[3],
                'sl_price': row[4],
                'entry_time': row[5]
            })
        
        conn.close()
        return signals
    
    def close_position(self, symbol: str, close_price: float, close_type: str = 'tp1') -> Optional[Dict]:
        """Close a position and move to history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find the position
        cursor.execute('''
            SELECT id, symbol, direction, entry_price, sl_price, entry_time
            FROM active_positions 
            WHERE symbol = ? AND confirmed = 1
            ORDER BY entry_time DESC LIMIT 1
        ''', (symbol,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        position_id, symbol, direction, entry_price, sl_price, entry_time = row
        
        # Calculate profit
        if direction == 'buy':
            profit_percent = ((close_price - entry_price) / entry_price) * 100
        else:
            profit_percent = ((entry_price - close_price) / entry_price) * 100
        
        # Move to closed positions
        cursor.execute('''
            INSERT INTO closed_positions 
            (symbol, direction, entry_price, close_price, profit_percent, close_type, entry_time, close_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, direction, entry_price, close_price, profit_percent, close_type, entry_time, datetime.now().isoformat()))
        
        # Remove from active
        cursor.execute('DELETE FROM active_positions WHERE id = ?', (position_id,))
        
        conn.commit()
        conn.close()
        
        return {
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'close_price': close_price,
            'profit_percent': profit_percent,
            'close_type': close_type
        }
    
    def cleanup_old_signals(self, hours: int = 24):
        """Remove old unconfirmed signals"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM active_positions 
            WHERE confirmed = 0 
            AND datetime(entry_time) < datetime('now', ?)
        ''', (f'-{hours} hours',))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*), SUM(profit_percent) FROM closed_positions WHERE profit_percent > 0')
        wins, win_profit = cursor.fetchone()
        wins = wins or 0
        win_profit = win_profit or 0
        
        cursor.execute('SELECT COUNT(*), SUM(profit_percent) FROM closed_positions WHERE profit_percent <= 0')
        losses, loss_amount = cursor.fetchone()
        losses = losses or 0
        loss_amount = loss_amount or 0
        
        cursor.execute('SELECT SUM(profit_percent) FROM closed_positions')
        total_profit = cursor.fetchone()[0] or 0
        
        conn.close()
        
        total_trades = wins + losses
        winrate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'winrate': winrate,
            'total_profit': total_profit
        }


# Test
if __name__ == "__main__":
    tracker = PositionTracker("test_positions.db")
    
    # Add a signal
    sig_id = tracker.add_signal('BTCUSDT', 'buy', 42000, 41500)
    print(f"Added signal ID: {sig_id}")
    
    # Confirm it
    tracker.confirm_position(position_id=sig_id)
    print("Confirmed position")
    
    # Get confirmed
    positions = tracker.get_confirmed_positions()
    print(f"Active positions: {positions}")
    
    # Close it
    result = tracker.close_position('BTCUSDT', 42500)
    print(f"Closed: {result}")
    
    # Stats
    stats = tracker.get_stats()
    print(f"Stats: {stats}")
