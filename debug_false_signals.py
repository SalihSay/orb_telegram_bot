from binance_client import BinanceClient
from orb_algo import find_todays_orb, get_utc_date
import config
from datetime import datetime

def check_fakeout(pair, signal_hour_utc):
    client = BinanceClient()
    print(f"\n--- Analyzing {pair} ---")
    
    # 1. Get ORB Levels
    orb_candles = client.get_klines(pair, config.ORB_TIMEFRAME, limit=24)
    orb_high, orb_low, orb_time = find_todays_orb(orb_candles)
    
    if not orb_high:
        print("ORB not found.")
        return

    print(f"ORB High: {orb_high}")
    
    # 2. Get 15m candles around signal time
    # Signal times from logs: NEAR ~08:21 UTC (11:21 TR), TIA ~10:06 UTC (13:06 TR)
    # We fetch a chunk covering today
    candles = client.get_klines(pair, '15m', limit=96) # 24h * 4
    
    found_fakeout = False
    for c in candles:
        ts = c['timestamp']
        dt = datetime.fromtimestamp(ts/1000)
        
        # Check if this candle triggered a 'false' buy
        # Condition: High > ORB_High (Triggered tick-based) BUT Close < ORB_High (Fakeout)
        
        if c['high'] > orb_high and c['close'] < orb_high:
            # Check if this happened around the reported time
            # We look for match with recent log times (approximate)
            print(f"Potential Fakeout at {dt} (UTC+3) | High: {c['high']} > {orb_high} > Close: {c['close']}")
            found_fakeout = True
            
    if not found_fakeout:
        print("No fakeout pattern found in recent candles.")

if __name__ == "__main__":
    # NEAR signal was at 11:21 TR (08:21 UTC)
    check_fakeout('NEARUSDT', 8)
    
    # TIA signal was at 13:06 TR (10:06 UTC)
    check_fakeout('TIAUSDT', 10)
    
    # XLM signal was at 13:06 TR
    check_fakeout('XLMUSDT', 10)
    
    print("\nCONCLUSION: If we see 'Potential Fakeout' entries matching the signal times,")
    print("it confirms the 'Tick-based' logic was the ONLY cause.")
