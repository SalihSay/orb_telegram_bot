"""
ORB Algo Telegram Alert Bot - One-shot scan for GitHub Actions
Scans all pairs, tracks active signals, sends entry/close notifications
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Optional

import config
from binance_client import BinanceClient
from orb_algo import ORBAlgo
from telegram_bot import TelegramAlertBot


# Override config with environment variables if available
if os.environ.get('TELEGRAM_BOT_TOKEN'):
    config.TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
if os.environ.get('CHAT_ID'):
    config.CHAT_ID = int(os.environ['CHAT_ID'])

# File to store active signals between runs
SIGNALS_FILE = 'active_signals.json'


def load_active_signals() -> Dict:
    """Load active signals from JSON file"""
    if os.path.exists(SIGNALS_FILE):
        try:
            with open(SIGNALS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_active_signals(signals: Dict):
    """Save active signals to JSON file"""
    with open(SIGNALS_FILE, 'w') as f:
        json.dump(signals, f, indent=2)


class ORBScanner:
    def __init__(self):
        self.binance = BinanceClient()
        self.bot = TelegramAlertBot()
        
        # One ORB algo instance per symbol
        self.algos: Dict[str, ORBAlgo] = {}
        for symbol in config.TRADING_PAIRS:
            self.algos[symbol] = ORBAlgo()
        
        # Load active signals
        self.active_signals = load_active_signals()
    
    async def run_scan(self):
        """Run a single scan of all pairs"""
        print("=" * 50)
        print(f"[*] ORB Algo Scan Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[i] Scanning {len(config.TRADING_PAIRS)} pairs")
        print(f"[i] Active signals: {len(self.active_signals)}")
        print("=" * 50)
        
        # Initialize Telegram bot
        await self.bot.start()
        
        new_signals = 0
        closed_signals = 0
        
        for symbol in config.TRADING_PAIRS:
            try:
                result = await self._scan_pair(symbol)
                if result == 'new':
                    new_signals += 1
                elif result == 'closed':
                    closed_signals += 1
            except Exception as e:
                print(f"   [!] Error scanning {symbol}: {e}")
        
        # Save updated signals
        save_active_signals(self.active_signals)
        
        print(f"\n[+] Scan complete. New: {new_signals}, Closed: {closed_signals}")
        
        # Stop bot
        await self.bot.stop()
    
    async def _scan_pair(self, symbol: str) -> Optional[str]:
        """Scan a single pair for signals"""
        # Get candle data
        candles_15m = self.binance.get_klines(symbol, '15m', limit=100)
        candles_30m = self.binance.get_klines(symbol, '30m', limit=50)
        
        if not candles_15m or not candles_30m:
            print(f"   [!] No data for {symbol}")
            return None
        
        algo = self.algos[symbol]
        
        # If we have an active signal for this symbol, check for close
        if symbol in self.active_signals:
            return await self._check_active_signal(symbol, candles_15m, candles_30m, algo)
        
        # Otherwise, check for new entry
        signal_type, signal_data = algo.analyze(candles_15m, candles_30m)
        
        if signal_type == 'entry':
            print(f"   [SIGNAL] {symbol}: {signal_data['direction'].upper()} signal!")
            
            # Store active signal
            self.active_signals[symbol] = {
                'direction': signal_data['direction'],
                'entry_price': signal_data['entry_price'],
                'sl_price': signal_data['sl_price'],
                'orb_high': signal_data.get('orb_high'),
                'orb_low': signal_data.get('orb_low'),
                'entry_time': datetime.now().isoformat()
            }
            
            # Send Telegram notification
            await self._send_entry_notification(symbol, signal_data)
            return 'new'
        
        return None
    
    async def _check_active_signal(self, symbol: str, candles_15m, candles_30m, algo) -> Optional[str]:
        """Check if an active signal has hit TP1 or SL"""
        signal_info = self.active_signals[symbol]
        
        if not candles_15m or len(candles_15m) < 20:
            return None
        
        # Get current candle data
        current_candle = candles_15m[-1]
        current_price = current_candle['close']
        entry_price = signal_info['entry_price']
        sl_price = signal_info['sl_price']
        is_long = signal_info['direction'] == 'buy'
        
        # Calculate EMA for TP1 check (Pine Script uses EMA for Dynamic TP)
        hl2 = [(c['high'] + c['low']) / 2 for c in candles_15m]
        ema = self._calculate_ema(hl2, config.EMA_LENGTH)
        current_ema = ema[-1] if ema else current_price
        
        # Calculate profit percentage
        if is_long:
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            ema_profit_pct = ((current_ema - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100
            ema_profit_pct = ((entry_price - current_ema) / entry_price) * 100
        
        # TP1 Check (Dynamic method - same as Pine Script)
        # Condition: EMA is in profit >= minimum AND close crosses back below/above EMA
        min_profit = config.MINIMUM_PROFIT_PERCENT
        
        if is_long:
            # Long: EMA > entry (profitable) AND close < EMA (crossback)
            is_ema_profitable = current_ema > entry_price
            is_crossback = current_price < current_ema
            hit_sl = current_candle['low'] <= sl_price
        else:
            # Short: EMA < entry (profitable) AND close > EMA (crossback)
            is_ema_profitable = current_ema < entry_price
            is_crossback = current_price > current_ema
            hit_sl = current_candle['high'] >= sl_price
        
        # Check TP1 - must have minimum profit AND crossback
        if is_ema_profitable and abs(ema_profit_pct) >= min_profit and is_crossback:
            print(f"   [TP1] {symbol}: TP1 hit! +{abs(ema_profit_pct):.2f}%")
            await self._send_close_notification(symbol, signal_info, current_ema, abs(ema_profit_pct), 'TP1')
            del self.active_signals[symbol]
            return 'closed'
        
        # Check Stop Loss
        if hit_sl:
            loss_pct = abs(profit_pct)
            print(f"   [SL] {symbol}: Stop Loss hit! -{loss_pct:.2f}%")
            await self._send_close_notification(symbol, signal_info, sl_price, -loss_pct, 'SL')
            del self.active_signals[symbol]
            return 'closed'
        
        return None
    
    def _calculate_ema(self, prices: list, period: int) -> list:
        """Calculate EMA"""
        if len(prices) < period:
            return prices
        
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
    
    async def _send_entry_notification(self, symbol: str, signal_data: Dict):
        """Send entry signal notification to Telegram"""
        direction = signal_data['direction']
        emoji = "🟢" if direction == 'buy' else "🔴"
        direction_text = "LONG" if direction == 'buy' else "SHORT"
        
        message = (
            f"{emoji} <b>YENİ SİNYAL: {symbol}</b>\n\n"
            f"📊 Yön: <b>{direction_text}</b>\n"
            f"💰 Giriş: <code>{signal_data['entry_price']:.4f}</code>\n"
            f"🛑 Stop Loss: <code>{signal_data['sl_price']:.4f}</code>\n"
            f"⏰ Zaman: {datetime.now().strftime('%H:%M')}\n\n"
            f"📈 ORB High: {signal_data.get('orb_high', 0):.4f}\n"
            f"📉 ORB Low: {signal_data.get('orb_low', 0):.4f}"
        )
        
        await self.bot.app.bot.send_message(
            chat_id=config.CHAT_ID,
            text=message,
            parse_mode='HTML'
        )
    
    async def _send_close_notification(self, symbol: str, signal_info: Dict, close_price: float, profit_pct: float, close_type: str):
        """Send close signal notification to Telegram"""
        direction = signal_info['direction']
        is_profit = profit_pct > 0
        
        if is_profit:
            emoji = "💰"
            result_text = f"+{profit_pct:.2f}%"
        else:
            emoji = "❌"
            result_text = f"{profit_pct:.2f}%"
        
        direction_text = "LONG" if direction == 'buy' else "SHORT"
        
        message = (
            f"{emoji} <b>{close_type} - {symbol}</b>\n\n"
            f"📊 Yön: {direction_text}\n"
            f"💰 Giriş: <code>{signal_info['entry_price']:.4f}</code>\n"
            f"📍 Çıkış: <code>{close_price:.4f}</code>\n"
            f"📈 Sonuç: <b>{result_text}</b>\n"
            f"⏰ Giriş zamanı: {signal_info.get('entry_time', 'N/A')[:16]}"
        )
        
        await self.bot.app.bot.send_message(
            chat_id=config.CHAT_ID,
            text=message,
            parse_mode='HTML'
        )


async def main():
    """Main entry point for GitHub Actions"""
    scanner = ORBScanner()
    await scanner.run_scan()


if __name__ == "__main__":
    asyncio.run(main())
