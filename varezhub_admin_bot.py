import telebot
import sqlite3
import time
import os
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
from telebot import types
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# AYARLAR
# ============================================================
ADMIN_TOKEN = ("8645221526:AAHE8i4y24KisQory-S_mkDDeL7CDU5uX48")
MARKET_TOKEN = ("8694381551:AAHOhVeKArNlOS20lT3437hILT9t9LVSkLE")
ADMINS = [8434939976]
DB_PATH = "nexus_elite_v28.db"           # Market botu ile AYNI DB

bot = telebot.TeleBot(ADMIN_TOKEN, parse_mode="HTML")
app = Flask(__name__)
CORS(app)

# ============================================================
# VERİTABANI
# ============================================================
def get_db():
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db

# ============================================================
# TELEGRAM BOT — /start
# ============================================================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    if uid not in ADMINS:
        bot.send_message(uid, "❌ Bu bot sadece adminlere özeldir.")
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🛡️ Admin Paneli Aç",
        web_app=types.WebAppInfo(url=os.getenv("PANEL_URL", "https://senin-panel-url.com"))
    ))
    kb.add(types.InlineKeyboardButton("📊 Hızlı İstatistik", callback_data="hizli_stats"))

    bot.send_message(uid,
        "👑 <b>VarezHub Admin Bot</b>\n\n"
        "Aşağıdaki butona bas ve admin paneline gir.",
        reply_markup=kb
    )

@bot.message_handler(commands=["stats"])
def stats_cmd(m):
    if m.from_user.id not in ADMINS:
        return
    gonder_stats(m.from_user.id)

@bot.message_handler(commands=["panel"])
def panel_cmd(m):
    if m.from_user.id not in ADMINS:
        return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🛡️ Paneli Aç",
        web_app=types.WebAppInfo(url=os.getenv("PANEL_URL", "https://senin-panel-url.com"))
    ))
    bot.send_message(m.from_user.id, "👆 Paneli açmak için bas:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    uid = call.from_user.id
    if uid not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Yetkin yok.")
        return

    if call.data == "hizli_stats":
        gonder_stats(uid)
        bot.answer_callback_query(call.id)

def gonder_stats(uid):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM users"); total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE banned=0"); active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE banned=1"); banned = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM market_log"); sales = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(fiyat),0) FROM market_log"); rev = c.fetchone()[0]
    db.close()

    bot.send_message(uid,
        f"📊 <b>VarezHub İstatistik</b>\n\n"
        f"👥 Toplam Üye: <b>{total}</b>\n"
        f"✅ Aktif: <b>{active}</b>\n"
        f"🚫 Banlı: <b>{banned}</b>\n"
        f"🛒 Toplam Satış: <b>{sales}</b>\n"
        f"💰 Toplam Gelir: <b>{rev} Ref</b>\n\n"
        f"🕐 {time.strftime('%H:%M:%S')}"
    )

# ============================================================
# FLASK API — Mini App için
# ============================================================
def admin_guard(req):
    """Basit admin kontrolü — initData header'ından"""
    # Geliştirme modunda bypass
    if os.getenv("DEV_MODE") == "1":
        return True
    uid_header = req.headers.get("X-User-Id", "")
    try:
        return int(uid_header) in ADMINS
    except:
        return False

@app.route("/api/stats")
def api_stats():
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    db = get_db()
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM users"); total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE banned=0"); active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE banned=1"); banned = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM market_log"); sales = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(fiyat),0) FROM market_log"); rev = c.fetchone()[0]
    db.close()
    return jsonify({"total": total, "active": active, "banned": banned, "sales": sales, "revenue": rev})

@app.route("/api/users")
def api_users():
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    search = request.args.get("search", "")
    db = get_db()
    c = db.cursor()
    if search:
        c.execute("SELECT id,first_name,ref,davet_sayisi,banned FROM users WHERE CAST(id AS TEXT)=? OR first_name LIKE ? ORDER BY ref DESC LIMIT 100",
                  (search, f"%{search}%"))
    else:
        c.execute("SELECT id,first_name,ref,davet_sayisi,banned FROM users ORDER BY ref DESC LIMIT 100")
    rows = [dict(r) for r in c.fetchall()]
    db.close()
    return jsonify(rows)

@app.route("/api/users/<int:uid>")
def api_user(uid):
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    r = c.fetchone()
    db.close()
    if not r:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404
    return jsonify(dict(r))

@app.route("/api/ban", methods=["POST"])
def api_ban():
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.json
    uid = data.get("user_id")
    db = get_db()
    c = db.cursor()
    c.execute("SELECT first_name FROM users WHERE id=?", (uid,))
    r = c.fetchone()
    if not r:
        db.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404
    c.execute("UPDATE users SET banned=1 WHERE id=?", (uid,))
    db.commit()
    db.close()
    # Kullanıcıya bildir
    try:
        market_bot = telebot.TeleBot(MARKET_TOKEN)
        market_bot.send_message(uid, "🚫 Sisteme erişimin engellendi.")
    except: pass
    return jsonify({"success": True, "name": r["first_name"]})

@app.route("/api/unban", methods=["POST"])
def api_unban():
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.json
    uid = data.get("user_id")
    db = get_db()
    c = db.cursor()
    c.execute("SELECT first_name FROM users WHERE id=?", (uid,))
    r = c.fetchone()
    if not r:
        db.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404
    c.execute("UPDATE users SET banned=0 WHERE id=?", (uid,))
    db.commit()
    db.close()
    try:
        market_bot = telebot.TeleBot(MARKET_TOKEN)
        market_bot.send_message(uid, "✅ Erişimin yeniden açıldı.")
    except: pass
    return jsonify({"success": True, "name": r["first_name"]})

@app.route("/api/addref", methods=["POST"])
def api_addref():
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.json
    uid, amount = data.get("user_id"), data.get("amount", 0)
    db = get_db()
    c = db.cursor()
    c.execute("SELECT first_name FROM users WHERE id=?", (uid,))
    r = c.fetchone()
    if not r:
        db.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404
    c.execute("UPDATE users SET ref = ref + ? WHERE id=?", (amount, uid))
    db.commit()
    db.close()
    return jsonify({"success": True, "name": r["first_name"], "amount": amount})

@app.route("/api/remref", methods=["POST"])
def api_remref():
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.json
    uid, amount = data.get("user_id"), data.get("amount", 0)
    db = get_db()
    c = db.cursor()
    c.execute("SELECT first_name FROM users WHERE id=?", (uid,))
    r = c.fetchone()
    if not r:
        db.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404
    c.execute("UPDATE users SET ref = MAX(0, ref - ?) WHERE id=?", (amount, uid))
    db.commit()
    db.close()
    return jsonify({"success": True, "name": r["first_name"], "amount": amount})

@app.route("/api/deluser", methods=["POST"])
def api_deluser():
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.json
    uid = data.get("user_id")
    db = get_db()
    c = db.cursor()
    c.execute("SELECT first_name FROM users WHERE id=?", (uid,))
    r = c.fetchone()
    if not r:
        db.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    c.execute("DELETE FROM bekleyen_ref WHERE yeni_uye_id=? OR davet_eden_id=?", (uid, uid))
    db.commit()
    db.close()
    return jsonify({"success": True, "name": r["first_name"]})

@app.route("/api/broadcast", methods=["POST"])
def api_broadcast():
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    data = request.json
    msg = data.get("message", "").strip()
    if not msg:
        return jsonify({"error": "Mesaj boş"}), 400
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id FROM users WHERE banned=0")
    users = [r["id"] for r in c.fetchall()]
    db.close()
    market_bot = telebot.TeleBot(MARKET_TOKEN)
    success = 0
    for user_id in users:
        try:
            market_bot.send_message(user_id, f"📢 <b>DUYURU</b>\n\n{msg}", parse_mode="HTML")
            success += 1
            time.sleep(0.05)
        except: pass
    return jsonify({"success": True, "sent": success, "total": len(users)})

@app.route("/api/market_log")
def api_market_log():
    if not admin_guard(request):
        return jsonify({"error": "Yetkisiz"}), 403
    limit = request.args.get("limit", 50, type=int)
    db = get_db()
    c = db.cursor()
    c.execute("""
        SELECT ml.id, ml.user_id, u.first_name, ml.urun, ml.fiyat, ml.tarih
        FROM market_log ml
        LEFT JOIN users u ON ml.user_id = u.id
        ORDER BY ml.tarih DESC LIMIT ?
    """, (limit,))
    rows = [{
        "id": r["id"], "user_id": r["user_id"],
        "name": r["first_name"] or "?",
        "product": r["urun"], "price": r["fiyat"],
        "time": time.strftime("%H:%M", time.localtime(r["tarih"]))
    } for r in c.fetchall()]
    db.close()
    return jsonify(rows)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": time.strftime("%H:%M:%S")})

# ============================================================
# ÇALIŞTIR — Bot + API aynı anda
# ============================================================
if __name__ == "__main__":
    print("🚀 VarezHub Admin Bot + API başlatılıyor...")

    # Flask API ayrı thread'de çalışsın
    api_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5001, debug=False),
        daemon=True
    )
    api_thread.start()
    print("✅ API: http://localhost:5001")

    print("✅ Bot polling başladı...")
    bot.infinity_polling()
  
