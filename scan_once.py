"""
ORB Algo Telegram Alert Bot - One-shot scan for GitHub Actions
Scans all pairs once and sends signals, then exits
"""
import asyncio
import os
from datetime import datetime
from typing import Dict

import config
from binance_client import BinanceClient
from orb_algo import ORBAlgo
from telegram_bot import TelegramAlertBot


# Override config with environment variables if available
if os.environ.get('TELEGRAM_BOT_TOKEN'):
    config.TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
if os.environ.get('CHAT_ID'):
    config.CHAT_ID = int(os.environ['CHAT_ID'])


class ORBScanner:
    def __init__(self):
        self.binance = BinanceClient()
        self.bot = TelegramAlertBot()
        
        # One ORB algo instance per symbol
        self.algos: Dict[str, ORBAlgo] = {}
        for symbol in config.TRADING_PAIRS:
            self.algos[symbol] = ORBAlgo()
    
    async def run_scan(self):
        """Run a single scan of all pairs"""
        print("=" * 50)
        print(f"[*] ORB Algo Scan Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[i] Scanning {len(config.TRADING_PAIRS)} pairs")
        print("=" * 50)
        
        # Initialize Telegram bot
        await self.bot.start()
        
        signals_found = 0
        
        for symbol in config.TRADING_PAIRS:
            try:
                signal = await self._scan_pair(symbol)
                if signal:
                    signals_found += 1
            except Exception as e:
                print(f"   [!] Error scanning {symbol}: {e}")
        
        print(f"\n[+] Scan complete. {signals_found} signals found.")
        
        # Stop bot
        await self.bot.stop()
    
    async def _scan_pair(self, symbol: str):
        """Scan a single pair for signals"""
        # Get candle data
        candles_15m = self.binance.get_klines(symbol, '15m', limit=100)
        candles_30m = self.binance.get_klines(symbol, '30m', limit=50)
        
        if not candles_15m or not candles_30m:
            print(f"   [!] No data for {symbol}")
            return None
        
        algo = self.algos[symbol]
        signal_type, signal_data = algo.analyze(candles_15m, candles_30m)
        
        if signal_type == 'entry':
            print(f"   [SIGNAL] {symbol}: {signal_data['direction'].upper()} signal!")
            
            # Send Telegram notification
            await self.bot.send_entry_signal(
                symbol=symbol,
                direction=signal_data['direction'],
                entry_price=signal_data['entry_price'],
                sl_price=signal_data['sl_price'],
                signal_id=f"gh_{symbol}_{datetime.now().strftime('%H%M')}"
            )
            return signal_data
        
        return None


async def main():
    """Main entry point for GitHub Actions"""
    scanner = ORBScanner()
    await scanner.run_scan()


if __name__ == "__main__":
    asyncio.run(main())
