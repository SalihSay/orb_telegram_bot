"""
ORB Algo Strategy Implementation
Ported from Pine Script to Python - Fixed Session Logic
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import config


class ORBState:
    OPENING_RANGE = "Opening Range"
    WAITING_FOR_BREAKOUTS = "Waiting For Breakouts"
    IN_BREAKOUT = "In Breakout"
    ENTRY_TAKEN = "Entry Taken"


@dataclass
class Breakout:
    is_bullish: bool
    start_index: int
    end_index: Optional[int] = None
    failed: bool = False
    retests: int = 0


@dataclass
class ORBSession:
    high: Optional[float] = None
    low: Optional[float] = None
    start_time: int = 0
    start_index: int = 0
    end_index: Optional[int] = None
    orb_complete: bool = False
    
    state: str = ORBState.OPENING_RANGE
    breakouts: List[Breakout] = field(default_factory=list)
    
    # Entry
    entry_bullish: Optional[bool] = None
    entry_index: Optional[int] = None
    entry_price: Optional[float] = None
    entry_atr: Optional[float] = None
    
    # Take Profit
    tp1_index: Optional[int] = None
    tp1_price: Optional[float] = None
    
    # Stop Loss
    sl_index: Optional[int] = None
    sl_price: Optional[float] = None


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return [prices[0]] * len(prices)
    
    ema = []
    multiplier = 2 / (period + 1)
    
    # First EMA is SMA
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
    
    # Calculate ATR as EMA of TR
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


def diff_percent(val1: float, val2: float) -> float:
    """Calculate percentage difference"""
    return abs(val1 - val2) / val2 * 100.0


def get_session_start_hour() -> int:
    """Get the UTC hour when trading session starts (00:00 UTC for crypto)"""
    return 0  # Crypto markets: new day starts at 00:00 UTC


def is_same_session(timestamp1: int, timestamp2: int) -> bool:
    """Check if two timestamps are in the same trading session (same UTC day)"""
    dt1 = datetime.fromtimestamp(timestamp1 / 1000, tz=timezone.utc)
    dt2 = datetime.fromtimestamp(timestamp2 / 1000, tz=timezone.utc)
    return dt1.date() == dt2.date()


def find_session_orb(candles_30m: List[Dict]) -> Tuple[Optional[float], Optional[float], Optional[int]]:
    """
    Find the ORB (Opening Range) for the current session.
    ORB = High and Low of the first 30-minute candle of the day.
    
    Returns: (orb_high, orb_low, orb_start_timestamp) or (None, None, None)
    """
    if not candles_30m:
        return None, None, None
    
    # Get the last candle's date to determine current session
    last_candle = candles_30m[-1]
    last_dt = datetime.fromtimestamp(last_candle['timestamp'] / 1000, tz=timezone.utc)
    current_date = last_dt.date()
    
    # Find the first 30m candle of today (the session's opening range)
    for candle in candles_30m:
        candle_dt = datetime.fromtimestamp(candle['timestamp'] / 1000, tz=timezone.utc)
        if candle_dt.date() == current_date:
            # This is the first candle of today's session = ORB
            return candle['high'], candle['low'], candle['timestamp']
    
    return None, None, None


def is_orb_period_complete(orb_start_time: int, current_time: int, orb_duration_minutes: int = 30) -> bool:
    """Check if ORB period is complete"""
    orb_duration_ms = orb_duration_minutes * 60 * 1000
    return current_time >= orb_start_time + orb_duration_ms


class ORBAlgo:
    def __init__(self):
        self.ema_length = config.EMA_LENGTH
        self.retests_needed = config.RETESTS_NEEDED
        self.breakout_condition = config.BREAKOUT_CONDITION
        self.sl_method = config.SL_METHOD
        self.tp_method = config.TP_METHOD
        self.adaptive_sl = config.ADAPTIVE_SL
        self.minimum_profit_percent = config.MINIMUM_PROFIT_PERCENT
        
        # Current session state
        self.current_session: Optional[ORBSession] = None
        self.last_session_date: Optional[str] = None
    
    def analyze(self, candles: List[Dict], orb_candles: List[Dict]) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Analyze candles and return signal if any
        
        Args:
            candles: 15-minute candles
            orb_candles: 30-minute candles for ORB calculation
            
        Returns:
            Tuple of (signal_type, signal_data) or (None, None)
        """
        if len(candles) < 50 or len(orb_candles) < 10:
            return None, None
        
        # Get current session's ORB
        orb_high, orb_low, orb_start_time = find_session_orb(orb_candles)
        
        if orb_high is None or orb_low is None:
            return None, None
        
        # Check if this is a new session
        current_candle = candles[-1]
        current_dt = datetime.fromtimestamp(current_candle['timestamp'] / 1000, tz=timezone.utc)
        current_date_str = current_dt.date().isoformat()
        
        if self.last_session_date != current_date_str:
            # New session - reset
            self.current_session = ORBSession()
            self.current_session.high = orb_high
            self.current_session.low = orb_low
            self.current_session.start_time = orb_start_time
            self.last_session_date = current_date_str
        
        session = self.current_session
        if session is None:
            return None, None
        
        # Check if ORB period is complete (30 minutes after session start)
        if not session.orb_complete:
            if is_orb_period_complete(session.start_time, current_candle['timestamp']):
                session.orb_complete = True
                session.state = ORBState.WAITING_FOR_BREAKOUTS
            else:
                # Still in opening range period
                return None, None
        
        # Calculate indicators
        hl2 = [(c['high'] + c['low']) / 2 for c in candles]
        ema = calculate_ema(hl2, self.ema_length)
        atr = calculate_atr(candles)
        
        current_ema = ema[-1]
        current_atr = atr[-1] if atr else 0.01
        
        # Check for breakout entry
        if session.state == ORBState.WAITING_FOR_BREAKOUTS:
            condition_price = current_ema if self.breakout_condition == 'EMA' else current_candle['close']
            
            if condition_price > session.high:
                # Bullish breakout
                breakout = Breakout(is_bullish=True, start_index=len(candles)-1)
                session.breakouts.append(breakout)
                session.state = ORBState.IN_BREAKOUT
                
            elif condition_price < session.low:
                # Bearish breakout
                breakout = Breakout(is_bullish=False, start_index=len(candles)-1)
                session.breakouts.append(breakout)
                session.state = ORBState.IN_BREAKOUT
        
        # Handle breakout
        if session.state == ORBState.IN_BREAKOUT and session.breakouts:
            cur_breakout = session.breakouts[-1]
            close = current_candle['close']
            
            # Check for failed breakout
            if cur_breakout.is_bullish and close < session.high:
                cur_breakout.failed = True
                session.state = ORBState.WAITING_FOR_BREAKOUTS
            elif not cur_breakout.is_bullish and close > session.low:
                cur_breakout.failed = True
                session.state = ORBState.WAITING_FOR_BREAKOUTS
            
            # Check for retest
            if not cur_breakout.failed:
                if cur_breakout.is_bullish and close > session.high and current_candle['low'] < session.high:
                    cur_breakout.retests += 1
                elif not cur_breakout.is_bullish and close < session.low and current_candle['high'] > session.low:
                    cur_breakout.retests += 1
                
                # Entry condition met
                if cur_breakout.retests >= self.retests_needed:
                    session.state = ORBState.ENTRY_TAKEN
                    session.entry_bullish = cur_breakout.is_bullish
                    session.entry_index = len(candles) - 1
                    session.entry_price = close
                    session.entry_atr = current_atr
                    
                    # Calculate Stop Loss
                    center = (session.high + session.low) / 2.0
                    if self.sl_method == 'Safer':
                        session.sl_price = (center + session.high) / 2.0 if session.entry_bullish else (center + session.low) / 2.0
                    elif self.sl_method == 'Balanced':
                        session.sl_price = center
                    elif self.sl_method == 'Risky':
                        session.sl_price = (center + session.low) / 2.0 if session.entry_bullish else (center + session.high) / 2.0
                    
                    # Return entry signal
                    return 'entry', {
                        'direction': 'buy' if session.entry_bullish else 'sell',
                        'entry_price': session.entry_price,
                        'sl_price': session.sl_price,
                        'orb_high': session.high,
                        'orb_low': session.low
                    }
        
        # Handle TP1 check for active position
        if session.state == ORBState.ENTRY_TAKEN and session.entry_price and not session.tp1_index:
            close = current_candle['close']
            
            is_profitable = (session.entry_bullish and current_ema > session.entry_price) or \
                           (not session.entry_bullish and current_ema < session.entry_price)
            
            if is_profitable and diff_percent(current_ema, session.entry_price) >= self.minimum_profit_percent:
                # Check TP1 condition
                if (session.entry_bullish and close < current_ema) or \
                   (not session.entry_bullish and close > current_ema):
                    session.tp1_index = len(candles) - 1
                    session.tp1_price = current_ema
                    
                    return 'close', {
                        'direction': 'buy' if session.entry_bullish else 'sell',
                        'entry_price': session.entry_price,
                        'close_price': session.tp1_price,
                        'profit_percent': diff_percent(session.tp1_price, session.entry_price)
                    }
            
            # Check Stop Loss
            if session.sl_price:
                if (session.entry_bullish and current_candle['low'] < session.sl_price) or \
                   (not session.entry_bullish and current_candle['high'] > session.sl_price):
                    session.sl_index = len(candles) - 1
                    
                    return 'stoploss', {
                        'direction': 'buy' if session.entry_bullish else 'sell',
                        'entry_price': session.entry_price,
                        'sl_price': session.sl_price,
                        'loss_percent': diff_percent(session.sl_price, session.entry_price)
                    }
        
        return None, None
    
    def reset_session(self):
        """Reset for new trading session"""
        self.current_session = None
        self.last_session_date = None


# Test
if __name__ == "__main__":
    algo = ORBAlgo()
    print("ORB Algo initialized successfully")
    print(f"Settings: EMA={algo.ema_length}, Retests={algo.retests_needed}, SL={algo.sl_method}")
