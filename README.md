# ORB Algo Telegram Bot - Kullanım Rehberi

## 🚀 Hızlı Başlangıç

### Adım 1: Python Kurulumu
Python 3.9+ yüklü olmalı. [python.org](https://www.python.org/downloads/) adresinden indirin.

### Adım 2: Bağımlılıkları Yükleyin
```bash
cd orb_telegram_bot
pip install -r requirements.txt
```

### Adım 3: Botu Test Edin
```bash
python main.py
```

Telegram'da bot size "ORB Alert Bot Başlatıldı!" mesajı gönderecek.

---

## 📱 Telegram Komutları

| Komut | Açıklama |
|-------|----------|
| `/start` | Botu başlat |
| `/girdim` | Pozisyona girdiğinizi onaylayın |
| `/pozisyonlar` | Aktif pozisyonları görün |
| `/istatistik` | Trading istatistikleri |
| `/yardim` | Yardım |

---

## ☁️ Railway.app'e Deploy Etme (Ücretsiz)

### Adım 1: GitHub'a Yükleyin
1. GitHub'da yeni repo oluşturun
2. Dosyaları push edin:
```bash
cd orb_telegram_bot
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADINIZ/orb-telegram-bot.git
git push -u origin main
```

### Adım 2: Railway'de Deploy Edin
1. [Railway.app](https://railway.app) → GitHub ile giriş
2. "New Project" → "Deploy from GitHub repo"
3. Repo'nuzu seçin
4. Otomatik deploy başlayacak

### Adım 3: Railway Ayarları
Railway'de proje ayarlarından:
- **Start Command**: `python main.py`
- Worker olarak çalışacak (Procfile zaten ayarlı)

---

## 📊 Takip Edilen Pariteler

```
BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, ADAUSDT,
TRXUSDT, AVAXUSDT, XRPUSDT, AAVEUSDT,
TAOUSDT, ZENUSDT, ETCUSDT, EIGENUSDT
```

`config.py` dosyasından değiştirebilirsiniz.

---

## ⚙️ Strateji Ayarları

`config.py` dosyasındaki ayarlar:

| Ayar | Değer | Açıklama |
|------|-------|----------|
| ORB_TIMEFRAME | 30m | ORB hesaplama zaman dilimi |
| SIGNAL_TIMEFRAME | 15m | Trading zaman dilimi |
| SENSITIVITY | Medium | Hassasiyet (High/Medium/Low) |
| BREAKOUT_CONDITION | EMA | Breakout koşulu (Close/EMA) |
| EMA_LENGTH | 13 | EMA uzunluğu |
| SL_METHOD | Balanced | Stop Loss yöntemi |

---

## 🔔 Nasıl Çalışır?

1. **Sinyal Taraması**: Bot her 60 saniyede tüm pariteleri tarar
2. **Sinyal Bulundu**: Telegram'a giriş bilgileri gönderilir
3. **Onay Bekler**: "✅ Girdim" butonuna tıklarsınız
4. **TP1 Takibi**: Sadece onayladığınız pozisyonlar takip edilir
5. **Close Bildirimi**: TP1 veya SL tetiklendiğinde haber verir

---

## 🐛 Sorun Giderme

### Bot mesaj göndermiyor
- Token ve Chat ID doğru mu kontrol edin
- Bot'u Telegram'da başlattığınızdan emin olun (/start)

### Sinyal gelmiyor
- Piyasa sakin olabilir, bekleyin
- Konsol çıktısını kontrol edin

### Railway çalışmıyor
- Logs kısmından hataları kontrol edin
- requirements.txt doğru yüklenmiş mi bakın
