"""Detailed debug for ARB signal - trace all states"""
from binance_client import BinanceClient
from orb_algo import find_todays_orb, get_utc_date, calculate_ema
from datetime import datetime, timezone, timedelta
import config

client = BinanceClient()

# ARB check
candles_15m = client.get_klines('ARBUSDT', '15m', limit=100)
candles_30m = client.get_klines('ARBUSDT', '30m', limit=50)

if candles_15m and candles_30m:
    # Get ORB
    orb_high, orb_low, orb_start_time = find_todays_orb(candles_30m)
    orb_end_time = orb_start_time + (30 * 60 * 1000)
    
    orb_start_dt = datetime.fromtimestamp(orb_start_time/1000, tz=timezone.utc) + timedelta(hours=3)
    print(f'ORB Start: {orb_start_dt.strftime("%H:%M")}')
    print(f'ORB: High={orb_high:.4f}, Low={orb_low:.4f}')
    print()
    
    # Get today's date
    today = get_utc_date(candles_15m[-1]['timestamp'])
    
    # Calculate EMA
    hl2 = [(c['high'] + c['low']) / 2 for c in candles_15m]
    ema_values = calculate_ema(hl2, config.EMA_LENGTH)
    
    # Filter today's candles after ORB
    today_candles = []
    for i, candle in enumerate(candles_15m):
        if get_utc_date(candle['timestamp']) == today and candle['timestamp'] >= orb_end_time:
            today_candles.append((i, candle))
    
    # Simulate algo state machine
    state = 'waiting'
    breakout_bullish = None
    breakout_start_idx = None
    retests = 0
    entry_data = None
    
    print(f"{'Time':<8} {'Close':<10} {'EMA':<10} {'CondPrice':<12} {'State':<15} {'Retests':<8}")
    print("-" * 75)
    
    for idx, candle in today_candles:
        ema = ema_values[idx]
        close = candle['close']
        high = candle['high']
        low = candle['low']
        
        ts = datetime.fromtimestamp(candle['timestamp']/1000, tz=timezone.utc) + timedelta(hours=3)
        time_str = ts.strftime("%H:%M")
        
        condition_price = ema  # Using EMA
        old_state = state
        
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
            # Check for failed breakout
            if breakout_bullish and close < orb_high:
                state = 'waiting'
                breakout_bullish = None
                retests = 0
            elif not breakout_bullish and close > orb_low:
                state = 'waiting'
                breakout_bullish = None
                retests = 0
            else:
                # Check for retest
                if idx > breakout_start_idx:
                    if breakout_bullish and close > orb_high and low < orb_high:
                        retests += 1
                    elif not breakout_bullish and close < orb_low and high > orb_low:
                        retests += 1
                
                # Check entry condition
                if retests >= config.RETESTS_NEEDED:
                    state = 'entry_taken'
                    entry_data = {
                        'direction': 'buy' if breakout_bullish else 'sell',
                        'entry_price': close,
                        'candle_time': candle['timestamp']
                    }
        
        # Print state
        cond_vs_orb = f"{'>' if condition_price > orb_high else '<' if condition_price < orb_low else '='}"
        print(f"{time_str:<8} {close:<10.4f} {ema:<10.4f} {cond_vs_orb}ORB          {state:<15} {retests if state != 'waiting' else '-':<8}")
        
        if old_state != state:
            if state == 'in_breakout':
                print(f"   ^ BREAKOUT {'BULLISH' if breakout_bullish else 'BEARISH'} started!")
            elif state == 'entry_taken':
                print(f"   ^ ENTRY TAKEN: {entry_data['direction'].upper()}")
            elif state == 'waiting' and old_state == 'in_breakout':
                print(f"   ^ BREAKOUT FAILED")
    
    print()
    if entry_data:
        print(f"Final: {entry_data}")
    else:
        print("No entry signal found")
