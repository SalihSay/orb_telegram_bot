"""Debug script v2 - check raw candle values"""
from binance_client import BinanceClient

client = BinanceClient()
candles_15m = client.get_klines('SOLUSDT', '15m', 100)

print('Checking candles around entry (IDX 64-70):')
for i in range(64, 75):
    c = candles_15m[i]
    h = c['high']
    l = c['low']
    cl = c['close']
    print(f"  IDX {i}: high={h:.4f}, low={l:.4f}, close={cl:.4f}")

# SL = 144.78 (center of ORB)
# For short: if high >= 144.78, SL hit
print("\nChecking if any candle high >= 144.78 (SL for short):")
sl = 144.78
for i in range(66, len(candles_15m)):  # Start from entry candle
    c = candles_15m[i]
    if c['high'] >= sl:
        print(f"  SL HIT at IDX {i}: high={c['high']:.4f} >= {sl}")
        break
else:
    print("  No SL hit found - position should still be open")
