"""
Telegram Bot - Sends signals and receives user confirmation
"""
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config


class TelegramAlertBot:
    def __init__(self, position_tracker=None):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.CHAT_ID
        self.position_tracker = position_tracker
        self.app = None
        self._running = False
    
    async def start(self):
        """Start the bot"""
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("girdim", self.cmd_girdim))
        self.app.add_handler(CommandHandler("pozisyonlar", self.cmd_positions))
        self.app.add_handler(CommandHandler("istatistik", self.cmd_stats))
        self.app.add_handler(CommandHandler("yardim", self.cmd_help))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        await self.app.initialize()
        await self.app.start()
        # drop_pending_updates=True fixes conflict when previous instance wasn't closed properly
        await self.app.updater.start_polling(drop_pending_updates=True)
        self._running = True
        
        print("[+] Telegram bot started!")
    
    async def stop(self):
        """Stop the bot"""
        if self.app and self._running:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            self._running = False
    
    async def send_entry_signal(self, symbol: str, direction: str, entry_price: float, 
                                sl_price: float, signal_id: int = None):
        """Send entry signal to user"""
        from datetime import datetime
        emoji = "🟢" if direction == "buy" else "🔴"
        direction_tr = "LONG" if direction == "buy" else "SHORT"
        current_time = datetime.now().strftime("%H:%M")
        
        message = f"""
{emoji} <b>{direction_tr} Sinyali!</b>

📊 <b>Parite:</b> {symbol}
⏰ <b>Timeframe:</b> 15dk
🕐 <b>Mum Saati:</b> {current_time}
💰 <b>Giriş:</b> {entry_price:.4f}
🛑 <b>Stop Loss:</b> {sl_price:.4f}

Pozisyona girdiyseniz /girdim yazın
"""
        
        # Add inline button
        keyboard = [[InlineKeyboardButton("✅ Girdim", callback_data=f"confirm_{signal_id}_{symbol}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def send_close_signal(self, symbol: str, direction: str, entry_price: float,
                                close_price: float, profit_percent: float):
        """Send TP1/Close signal to user"""
        profit_emoji = "📈" if profit_percent > 0 else "📉"
        profit_sign = "+" if profit_percent > 0 else ""
        
        message = f"""
✅ <b>Pozisyon Kapatıldı!</b>

📊 <b>Parite:</b> {symbol}
💰 <b>Giriş:</b> {entry_price:.4f}
🎯 <b>Close:</b> {close_price:.4f}
{profit_emoji} <b>Kar:</b> {profit_sign}{profit_percent:.2f}%
"""
        
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode='HTML'
        )
    
    async def send_stoploss_signal(self, symbol: str, entry_price: float, 
                                   sl_price: float, loss_percent: float):
        """Send stop loss notification"""
        message = f"""
🛑 <b>Stop Loss Tetiklendi!</b>

📊 <b>Parite:</b> {symbol}
💰 <b>Giriş:</b> {entry_price:.4f}
❌ <b>SL:</b> {sl_price:.4f}
📉 <b>Kayıp:</b> -{loss_percent:.2f}%
"""
        
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            parse_mode='HTML'
        )
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        message = """
🤖 <b>ORB Algo Alert Bot</b>

Bu bot, ORB stratejisine göre kripto sinyalleri gönderir.

<b>Komutlar:</b>
/girdim - Pozisyona girdiğinizi onaylayın
/pozisyonlar - Aktif pozisyonları görün
/istatistik - Trading istatistikleri
/yardim - Yardım

Bot çalışıyor ve sinyalleri takip ediyor! 🚀
"""
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def cmd_girdim(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /girdim command - confirm position entry"""
        if self.position_tracker:
            success = self.position_tracker.confirm_position()
            if success:
                await update.message.reply_text("✅ Pozisyon onaylandı! TP1 takibi başladı.")
            else:
                await update.message.reply_text("❌ Onaylanacak bekleyen sinyal yok.")
        else:
            await update.message.reply_text("❌ Position tracker bağlı değil.")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pozisyonlar command - show active positions"""
        if not self.position_tracker:
            await update.message.reply_text("❌ Position tracker bağlı değil.")
            return
        
        positions = self.position_tracker.get_confirmed_positions()
        
        if not positions:
            await update.message.reply_text("📋 Aktif pozisyon yok.")
            return
        
        message = "📋 <b>Aktif Pozisyonlar:</b>\n\n"
        for pos in positions:
            emoji = "🟢" if pos['direction'] == 'buy' else "🔴"
            message += f"{emoji} {pos['symbol']}\n"
            message += f"   Giriş: {pos['entry_price']:.4f}\n"
            message += f"   SL: {pos['sl_price']:.4f}\n\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /istatistik command - show trading stats"""
        if not self.position_tracker:
            await update.message.reply_text("❌ Position tracker bağlı değil.")
            return
        
        stats = self.position_tracker.get_stats()
        
        message = f"""
📊 <b>Trading İstatistikleri</b>

📈 Toplam İşlem: {stats['total_trades']}
✅ Kazanan: {stats['wins']}
❌ Kaybeden: {stats['losses']}
🎯 Winrate: {stats['winrate']:.1f}%
💰 Toplam Kar: {stats['total_profit']:.2f}%
"""
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /yardim command"""
        message = """
📖 <b>Kullanım Rehberi</b>

1️⃣ Bot sinyal gönderdiğinde bildirim alırsınız
2️⃣ Pozisyona girdiyseniz "✅ Girdim" butonuna tıklayın
3️⃣ Bot sadece onayladığınız pozisyonları takip eder
4️⃣ TP1 oluştuğunda close bildirimi alırsınız

<b>Komutlar:</b>
/girdim - Pozisyon onayı
/pozisyonlar - Aktif pozisyonlar
/istatistik - İstatistikler
"""
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button clicks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("confirm_"):
            parts = data.split("_")
            if len(parts) >= 3:
                signal_id = int(parts[1])
                symbol = parts[2]
                
                if self.position_tracker:
                    success = self.position_tracker.confirm_position(position_id=signal_id)
                    if success:
                        await query.edit_message_text(
                            query.message.text + "\n\n✅ <b>Pozisyon onaylandı! TP1 takibi başladı.</b>",
                            parse_mode='HTML'
                        )
                    else:
                        await query.edit_message_text(
                            query.message.text + "\n\n❌ <b>Onaylama başarısız.</b>",
                            parse_mode='HTML'
                        )


# Test
if __name__ == "__main__":
    async def test():
        bot = TelegramAlertBot()
        await bot.start()
        
        # Send test message
        await bot.app.bot.send_message(
            chat_id=config.CHAT_ID,
            text="🤖 Bot test mesajı - Çalışıyor!"
        )
        
        print("Test message sent! Press Ctrl+C to stop.")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await bot.stop()
    
    asyncio.run(test())
