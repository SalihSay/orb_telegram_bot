"""Debug script for SOL/USDT signal"""
from orb_algo import ORBAlgo, find_todays_orb, get_utc_date, calculate_ema, calculate_atr
from binance_client import BinanceClient
import config

client = BinanceClient()
candles_15m = client.get_klines('SOLUSDT', '15m', 100)
candles_30m = client.get_klines('SOLUSDT', '30m', 50)

# Debug info
print('=== DEBUG SOL/USDT ===')
print(f"Last 15m candle time: {candles_15m[-1]['timestamp']}")
print(f"Last 15m candle date: {get_utc_date(candles_15m[-1]['timestamp'])}")

orb_high, orb_low, orb_start = find_todays_orb(candles_30m)
print(f"ORB: high={orb_high}, low={orb_low}")

today = get_utc_date(candles_15m[-1]['timestamp'])
orb_end_time = orb_start + (30 * 60 * 1000)

today_candles = []
for i, candle in enumerate(candles_15m):
    if get_utc_date(candle['timestamp']) == today and candle['timestamp'] >= orb_end_time:
        today_candles.append((i, candle))

print(f"Today candles count: {len(today_candles)}")
if today_candles:
    print(f"First today candle index: {today_candles[0][0]}")
    print(f"Last today candle index: {today_candles[-1][0]}")

# Check breakout detection
hl2 = [(c['high'] + c['low']) / 2 for c in candles_15m]
ema_values = calculate_ema(hl2, config.EMA_LENGTH)

print(f"\nLast EMA: {ema_values[-1]:.4f}")
print(f"ORB Low: {orb_low}")
print(f"Last close: {candles_15m[-1]['close']}")
print(f"Close < ORB Low? {candles_15m[-1]['close'] < orb_low}")

# Simulate the algo
print("\n=== SIMULATING SIGNAL DETECTION ===")
state = 'waiting'
breakout_bullish = None
breakout_start_idx = None
retests = 0
entry_data = None

for idx, candle in today_candles:
    ema = ema_values[idx]
    close = candle['close']
    high = candle['high']
    low = candle['low']
    
    condition_price = close  # Using Close condition
    
    if state == 'waiting':
        if condition_price > orb_high:
            state = 'in_breakout'
            breakout_bullish = True
            breakout_start_idx = idx
            retests = 0
            print(f"  [IDX {idx}] Bullish breakout started")
        elif condition_price < orb_low:
            state = 'in_breakout'
            breakout_bullish = False
            breakout_start_idx = idx
            retests = 0
            print(f"  [IDX {idx}] Bearish breakout started")
    
    elif state == 'in_breakout':
        if breakout_bullish and close < orb_high:
            print(f"  [IDX {idx}] Breakout FAILED (close {close} < orb_high {orb_high})")
            state = 'waiting'
            breakout_bullish = None
            retests = 0
        elif not breakout_bullish and close > orb_low:
            print(f"  [IDX {idx}] Breakout FAILED (close {close} > orb_low {orb_low})")
            state = 'waiting'
            breakout_bullish = None
            retests = 0
        else:
            if idx > breakout_start_idx:
                if breakout_bullish and close > orb_high and low < orb_high:
                    retests += 1
                    print(f"  [IDX {idx}] Bullish retest #{retests}")
                elif not breakout_bullish and close < orb_low and high > orb_low:
                    retests += 1
                    print(f"  [IDX {idx}] Bearish retest #{retests}")
            
            if retests >= config.RETESTS_NEEDED:
                # Calculate SL
                center = (orb_high + orb_low) / 2.0
                sl_price = center  # Balanced
                
                print(f"  [IDX {idx}] ENTRY! Direction: {'BUY' if breakout_bullish else 'SELL'}")
                print(f"       Entry price: {close}, SL: {sl_price}")
                state = 'entry_taken'
                entry_data = {
                    'direction': 'buy' if breakout_bullish else 'sell',
                    'entry_price': close,
                    'sl_price': sl_price,
                    'entry_index': idx
                }
    
    elif state == 'entry_taken':
        # TRAILING STOP SIMULATION
        entry_price = entry_data['entry_price']
        current_sl = entry_data['sl_price']
        is_long = entry_data['direction'] == 'buy'
        current_atr = 0.5  # Approximate
        
        is_profitable = (is_long and ema > entry_price) or (not is_long and ema < entry_price)
        ema_profit = abs(ema - entry_price) / entry_price * 100
        
        # Check SL hit
        if is_long and low <= current_sl:
            print(f"  [IDX {idx}] SL HIT (long): low={low} <= sl={current_sl}")
            entry_data = None
            state = 'closed'
        elif not is_long and high >= current_sl:
            print(f"  [IDX {idx}] SL HIT (short): high={high} >= sl={current_sl}")
            entry_data = None
            state = 'closed'
        else:
            print(f"  [IDX {idx}] Position open, high={high:.2f}, sl={current_sl:.2f}")

print(f"\n=== FINAL STATE ===")
print(f"State: {state}")
print(f"Entry data: {entry_data}")
