from binance_client import BinanceClient
from orb_algo import find_todays_orb, get_utc_date
import config

def debug_chz_sl():
    client = BinanceClient()
    pair = 'CHZUSDT'
    
    print(f"--- Debugging {pair} SL ---")
    
    # 1. Fetch ORB Candles
    orb_candles = client.get_klines(pair, config.ORB_TIMEFRAME, limit=24)
    print(f"Fetched {len(orb_candles)} candles (1h)")
    
    # 2. Find ORB
    orb_high, orb_low, orb_time = find_todays_orb(orb_candles)
    
    if not orb_high:
        print("ORB Not Found.")
        return
        
    print(f"ORB High: {orb_high}")
    print(f"ORB Low:  {orb_low}")
    
    # 3. Calculate SL for all methods (Assuming LONG signal as per user)
    center = (orb_high + orb_low) / 2.0
    print(f"Center:   {center:.6f}")
    
    # For Long Signal:
    # Safer: Between Center and High
    sl_safer = (center + orb_high) / 2.0
    # Balanced: Center
    sl_balanced = center
    # Risky: Between Center and Low
    sl_risky = (center + orb_low) / 2.0
    
    print(f"\n--- Calculated SL (LONG) ---")
    print(f"Safer:    {sl_safer:.6f}")
    print(f"Balanced: {sl_balanced:.6f}  <-- Current Config")
    print(f"Risky:    {sl_risky:.6f}")
    
    print(f"\nUser Reported Bot SL: 0.0522")
    print(f"User Reported TV SL:  0.05321")
    
    # Check matching
    print("\n--- Match Analysis ---")
    if abs(sl_balanced - 0.0522) < 0.0001:
        print("Bot is correctly using 'Balanced'.")
    elif abs(sl_risky - 0.0522) < 0.0001:
        print("Bot seems to be using 'Risky'!")
    else:
        print("Bot SL does not match any standard calc. Check data source.")
        
    if abs(sl_safer - 0.05321) < 0.0001:
        print("TV seems to be using 'Safer'.")
    elif abs(sl_balanced - 0.05321) < 0.0001:
        print("TV seems to be using 'Balanced'.")
    else:
        print("TV SL match unclear.")

if __name__ == "__main__":
    debug_chz_sl()
