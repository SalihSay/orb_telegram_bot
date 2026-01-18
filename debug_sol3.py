"""Debug the real ORBAlgo class"""
from orb_algo import ORBAlgo, find_todays_orb, get_utc_date, calculate_ema, calculate_atr
from binance_client import BinanceClient
import config

client = BinanceClient()
candles_15m = client.get_klines('SOLUSDT', '15m', 100)
candles_30m = client.get_klines('SOLUSDT', '30m', 50)

# Replicate exact algo logic
algo = ORBAlgo()

if len(candles_15m) < 50 or len(candles_30m) < 10:
    print("Not enough candles")
    exit()

orb_high, orb_low, orb_start_time = find_todays_orb(candles_30m)
if orb_high is None:
    print("No ORB found")
    exit()

today = get_utc_date(candles_15m[-1]['timestamp'])
orb_end_time = orb_start_time + (30 * 60 * 1000)

today_candles = []
for i, candle in enumerate(candles_15m):
    if get_utc_date(candle['timestamp']) == today and candle['timestamp'] >= orb_end_time:
        today_candles.append((i, candle))

hl2 = [(c['high'] + c['low']) / 2 for c in candles_15m]
ema_values = calculate_ema(hl2, algo.ema_length)
atr_values = calculate_atr(candles_15m)

print(f"ORB: high={orb_high}, low={orb_low}")
print(f"Today candles: {len(today_candles)}")
print(f"ATR values length: {len(atr_values)}")
print(f"EMA values length: {len(ema_values)}")

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
    
    condition_price = ema if algo.breakout_condition == 'EMA' else close
    
    if state == 'waiting':
        if condition_price > orb_high:
            state = 'in_breakout'
            breakout_bullish = True
            breakout_start_idx = idx
            retests = 0
        elif condition_price < orb_low:
            state = 'in_breakout'
            breakout_bullish = False
            breakout_start_idx = idx
            retests = 0
    
    elif state == 'in_breakout':
        if breakout_bullish and close < orb_high:
            state = 'waiting'
            breakout_bullish = None
            retests = 0
        elif not breakout_bullish and close > orb_low:
            state = 'waiting'
            breakout_bullish = None
            retests = 0
        else:
            if idx > breakout_start_idx:
                if breakout_bullish and close > orb_high and low < orb_high:
                    retests += 1
                elif not breakout_bullish and close < orb_low and high > orb_low:
                    retests += 1
            
            if retests >= algo.retests_needed:
                state = 'entry_taken'
                center = (orb_high + orb_low) / 2.0
                if algo.sl_method == 'Balanced':
                    sl_price = center
                else:
                    sl_price = center
                
                entry_data = {
                    'direction': 'buy' if breakout_bullish else 'sell',
                    'entry_price': close,
                    'sl_price': sl_price,
                    'orb_high': orb_high,
                    'orb_low': orb_low,
                    'entry_index': idx
                }
                print(f"\n*** ENTRY FOUND at IDX {idx} ***")
                print(f"    Direction: {entry_data['direction']}")
                print(f"    Entry: {entry_data['entry_price']}, SL: {entry_data['sl_price']}")
    
    elif state == 'entry_taken':
        entry_price = entry_data['entry_price']
        current_sl = entry_data['sl_price']
        is_long = entry_data['direction'] == 'buy'
        
        # ATR for this candle
        atr_idx = idx - 12  # ATR starts at index 12
        if atr_idx >= 0 and atr_idx < len(atr_values):
            current_atr = atr_values[atr_idx]
        else:
            current_atr = atr_values[-1] if atr_values else 0
        
        is_profitable = (is_long and ema > entry_price) or (not is_long and ema < entry_price)
        ema_profit = abs(ema - entry_price) / entry_price * 100
        
        # Trailing stop
        if is_profitable and ema_profit >= algo.minimum_profit_percent:
            if is_long:
                new_sl = ema - current_atr * 0.5
                if new_sl > current_sl:
                    entry_data['sl_price'] = new_sl
                    current_sl = new_sl
            else:
                new_sl = ema + current_atr * 0.5
                if new_sl < current_sl:
                    old_sl = current_sl
                    entry_data['sl_price'] = new_sl
                    current_sl = new_sl
                    print(f"  [IDX {idx}] Trailing SL: {old_sl:.4f} -> {new_sl:.4f}")
        
        # Check SL hit
        if is_long and low <= current_sl:
            print(f"  [IDX {idx}] SL HIT (long): low={low} <= sl={current_sl}")
            entry_data = None
            state = 'closed'
        elif not is_long and high >= current_sl:
            print(f"  [IDX {idx}] SL HIT (short): high={high} >= sl={current_sl}")
            entry_data = None
            state = 'closed'

print(f"\n=== FINAL ===")
print(f"State: {state}")
print(f"Entry data: {entry_data}")
if entry_data and state == 'entry_taken':
    print("RESULT: Would return 'entry' signal")
else:
    print("RESULT: Would return None")
