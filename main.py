import threading
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("🚀 VarezHub başlatılıyor...")

    from varezhub_admin_bot import bot as admin_bot, app
    from market_bot import bot as market_bot

    # Flask API thread
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=8080, debug=False),
        daemon=True
    )
    flask_thread.start()
    print("✅ API başladı")

    # Market botu thread
    market_thread = threading.Thread(
        target=lambda: market_bot.infinity_polling(none_stop=True),
        daemon=True
    )
    market_thread.start()
    print("🛒 Market botu başladı")

    # Admin botu ana thread
    print("🛡️ Admin botu başladı")
    admin_bot.infinity_polling(none_stop=True)
