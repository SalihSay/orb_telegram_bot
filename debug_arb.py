"""Debug ARB signal"""
from binance_client import BinanceClient
from orb_algo import ORBAlgo, find_todays_orb, get_utc_date, calculate_ema
from datetime import datetime, timezone, timedelta

client = BinanceClient()
algo = ORBAlgo()

# ARB check
candles_15m = client.get_klines('ARBUSDT', '15m', limit=100)
candles_30m = client.get_klines('ARBUSDT', '30m', limit=50)

if candles_15m and candles_30m:
    # Get ORB
    orb_high, orb_low, orb_start = find_todays_orb(candles_30m)
    print(f'ORB: High={orb_high:.4f}, Low={orb_low:.4f}')
    
    # Check EMA
    hl2 = [(c['high'] + c['low']) / 2 for c in candles_15m]
    ema_values = calculate_ema(hl2, 13)
    
    # Check last few candles
    for i in range(-5, 0):
        c = candles_15m[i]
        ema = ema_values[i]
        ts = datetime.fromtimestamp(c['timestamp']/1000, tz=timezone.utc) + timedelta(hours=3)
        print(f'{ts.strftime("%H:%M")}: Close={c["close"]:.4f}, EMA={ema:.4f}, High={c["high"]:.4f}, Low={c["low"]:.4f}')
        print(f'   EMA > ORB_High: {ema > orb_high}, EMA < ORB_Low: {ema < orb_low}')
    
    # Check signal
    signal_type, signal_data = algo.analyze(candles_15m, candles_30m)
    print(f'\nSignal: {signal_type}')
    if signal_data:
        print(f'Data: {signal_data}')
