"""Quick test for ARB signal"""
from orb_algo import ORBAlgo
from binance_client import BinanceClient

c = BinanceClient()
algo = ORBAlgo()
r15 = c.get_klines("ARBUSDT", "15m", 100)
r30 = c.get_klines("ARBUSDT", "30m", 50)
t, d = algo.analyze(r15, r30)
print("Signal:", t)
print("Data:", d)
