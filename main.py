import threading
import os
from dotenv import load_dotenv

load_dotenv()

def run_market_bot():
    print("🛒 Market botu başlatılıyor...")
    from market_bot import bot
    bot.infinity_polling(none_stop=True)

def run_admin_bot():
    print("🛡️ Admin botu başlatılıyor...")
    from varezhub_admin_bot import bot as admin_bot, app
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5001, debug=False),
        daemon=True
    )
    flask_thread.start()
    print("✅ API başladı")
    admin_bot.infinity_polling(none_stop=True)

if __name__ == "__main__":
    print("🚀 VarezHub başlatılıyor...")
    t1 = threading.Thread(target=run_market_bot, daemon=True)
    t1.start()
    run_admin_bot()
