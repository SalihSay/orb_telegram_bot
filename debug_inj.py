from binance_client import BinanceClient
from orb_algo import find_todays_orb, get_utc_date
import config
from datetime import datetime

def debug_inj_orb():
    client = BinanceClient()
    pair = 'INJUSDT'
    
    print(f"--- Debugging {pair} ---")
    
    # Fetch ORB Candles (1h)
    orb_candles = client.get_klines(pair, config.ORB_TIMEFRAME, limit=24)
    print(f"Fetched {len(orb_candles)} ORB candles ({config.ORB_TIMEFRAME})")
    
    # Find Today's ORB
    orb_high, orb_low, orb_time = find_todays_orb(orb_candles)
    
    if orb_high:
        print(f"[+] ORB Found for today (UTC Date: {get_utc_date(orb_candles[-1]['timestamp'])})")
        print(f"ORB Start Time (Timestamp): {orb_time}")
        print(f"ORB Start Time (Date): {datetime.fromtimestamp(orb_time/1000)}")
        print(f"ORB High: {orb_high}")
        print(f"ORB Low: {orb_low}")
        
        # Check if user's levels match ANY candle
        print(f"\nUser provided levels -> High: 4.594 | Low: 4.483")
        
        print("\n--- Candle Dump (Last 12 Hours) ---")
        for c in orb_candles[-12:]:
            ts = c['timestamp']
            dt = datetime.fromtimestamp(ts/1000)
            date_str = get_utc_date(ts)
            print(f"Time: {dt} | H: {c['high']} | L: {c['low']} | C: {c['close']}")
            if ts == orb_time:
                print("   <-- THIS IS THE DETECTED ORB CANDLE")
                
    else:
        print("[-] ORB NOT Found for today!")

if __name__ == "__main__":
    debug_inj_orb()
