# ORB Algo Telegram Bot Configuration

# Telegram Settings
TELEGRAM_BOT_TOKEN = "8396997139:AAEHrO7KVtWI1p-u24rzRiGhjv0VrXVVgVY"
CHAT_ID = -5196086558

# Trading Pairs (Binance format)
# Tier 1: Large cap
# Tier 2: Solid projects
# Tier 3: Volatile but potential
TRADING_PAIRS = [
    # Tier 1 - Ana Coinler
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT',
    # Tier 2 - Altcoinler
    'DOTUSDT', 'NEARUSDT', 'ATOMUSDT', 'UNIUSDT', 'AAVEUSDT', 'LTCUSDT',
    'XLMUSDT', 'POLUSDT', 'TAOUSDT', 'OPUSDT', 'INJUSDT', 'SUIUSDT',
    'ZENUSDT', 'ENAUSDT', 'EIGENUSDT', 'ZECUSDT',
    # Tier 3 - Yeni Eklenenler
    'PEPEUSDT', 'DASHUSDT', 'LDOUSDT', 'JASMYUSDT', 'AXSUSDT', 'CHZUSDT', 'ICPUSDT',
]

# ORB Algo Settings (matching Pine Script)
ORB_TIMEFRAME = '1h'        # ORB Timeframe (1 hour)
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
