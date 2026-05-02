import telebot
import sqlite3
import time
import os
from telebot import types
from dotenv import load_dotenv

load_dotenv()

# --- 👑 AYARLAR ---
TOKEN = ("8694381551:AAHOhVeKArNlOS20lT3437hILT9t9LVSkLE")
ADMINS = [8434939976]

KANALLAR = [
    {"ad": "✈️ 1. Zorunlu Kanal", "id": "-1003920052165", "username": "zeroarsivim"},
    {"ad": "✈️ 2. Zorunlu Kanal", "id": "-1003955733214", "username": "tetikciler_34x"}
]

SATICI_1 = "HollandaBaskan"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
user_states = {}

# --- 📊 VERİTABANI ---
DB_PATH = "nexus_elite_v28.db"

def get_db():
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db

def db_kur():
    db = get_db()
    c = db.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        first_name TEXT,
        ref INTEGER DEFAULT 0,
        davet_sayisi INTEGER DEFAULT 0,
        son_bonus INTEGER DEFAULT 0,
        duyuru_hakki INTEGER DEFAULT 0,
        banned INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS bekleyen_ref (
        yeni_uye_id INTEGER PRIMARY KEY,
        davet_eden_id INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS market_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        urun TEXT,
        fiyat INTEGER,
        tarih INTEGER
    )""")
    db.commit()
    db.close()

db_kur()

# --- 🛡️ KANAL KONTROLÜ ---
def abone_mi(user_id):
    try:
        for kanal in KANALLAR:
            status = bot.get_chat_member(kanal["id"], user_id).status
            if status in ['left', 'kicked', 'restricted']:
                return False
        return True
    except:
        return False

def banli_mi(user_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT banned FROM users WHERE id=?", (user_id,))
    r = c.fetchone()
    db.close()
    return r and r["banned"] == 1

# --- 📱 MENÜLER ---
def zorunlu_kanal_menusu(uid):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for i, k in enumerate(KANALLAR, 1):
        kb.add(types.InlineKeyboardButton(
            f"📍 Adım {i}: {k['ad']}",
            url=f"https://t.me/{k['username']}"
        ))
    kb.add(types.InlineKeyboardButton("⚙️ SİSTEMİ AKTİF ET", callback_data="check_sub"))
    bot.send_message(uid,
        "🛡️ <b>VarezHub Güvenlik Doğrulaması</b>\n\n"
        "Sistemi kullanabilmek için lütfen kanallara katılın.",
        reply_markup=kb
    )

def ana_menu(uid, fname):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT count(id) FROM users WHERE banned=0")
    toplam = c.fetchone()[0]
    db.close()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👤 Profilim", "🛒 Market")
    markup.add("🔗 Referans Linkim", "🏆 Liderlik Tablosu")
    markup.add("🎁 Günlük Hediye", "💬 Destek")

    bot.send_message(uid,
        f"✅ <b>Sistem Aktif!</b>\n"
        f"Hoş geldin <b>{fname}</b> kanka.\n"
        f"Aktif Üye: <b>{toplam}</b>",
        reply_markup=markup
    )

def admin_menu(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 İstatistik", callback_data="admin_stats"),
        types.InlineKeyboardButton("👥 Top Kullanıcı", callback_data="admin_users")
    )
    kb.add(
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🚫 Ban", callback_data="admin_ban")
    )
    kb.add(
        types.InlineKeyboardButton("✅ Unban", callback_data="admin_unban"),
        types.InlineKeyboardButton("➕ Ref Ekle", callback_data="admin_addref")
    )
    kb.add(
        types.InlineKeyboardButton("➖ Ref Sil", callback_data="admin_remref"),
        types.InlineKeyboardButton("🗑️ Kullanıcı Sil", callback_data="admin_deluser")
    )
    kb.add(
        types.InlineKeyboardButton("📦 Market Log", callback_data="admin_marketlog"),
        types.InlineKeyboardButton("🔍 Kullanıcı Ara", callback_data="admin_finduser")
    )
    bot.send_message(uid, "👑 <b>ADMIN PANEL</b>\nNe yapmak istiyorsun?", reply_markup=kb)

# --- Market ---
MARKET_DATA = {
    "📈 Insta Hit": 3,
    "🎮 Pubg Hit": 5,
    "🎨 Özel Logo": 5,
    "💨 Cpm Tool": 7,
    "📸 Insta Tool": 8,
    "💬 Wp Fake N": 10,
    "✈️ Tg Fake N": 15,
    "📞 +90 Fake N": 20,
    "📢 Botta Duyuru": 30,
    "🛡️ Bot Kurulum": 50,
    "🎥 TikTok Hit": 5,
    "🔥 Özel Config": 10,
    "💎 VIP Rolü": 40
}

# --- 🕹️ CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    uid = call.from_user.id

    if banli_mi(uid):
        bot.answer_callback_query(call.id, "🚫 Banlısın!", show_alert=True)
        return

    db = get_db()
    c = db.cursor()

    # --- Kanal kontrolü ---
    if call.data == "check_sub":
        if abone_mi(uid):
            c.execute("SELECT davet_eden_id FROM bekleyen_ref WHERE yeni_uye_id=?", (uid,))
            res = c.fetchone()
            if res:
                c.execute("UPDATE users SET ref = ref + 1, davet_sayisi = davet_sayisi + 1 WHERE id=?", (res["davet_eden_id"],))
                c.execute("DELETE FROM bekleyen_ref WHERE yeni_uye_id=?", (uid,))
                db.commit()
                try:
                    bot.send_message(res["davet_eden_id"], "🎉 <b>Referans Geldi!</b> +1 Puan kazandınız.")
                except:
                    pass
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            ana_menu(uid, call.from_user.first_name)
        else:
            bot.answer_callback_query(call.id, "❌ Kanallara katılmadın kanka!", show_alert=True)
        db.close()
        return

    # --- Market ---
    if call.data.startswith("buy_"):
        idx = int(call.data.split("_")[1])
        urunler = list(MARKET_DATA.items())
        if idx >= len(urunler):
            db.close()
            return
        urun, fiyat = urunler[idx]
        c.execute("SELECT ref FROM users WHERE id=?", (uid,))
        res = c.fetchone()
        if not res or res["ref"] < fiyat:
            bot.answer_callback_query(call.id, "❌ Puanın yetersiz kanka!", show_alert=True)
            db.close()
            return

        if urun == "📢 Botta Duyuru":
            c.execute("UPDATE users SET ref = ref - ?, duyuru_hakki = 1 WHERE id=?", (fiyat, uid))
            db.commit()
            bot.send_message(uid, "📢 <b>Duyuru Hakkı Aktif!</b> Mesajını buraya yaz kanka.")
            user_states[uid] = "waiting_announcement"
        else:
            c.execute("UPDATE users SET ref = ref - ? WHERE id=?", (fiyat, uid))
            c.execute("INSERT INTO market_log (user_id, urun, fiyat, tarih) VALUES (?,?,?,?)",
                      (uid, urun, fiyat, int(time.time())))
            db.commit()
            bot.send_message(uid, f"🎉 <b>{urun}</b> satın alındı! @{SATICI_1} sana ulaşacak.")
        db.close()
        return

    # --- Admin callbacks ---
    if uid not in ADMINS:
        db.close()
        return

    if call.data == "admin_stats":
        c.execute("SELECT count(id) FROM users")
        total = c.fetchone()[0]
        c.execute("SELECT count(id) FROM users WHERE banned=1")
        banned = c.fetchone()[0]
        c.execute("SELECT count(id) FROM market_log")
        sales = c.fetchone()[0]
        c.execute("SELECT sum(fiyat) FROM market_log")
        rev = c.fetchone()[0] or 0
        bot.send_message(uid,
            f"📊 <b>İstatistik</b>\n\n"
            f"👥 Toplam Üye: <b>{total}</b>\n"
            f"🚫 Banlı: <b>{banned}</b>\n"
            f"🛒 Satış: <b>{sales}</b>\n"
            f"💰 Toplam Gelir: <b>{rev} Ref</b>"
        )

    elif call.data == "admin_users":
        c.execute("SELECT id, first_name, ref, davet_sayisi FROM users ORDER BY ref DESC LIMIT 10")
        rows = c.fetchall()
        txt = "👥 <b>Top 10 Kullanıcı</b>\n\n"
        for i, r in enumerate(rows, 1):
            txt += f"{i}. <b>{r['first_name']}</b> | 💰{r['ref']} Ref | 👥{r['davet_sayisi']} Davet\n"
        bot.send_message(uid, txt or "Liste boş.")

    elif call.data == "admin_broadcast":
        user_states[uid] = "broadcast"
        bot.send_message(uid, "📢 Broadcast mesajını yaz:")

    elif call.data == "admin_ban":
        user_states[uid] = "ban"
        bot.send_message(uid, "🚫 Banlanacak kullanıcı ID'sini yaz:")

    elif call.data == "admin_unban":
        user_states[uid] = "unban"
        bot.send_message(uid, "✅ Unban yapılacak kullanıcı ID'sini yaz:")

    elif call.data == "admin_addref":
        user_states[uid] = "addref"
        bot.send_message(uid, "➕ Format: <code>USER_ID MIKTAR</code>")

    elif call.data == "admin_remref":
        user_states[uid] = "remref"
        bot.send_message(uid, "➖ Format: <code>USER_ID MIKTAR</code>")

    elif call.data == "admin_deluser":
        user_states[uid] = "deluser"
        bot.send_message(uid, "🗑️ Silinecek kullanıcı ID'sini yaz:")

    elif call.data == "admin_marketlog":
        c.execute("SELECT user_id, urun, fiyat, tarih FROM market_log ORDER BY id DESC LIMIT 10")
        rows = c.fetchall()
        txt = "📦 <b>Son 10 Satış</b>\n\n"
        for r in rows:
            t = time.strftime('%d.%m %H:%M', time.localtime(r["tarih"]))
            txt += f"👤 <code>{r['user_id']}</code> | {r['urun']} | {r['fiyat']} Ref | {t}\n"
        bot.send_message(uid, txt or "Log boş.")

    elif call.data == "admin_finduser":
        user_states[uid] = "finduser"
        bot.send_message(uid, "🔍 Kullanıcı ID'si yaz:")

    db.close()

# --- 🚀 MESAJ İŞLEYİCİ ---
@bot.message_handler(commands=["start"])
def start_handler(m):
    uid = m.from_user.id
    fname = m.from_user.first_name

    if banli_mi(uid):
        bot.send_message(uid, "🚫 Sisteme erişimin engellenmiş.")
        return

    db = get_db()
    c = db.cursor()
    c.execute("SELECT id FROM users WHERE id=?", (uid,))
    if not c.fetchone():
        parts = m.text.split()
        ref_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        c.execute("INSERT INTO users (id, first_name) VALUES (?,?)", (uid, fname))
        if ref_id and ref_id != uid:
            c.execute("INSERT OR REPLACE INTO bekleyen_ref VALUES (?,?)", (uid, ref_id))
        db.commit()
    db.close()

    if not abone_mi(uid):
        zorunlu_kanal_menusu(uid)
    else:
        ana_menu(uid, fname)

@bot.message_handler(commands=["admin"])
def admin_cmd(m):
    if m.from_user.id not in ADMINS:
        bot.send_message(m.from_user.id, "❌ Yetkin yok.")
        return
    admin_menu(m.from_user.id)

@bot.message_handler(func=lambda m: True)
def text_handler(m):
    uid = m.from_user.id
    fname = m.from_user.first_name

    if banli_mi(uid):
        bot.send_message(uid, "🚫 Sisteme erişimin engellenmiş.")
        return

    db = get_db()
    c = db.cursor()

    # --- Admin state işlemleri ---
    if uid in user_states:
        state = user_states[uid]

        if state == "broadcast":
            c.execute("SELECT id FROM users WHERE banned=0")
            users = c.fetchall()
            basarili = 0
            for u in users:
                try:
                    bot.send_message(u["id"], f"📢 <b>DUYURU</b>\n\n{m.text}")
                    basarili += 1
                    time.sleep(0.05)
                except:
                    pass
            bot.send_message(uid, f"✅ Broadcast tamamlandı. {basarili}/{len(users)} kişiye ulaştı.")
            del user_states[uid]
            db.close()
            return

        if state == "ban":
            try:
                target = int(m.text)
                c.execute("UPDATE users SET banned=1 WHERE id=?", (target,))
                db.commit()
                bot.send_message(uid, f"🚫 <code>{target}</code> banlandı.")
                try:
                    bot.send_message(target, "🚫 Sisteme erişimin engellendi.")
                except:
                    pass
            except:
                bot.send_message(uid, "❌ Geçersiz ID.")
            del user_states[uid]
            db.close()
            return

        if state == "unban":
            try:
                target = int(m.text)
                c.execute("UPDATE users SET banned=0 WHERE id=?", (target,))
                db.commit()
                bot.send_message(uid, f"✅ <code>{target}</code> unban edildi.")
            except:
                bot.send_message(uid, "❌ Geçersiz ID.")
            del user_states[uid]
            db.close()
            return

        if state == "addref":
            try:
                parts = m.text.split()
                target, amount = int(parts[0]), int(parts[1])
                c.execute("UPDATE users SET ref = ref + ? WHERE id=?", (amount, target))
                db.commit()
                bot.send_message(uid, f"➕ <code>{target}</code> kullanıcısına {amount} ref eklendi.")
            except:
                bot.send_message(uid, "❌ Format: USER_ID MIKTAR")
            del user_states[uid]
            db.close()
            return

        if state == "remref":
            try:
                parts = m.text.split()
                target, amount = int(parts[0]), int(parts[1])
                c.execute("UPDATE users SET ref = MAX(0, ref - ?) WHERE id=?", (amount, target))
                db.commit()
                bot.send_message(uid, f"➖ <code>{target}</code> kullanıcısından {amount} ref silindi.")
            except:
                bot.send_message(uid, "❌ Format: USER_ID MIKTAR")
            del user_states[uid]
            db.close()
            return

        if state == "deluser":
            try:
                target = int(m.text)
                c.execute("DELETE FROM users WHERE id=?", (target,))
                c.execute("DELETE FROM bekleyen_ref WHERE yeni_uye_id=? OR davet_eden_id=?", (target, target))
                db.commit()
                bot.send_message(uid, f"🗑️ <code>{target}</code> silindi.")
            except:
                bot.send_message(uid, "❌ Geçersiz ID.")
            del user_states[uid]
            db.close()
            return

        if state == "finduser":
            try:
                target = int(m.text)
                c.execute("SELECT * FROM users WHERE id=?", (target,))
                r = c.fetchone()
                if r:
                    durum = "🚫 Banlı" if r["banned"] else "✅ Aktif"
                    bot.send_message(uid,
                        f"🔍 <b>Kullanıcı Bilgisi</b>\n\n"
                        f"🆔 ID: <code>{r['id']}</code>\n"
                        f"👤 İsim: {r['first_name']}\n"
                        f"💰 Ref: {r['ref']}\n"
                        f"👥 Davet: {r['davet_sayisi']}\n"
                        f"📊 Durum: {durum}"
                    )
                else:
                    bot.send_message(uid, "❌ Kullanıcı bulunamadı.")
            except:
                bot.send_message(uid, "❌ Geçersiz ID.")
            del user_states[uid]
            db.close()
            return

        if state == "waiting_announcement":
            c.execute("SELECT duyuru_hakki FROM users WHERE id=?", (uid,))
            hak = c.fetchone()
            if hak and hak["duyuru_hakki"] > 0:
                c.execute("UPDATE users SET duyuru_hakki = 0 WHERE id=?", (uid,))
                db.commit()
                del user_states[uid]
                c.execute("SELECT id FROM users WHERE banned=0")
                all_u = c.fetchall()
                for u in all_u:
                    try:
                        bot.send_message(u["id"], f"📢 <b>ÜYE DUYURUSU</b>\n\n{m.text}")
                        time.sleep(0.04)
                    except:
                        pass
                bot.send_message(uid, "✅ Duyurun tüm üyelere gönderildi!")
            db.close()
            return

    # --- Normal butonlar ---
    if m.text == "👤 Profilim":
        c.execute("SELECT ref, davet_sayisi FROM users WHERE id=?", (uid,))
        res = c.fetchone()
        if res:
            bot.send_message(uid,
                f"👤 <b>Profilim</b>\n\n"
                f"🆔 ID: <code>{uid}</code>\n"
                f"💰 Bakiye: <b>{res['ref']} Ref</b>\n"
                f"👥 Davet: <b>{res['davet_sayisi']}</b>"
            )

    elif m.text == "🎁 Günlük Hediye":
        c.execute("SELECT son_bonus FROM users WHERE id=?", (uid,))
        row = c.fetchone()
        if row:
            su_an = int(time.time())
            if su_an - row["son_bonus"] > 86400:
                c.execute("UPDATE users SET ref = ref + 1, son_bonus = ? WHERE id=?", (su_an, uid))
                db.commit()
                bot.send_message(uid, "🎉 Günlük bonusun eklendi! +1 Ref kazandın.")
            else:
                kalan = 86400 - (su_an - row["son_bonus"])
                saat = kalan // 3600
                dakika = (kalan % 3600) // 60
                bot.send_message(uid, f"⏳ Sonraki bonus için <b>{saat}s {dakika}dk</b> bekle.")

    elif m.text == "🛒 Market":
        kb = types.InlineKeyboardMarkup(row_width=2)
        btns = [
            types.InlineKeyboardButton(f"{u} ({f} Ref)", callback_data=f"buy_{i}")
            for i, (u, f) in enumerate(MARKET_DATA.items())
        ]
        kb.add(*btns)
        bot.send_message(uid, "🛒 <b>VarezHub Market</b>", reply_markup=kb)

    elif m.text == "🔗 Referans Linkim":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid, f"🔗 <b>Referans Linkin:</b>\n<code>{link}</code>")

    elif m.text == "🏆 Liderlik Tablosu":
        c.execute("SELECT first_name, davet_sayisi FROM users WHERE davet_sayisi > 0 AND banned=0 ORDER BY davet_sayisi DESC LIMIT 10")
        rows = c.fetchall()
        madalyalar = ["🥇", "🥈", "🥉"]
        lb = "🏆 <b>Top 10 Listesi</b>\n\n"
        for i, r in enumerate(rows, 1):
            medal = madalyalar[i-1] if i <= 3 else f"{i}."
            lb += f"{medal} {r['first_name']} — <b>{r['davet_sayisi']} Davet</b>\n"
        bot.send_message(uid, lb if rows else "Liste boş.")

    elif m.text == "💬 Destek":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("👤 Kurucu", url=f"https://t.me/{SATICI_1}"))
        bot.send_message(uid, "🆘 <b>Destek için:</b>", reply_markup=kb)

    db.close()

print("🚀 Bot başlatılıyor...")
bot.infinity_polling()
  
