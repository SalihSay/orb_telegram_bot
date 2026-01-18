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
    
    async def start(self):
        """Start the alert system"""
        print("=" * 50)
        print("[*] ORB Algo Alert System Starting...")
        print(f"[i] Tracking {len(config.TRADING_PAIRS)} pairs")
        print(f"[i] Scan interval: {self._scan_interval}s")
        print("=" * 50)
        
        # Start Telegram bot
        await self.bot.start()
        
        # Send startup message (may fail if user hasn't started bot in Telegram)
        try:
            await self.bot.app.bot.send_message(
                chat_id=config.CHAT_ID,
                text=f"🤖 <b>ORB Alert Bot Başlatıldı!</b>\n\n"
                     f"📊 Takip edilen parite: {len(config.TRADING_PAIRS)}\n"
                     f"⏰ Tarama aralığı: 15dk\n\n"
                     f"Sinyaller geldiğinde bildirim alacaksınız!",
                parse_mode='HTML'
            )
            print("[+] Startup message sent to Telegram!")
        except Exception as e:
            print(f"[!] Could not send startup message: {e}")
            print("[i] Make sure you have started the bot in Telegram with /start command")
        
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
            
            # Calculate seconds until next scan time (every 15 minutes: 01, 16, 31, 46)
            now = datetime.now()
            current_minute = now.minute
            
            # Find next scan minute (every 15 minutes + 1 for candle close buffer)
            scan_minutes = [1, 16, 31, 46]
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
        candles_15m = self.binance.get_klines(symbol, '15m', limit=100)
        candles_30m = self.binance.get_klines(symbol, '30m', limit=50)
        
        if not candles_15m or not candles_30m:
            return
        
        algo = self.algos[symbol]
        signal_type, signal_data = algo.analyze(candles_15m, candles_30m)
        
        if signal_type == 'entry':
            print(f"   [SIGNAL] {symbol}: {signal_data['direction'].upper()} signal!")
            
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
        """Check active positions for TP1 or SL"""
        positions = self.tracker.get_confirmed_positions()
        
        for pos in positions:
            symbol = pos['symbol']
            
            try:
                # Get current data
                candles_15m = self.binance.get_klines(symbol, '15m', limit=100)
                candles_30m = self.binance.get_klines(symbol, '30m', limit=50)
                
                if not candles_15m:
                    continue
                
                algo = self.algos[symbol]
                signal_type, signal_data = algo.analyze(candles_15m, candles_30m)
                
                if signal_type == 'close':
                    print(f"   [TP1] {symbol}: TP1 triggered!")
                    
                    # Close position in tracker
                    result = self.tracker.close_position(symbol, signal_data['close_price'], 'tp1')
                    
                    if result:
                        # Send notification
                        await self.bot.send_close_signal(
                            symbol=symbol,
                            direction=result['direction'],
                            entry_price=result['entry_price'],
                            close_price=result['close_price'],
                            profit_percent=result['profit_percent']
                        )
                    
                    # Reset algo for this symbol
                    algo.reset_session()
                
                elif signal_type == 'stoploss':
                    print(f"   [SL] {symbol}: Stop Loss triggered!")
                    
                    # Close position
                    result = self.tracker.close_position(symbol, signal_data['sl_price'], 'sl')
                    
                    if result:
                        await self.bot.send_stoploss_signal(
                            symbol=symbol,
                            entry_price=result['entry_price'],
                            sl_price=result['close_price'],
                            loss_percent=abs(result['profit_percent'])
                        )
                    
                    algo.reset_session()
                    
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
