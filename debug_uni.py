from binance_client import BinanceClient
from orb_algo import find_todays_orb, calculate_ema
import config

def debug_uni():
    client = BinanceClient()
    pair = 'UNIUSDT'
    
    print(f"=== Debugging {pair} TP1 ===")
    
    # Get candles
    candles_15m = client.get_klines(pair, '15m', limit=50)
    candles_orb = client.get_klines(pair, config.ORB_TIMEFRAME, limit=24)
    
    # Filter closed only
    closed_15m = [c for c in candles_15m if c['is_closed']]
    closed_orb = [c for c in candles_orb if c['is_closed']]
    
    # ORB
    orb_high, orb_low, _ = find_todays_orb(closed_orb)
    print(f"ORB High: {orb_high}")
    print(f"ORB Low:  {orb_low}")
    center = (orb_high + orb_low) / 2.0
    print(f"SL (Balanced): {center}")
    
    # EMA
    hl2 = [(c['high'] + c['low']) / 2 for c in closed_15m]
    ema_values = calculate_ema(hl2, config.EMA_LENGTH)
    
    # Last few candles
    print("\n--- Last 5 Closed 15m Candles ---")
    for i in range(-5, 0):
        c = closed_15m[i]
        ema = ema_values[len(ema_values) + i]
        from datetime import datetime
        ts = datetime.fromtimestamp(c['timestamp']/1000)
        
        print(f"{ts} | Close: {c['close']:.4f} | EMA: {ema:.4f} | High: {c['high']:.4f} | Low: {c['low']:.4f}")
        
        # Check TP1 condition for SHORT
        # TP1 for short: close > ema (crossback)
        if c['close'] > ema:
            print(f"  --> TP1 Crossback detected! (close {c['close']:.4f} > ema {ema:.4f})")

if __name__ == "__main__":
    debug_uni()
