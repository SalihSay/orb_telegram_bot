"""
ORB Algo Strategy Implementation
Stateless version - analyzes complete history each scan
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import config


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return [prices[0]] * len(prices)
    
    ema = []
    multiplier = 2 / (period + 1)
    sma = sum(prices[:period]) / period
    ema.append(sma)
    
    for i in range(1, len(prices)):
        if i < period:
            ema.append(sum(prices[:i+1]) / (i+1))
        else:
            ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    
    return ema


def calculate_atr(candles: List[Dict], period: int = 12) -> List[float]:
    """Calculate Average True Range"""
    if len(candles) < 2:
        return [0.0]
    
    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i-1]['close']
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    atr = []
    if len(true_ranges) >= period:
        first_atr = sum(true_ranges[:period]) / period
        atr.append(first_atr)
        
        multiplier = 2 / (period + 1)
        for i in range(period, len(true_ranges)):
            new_atr = (true_ranges[i] - atr[-1]) * multiplier + atr[-1]
            atr.append(new_atr)
    else:
        atr = [sum(true_ranges) / len(true_ranges)] * len(true_ranges) if true_ranges else [0]
    
    return atr


def get_utc_date(timestamp_ms: int) -> str:
    """Get UTC date string from timestamp"""
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date().isoformat()


def find_todays_orb(candles_30m: List[Dict]) -> Tuple[Optional[float], Optional[float], Optional[int]]:
    """
    Find today's ORB (Opening Range).
    Returns the first 30m candle's high/low for today.
    """
    if not candles_30m:
        return None, None, None
    
    # Get today's date from the last candle
    last_candle = candles_30m[-1]
    today = get_utc_date(last_candle['timestamp'])
    
    # Find first candle of today
    for candle in candles_30m:
        if get_utc_date(candle['timestamp']) == today:
            return candle['high'], candle['low'], candle['timestamp']
    
    return None, None, None


class ORBAlgo:
    """
    Stateless ORB Algo - analyzes complete history each scan
    """
    def __init__(self):
        self.ema_length = config.EMA_LENGTH
        self.retests_needed = config.RETESTS_NEEDED
        self.breakout_condition = config.BREAKOUT_CONDITION
        self.sl_method = config.SL_METHOD
        self.minimum_profit_percent = config.MINIMUM_PROFIT_PERCENT
    
    def analyze(self, candles_15m: List[Dict], candles_30m: List[Dict]) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Analyze all candles and find if there's a new entry signal.
        This is stateless - analyzes complete history each time.
        """
        if len(candles_15m) < 50 or len(candles_30m) < 10:
            return None, None
        
        # Get today's ORB
        orb_high, orb_low, orb_start_time = find_todays_orb(candles_30m)
        if orb_high is None:
            return None, None
        
        # Get today's date
        today = get_utc_date(candles_15m[-1]['timestamp'])
        
        # Filter candles to only today's candles AFTER ORB period
        orb_end_time = orb_start_time + (30 * 60 * 1000)  # 30 minutes after ORB start
        
        today_candles = []
        for i, candle in enumerate(candles_15m):
            if get_utc_date(candle['timestamp']) == today and candle['timestamp'] >= orb_end_time:
                today_candles.append((i, candle))
        
        if len(today_candles) < 2:
            return None, None
        
        # Calculate EMA for all candles
        hl2 = [(c['high'] + c['low']) / 2 for c in candles_15m]
        ema_values = calculate_ema(hl2, self.ema_length)
        atr_values = calculate_atr(candles_15m)
        
        # Simulate the algo logic on today's candles
        state = 'waiting'  # waiting, in_breakout, entry_taken
        breakout_bullish = None
        breakout_start_idx = None
        retests = 0
        entry_data = None
        
        for idx, candle in today_candles:
            ema = ema_values[idx]
            close = candle['close']
            high = candle['high']
            low = candle['low']
            
            condition_price = ema if self.breakout_condition == 'EMA' else close
            
            if state == 'waiting':
                # Check for breakout
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
                    # Check for retest (only after breakout bar)
                    if idx > breakout_start_idx:
                        if breakout_bullish and close > orb_high and low < orb_high:
                            retests += 1
                        elif not breakout_bullish and close < orb_low and high > orb_low:
                            retests += 1
                    
                    # Check entry condition
                    if retests >= self.retests_needed:
                        state = 'entry_taken'
                        
                        # Calculate SL
                        center = (orb_high + orb_low) / 2.0
                        if self.sl_method == 'Safer':
                            sl_price = (center + orb_high) / 2.0 if breakout_bullish else (center + orb_low) / 2.0
                        elif self.sl_method == 'Balanced':
                            sl_price = center
                        else:  # Risky
                            sl_price = (center + orb_low) / 2.0 if breakout_bullish else (center + orb_high) / 2.0
                        
                        entry_data = {
                            'direction': 'buy' if breakout_bullish else 'sell',
                            'entry_price': close,
                            'sl_price': sl_price,
                            'orb_high': orb_high,
                            'orb_low': orb_low,
                            'entry_index': idx
                        }
            
            elif state == 'entry_taken':
                # Entry already taken, stop scanning for new entries
                break
        
        # Return entry if one was found today
        if entry_data:
            return 'entry', entry_data
        
        return None, None
    
    def reset_session(self):
        """No-op for stateless implementation"""
        pass


# Test
if __name__ == "__main__":
    algo = ORBAlgo()
    print("ORB Algo (Stateless) initialized successfully")
    print(f"Settings: EMA={algo.ema_length}, Retests={algo.retests_needed}, SL={algo.sl_method}")
