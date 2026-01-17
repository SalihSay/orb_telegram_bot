# ORB Algo Telegram Bot Configuration

# Telegram Settings
TELEGRAM_BOT_TOKEN = "8396997139:AAEHrO7KVtWI1p-u24rzRiGhjv0VrXVVgVY"
CHAT_ID = 735859243

# Trading Pairs (Binance format)
# Tier 1: Large cap
# Tier 2: Solid projects
# Tier 3: Volatile but potential
TRADING_PAIRS = [
    # Tier 1 - Büyük Piyasa Değeri
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    # Tier 2 - Sağlam Projeler
    'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'MATICUSDT',
    'NEARUSDT', 'ATOMUSDT', 'UNIUSDT', 'AAVEUSDT', 'LTCUSDT',
    # Tier 3 - Volatil ama Potansiyelli
    'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SUIUSDT',
]

# ORB Algo Settings (matching Pine Script)
ORB_TIMEFRAME = '30m'       # ORB Timeframe (30 minutes)
SIGNAL_TIMEFRAME = '15m'    # Trading timeframe (15 minutes)
SENSITIVITY = 'Medium'      # High, Medium, Low, Lowest
BREAKOUT_CONDITION = 'EMA'  # Close or EMA
TP_METHOD = 'Dynamic'       # Dynamic or ATR
EMA_LENGTH = 13
SL_METHOD = 'Balanced'      # Safer, Balanced, Risky
ADAPTIVE_SL = True

# Derived settings
RETESTS_NEEDED = {
    'High': 0,
    'Medium': 1,
    'Low': 2,
    'Lowest': 3
}[SENSITIVITY]

# Minimum profit settings
MINIMUM_PROFIT_PERCENT = 0.20
