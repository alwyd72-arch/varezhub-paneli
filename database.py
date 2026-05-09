# 🐙 OCTOPUS LOG BOT — Kurulum Kılavuzu

## 📁 Dosyalar
```
octopus_log_bot/
├── bot.py          ← Ana bot kodu
├── config.py       ← Ayarlar (token, kanallar vs.)
├── database.py     ← SQLite veritabanı
└── requirements.txt
```

---

## ⚙️ KURULUM (VPS / Sunucu)

### 1. Python kur (3.10+)
```bash
sudo apt update && sudo apt install python3 python3-pip -y
```

### 2. Dosyaları yükle
```bash
mkdir octopus_bot && cd octopus_bot
# Dosyaları bu klasöre at
```

### 3. Kütüphaneleri yükle
```bash
pip install -r requirements.txt
```

### 4. config.py'yi düzenle
```python
BOT_TOKEN = "BURAYA_BOT_TOKEN"       # @BotFather'dan al
ADMIN_ID  = 123456789                  # Kendi Telegram ID'n
REQUIRED_CHANNELS = ["@kanal1", ...]  # Kanalların
LOG_SOURCES = ["https://..."]         # Log API'lerin
```

### 5. Botu başlat
```bash
python3 bot.py
```

### 6. Arka planda çalıştır (önerilen)
```bash
# screen ile:
screen -S octopus
python3 bot.py
# CTRL+A D ile çıkabilirsin

# veya systemd ile:
sudo nano /etc/systemd/system/octopus.service
```

**systemd servis dosyası:**
```ini
[Unit]
Description=Octopus Log Bot
After=network.target

[Service]
WorkingDirectory=/root/octopus_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable octopus
sudo systemctl start octopus
```

---

## 💎 VIP — Telegram Stars Kurulumu

1. @BotFather'a git → `/mybots` → botunu seç
2. **Payments** → **Telegram Stars** seç
3. Bot otomatik Stars ödemesi alır
4. Ödeme gelince bot 30 gün VIP verir

---

## 🔧 Admin Komutları

| Komut | Açıklama |
|-------|----------|
| `/istatistik` | Kullanıcı istatistikleri |
| `/vipver USER_ID GÜN` | Manuel VIP ver |
| `/broadcast MESAJ` | Tüm kullanıcılara mesaj |

---

## 🌐 Log API Entegrasyonu

`config.py` içindeki `LOG_SOURCES` listesine kendi API adreslerini yaz.

API'nin döndürmesi beklenen JSON formatı:
```json
{
  "results": [
    {"username": "user@mail.com", "password": "pass123", "url": "site.com"},
    ...
  ]
}
```

`bot.py` içindeki `fetch_logs()` fonksiyonunu API'ne göre düzenleyebilirsin.

---

## 📌 Notlar

- Veritabanı `bot.db` dosyasına otomatik oluşur
- Günlük limitler her gece 00:00'da sıfırlanır
- VIP süresi dolunca otomatik iptal olur
