"""
ORB Algo Telegram Alert Bot - Main Entry Point
Combines all modules and runs the trading signal scanner
"""
import asyncio
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict

import config
from binance_client import BinanceClient
from orb_algo import ORBAlgo
from position_tracker import PositionTracker
from telegram_bot import TelegramAlertBot


class ORBAlertSystem:
    def __init__(self):
        self.binance = BinanceClient()
        self.tracker = PositionTracker()
        self.bot = TelegramAlertBot(position_tracker=self.tracker)
        
        # One ORB algo instance per symbol
        self.algos: Dict[str, ORBAlgo] = {}
        for symbol in config.TRADING_PAIRS:
            self.algos[symbol] = ORBAlgo()
        
        self._running = False
        self._scan_interval = 60  # Check every 60 seconds
        self._sent_signals = set()  # Track sent signals to avoid duplicates (symbol_direction_date)
    
    async def start(self):
        """Start the alert system"""
        print("=" * 50)
        print("[*] ORB Algo Alert System Starting...")
        print(f"[i] Tracking {len(config.TRADING_PAIRS)} pairs")
        print(f"[i] Scan interval: {self._scan_interval}s")
        print("=" * 50)
        
        # Start Telegram bot (no startup message to avoid spam)
        await self.bot.start()
        print("[+] Telegram bot started!")
        
        self._running = True
        
        # Start scanning loop
        await self._scan_loop()
    
    async def stop(self):
        """Stop the system"""
        print("\n[!] Stopping ORB Alert System...")
        self._running = False
        await self.bot.stop()
        print("[+] System stopped.")
    
    async def _scan_loop(self):
        """Main scanning loop - scans at 01, 16, 31, 46 minute marks (1 min after candle close)"""
        while self._running:
            try:
                await self._scan_all_pairs()
                await self._check_active_positions()
                
                # Cleanup old signals
                self.tracker.cleanup_old_signals(hours=12)
                
            except Exception as e:
                print(f"[!] Scan error: {e}")
            
            # Calculate seconds until next scan time (every 5 minutes: 01, 06, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56)
            now = datetime.now()
            current_minute = now.minute
            
            # Find next scan minute (every 5 minutes + 1 for candle close buffer)
            scan_minutes = [1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56]
            next_scan_minute = None
            for m in scan_minutes:
                if m > current_minute:
                    next_scan_minute = m
                    break
            
            if next_scan_minute is None:
                # Next scan is in the next hour at minute 01
                next_scan_minute = 1
                seconds_until_next = (60 - current_minute + 1) * 60 - now.second
            else:
                seconds_until_next = (next_scan_minute - current_minute) * 60 - now.second
            
            if seconds_until_next <= 0:
                seconds_until_next = 5 * 60  # Wait full 5 minutes
            
            next_scan = now + timedelta(seconds=seconds_until_next)
            print(f"[i] Next scan at {next_scan.strftime('%H:%M:%S')} (in {seconds_until_next//60}m {seconds_until_next%60}s)")
            
            await asyncio.sleep(seconds_until_next)
    
    async def _scan_all_pairs(self):
        """Scan all pairs for new signals"""
        print(f"\n[*] Scanning {len(config.TRADING_PAIRS)} pairs... [{datetime.now().strftime('%H:%M:%S')}]")
        
        for symbol in config.TRADING_PAIRS:
            try:
                await self._scan_pair(symbol)
            except Exception as e:
                print(f"   [!] Error scanning {symbol}: {e}")
    
    async def _scan_pair(self, symbol: str):
        """Scan a single pair for signals"""
        # Get candle data
        candles_15m = self.binance.get_klines(symbol, config.SIGNAL_TIMEFRAME, limit=100)
        candidates_orb = self.binance.get_klines(symbol, config.ORB_TIMEFRAME, limit=50)
        
        if not candles_15m or not candidates_orb:
            return

        # CANDLE CLOSE LOGIC: Filter to only keep closed candles
        # This prevents "repainting" signals during forming candles
        candles_15m = [c for c in candles_15m if c['is_closed']]
        candles_orb = [c for c in candidates_orb if c['is_closed']]

        if not candles_15m or not candles_orb:
            return
        
        algo = self.algos[symbol]
        signal_type, signal_data = algo.analyze(candles_15m, candles_orb)
        
        if signal_type == 'entry':
            # Create unique signal key to avoid duplicates
            from datetime import datetime
            
            # Use candle time as unique identifier for this signal
            candle_time = signal_data.get('candle_time', 0)
            signal_key = f"{symbol}_{signal_data['direction']}_{candle_time}"
            
            # Skip if this exact signal was already sent
            if signal_key in self._sent_signals:
                return
            
            print(f"   [SIGNAL] {symbol}: {signal_data['direction'].upper()} signal (Closed Candle)!")
            
            # Mark signal as sent
            self._sent_signals.add(signal_key)
            
            # Add to tracker
            signal_id = self.tracker.add_signal(
                symbol=symbol,
                direction=signal_data['direction'],
                entry_price=signal_data['entry_price'],
                sl_price=signal_data['sl_price'],
                orb_high=signal_data.get('orb_high'),
                orb_low=signal_data.get('orb_low')
            )
            
            # Send Telegram notification
            await self.bot.send_entry_signal(
                symbol=symbol,
                direction=signal_data['direction'],
                entry_price=signal_data['entry_price'],
                sl_price=signal_data['sl_price'],
                signal_id=signal_id,
                candle_time=signal_data.get('candle_time')
            )
    
    async def _check_active_positions(self):
        """Check active positions for TP1 or SL using Candle Close logic"""
        positions = self.tracker.get_confirmed_positions()
        
        for pos in positions:
            symbol = pos['symbol']
            entry_price = pos['entry_price']
            sl_price = pos['sl_price']
            is_long = pos['direction'] == 'buy'
            
            try:
                # Get current candle data - fetch 2 to ensure we get the last closed one
                candles_15m = self.binance.get_klines(symbol, config.SIGNAL_TIMEFRAME, limit=5)
                
                # Filter for closed candles
                closed_candles = [c for c in candles_15m if c['is_closed']]
                
                if not closed_candles:
                    continue
                
                # Use the LAST CLOSED candle for exit analysis
                current_candle = closed_candles[-1]
                current_high = current_candle['high']
                current_low = current_candle['low']
                current_close = current_candle['close']
                
                # Calculate EMA for TP check (using closed candles only)
                hl2 = [(c['high'] + c['low']) / 2 for c in closed_candles]
                ema_len = min(config.EMA_LENGTH, len(hl2))
                
                # Simple SMA/EMA calculation for check
                # Note: This is an approximation. Ideally orb_algo should handle exits.
                # But calculating EMA on closed candles is safe.
                if len(hl2) >= ema_len:
                    # Calculate EMA
                    multiplier = 2 / (ema_len + 1)
                    ema = sum(hl2[:ema_len]) / ema_len
                    for price in hl2[ema_len:]:
                         ema = (price - ema) * multiplier + ema
                else:
                    ema = sum(hl2) / len(hl2)
                
                # Check Stop Loss (Wick Logic - matches TradingView)
                sl_hit = False
                if is_long and current_low < sl_price:  # Check low (wick), not close
                    sl_hit = True
                elif not is_long and current_high > sl_price: # Check high (wick), not close
                    sl_hit = True
                
                if sl_hit:
                    print(f"   [SL] {symbol}: Stop Loss triggered (Closed Candle)!")
                    
                    # Close position
                    result = self.tracker.close_position(symbol, current_close, 'sl')
                    
                    if result:
                        await self.bot.send_stoploss_signal(
                            symbol=symbol,
                            entry_price=result['entry_price'],
                            sl_price=result['close_price'],
                            loss_percent=abs(result['profit_percent'])
                        )
                    continue
                
                # Check TP (EMA crossback with profit)
                is_profitable = (is_long and current_close > entry_price) or (not is_long and current_close < entry_price)
                profit_pct = abs(current_close - entry_price) / entry_price * 100
                
                if is_profitable and profit_pct >= config.MINIMUM_PROFIT_PERCENT:
                    # Check for EMA crossback
                    ema_crossback = (is_long and current_close < ema) or (not is_long and current_close > ema)
                    
                    if ema_crossback:
                        print(f"   [TP1] {symbol}: TP1 triggered (Closed Candle)!")
                        
                        result = self.tracker.close_position(symbol, current_close, 'tp1')
                        
                        if result:
                            await self.bot.send_close_signal(
                                symbol=symbol,
                                direction=result['direction'],
                                entry_price=result['entry_price'],
                                close_price=result['close_price'],
                                profit_percent=result['profit_percent']
                            )
                    
            except Exception as e:
                print(f"   [!] Error checking {symbol}: {e}")


async def main():
    """Main entry point"""
    system = ORBAlertSystem()
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        asyncio.create_task(system.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await system.start()
    except KeyboardInterrupt:
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
