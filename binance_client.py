"""
Binance Client - Fetches candlestick data from Binance API
"""
import requests
from datetime import datetime
from typing import List, Dict, Optional


class BinanceClient:
    BASE_URL = "https://api.binance.com/api/v3"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict]:
        """
        Fetch candlestick data from Binance
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (e.g., '15m', '30m', '1h')
            limit: Number of candles to fetch
            
        Returns:
            List of candle dictionaries with open, high, low, close, volume
        """
        endpoint = f"{self.BASE_URL}/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            raw_data = response.json()
            
            candles = []
            for candle in raw_data:
                candles.append({
                    'timestamp': candle[0],
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]),
                    'close_time': candle[6],
                    'is_closed': True if candle[6] < datetime.now().timestamp() * 1000 else False
                })
            
            return candles
            
        except requests.RequestException as e:
            print(f"Error fetching data for {symbol}: {e}")
            return []
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        endpoint = f"{self.BASE_URL}/ticker/price"
        params = {'symbol': symbol}
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data['price'])
        except requests.RequestException as e:
            print(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_server_time(self) -> int:
        """Get Binance server time"""
        endpoint = f"{self.BASE_URL}/time"
        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()['serverTime']
        except requests.RequestException:
            return int(datetime.now().timestamp() * 1000)


# Test
if __name__ == "__main__":
    client = BinanceClient()
    candles = client.get_klines('BTCUSDT', '15m', limit=5)
    for c in candles:
        print(f"Close: {c['close']}, High: {c['high']}, Low: {c['low']}")
