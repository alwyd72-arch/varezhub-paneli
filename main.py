"""
VarezHub — Ana Başlatıcı
Railway'de bu dosya çalışır, hem market botunu hem admin botunu başlatır.
"""
import threading
import os
from dotenv import load_dotenv

load_dotenv()

def run_market_bot():
    print("🛒 Market botu başlatılıyor...")
    import market_bot

def run_admin_bot():
    print("🛡️ Admin botu + API başlatılıyor...")
    import varezhub_admin_bot

if __name__ == "__main__":
    print("🚀 VarezHub başlatılıyor...")

    # Market botunu ayrı thread'de çalıştır
    t1 = threading.Thread(target=run_market_bot, daemon=True)
    t1.start()

    # Admin botu + Flask API ana thread'de çalışsın
    run_admin_bot()
    
