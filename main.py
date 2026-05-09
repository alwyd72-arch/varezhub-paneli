import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
import database as db
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ─────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────

async def check_membership(user_id: int) -> bool:
    """Kullanıcının zorunlu kanallara üye olup olmadığını kontrol et"""
    for channel in config.REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked", "banned"]:
                return False
        except Exception:
            return False
    return True

def get_join_keyboard():
    """Kanal katılım butonları"""
    buttons = []
    for i, (channel, name) in enumerate(zip(config.REQUIRED_CHANNELS, config.CHANNEL_NAMES)):
        buttons.append([InlineKeyboardButton(text=f"📢 {name}", url=f"https://t.me/{channel.lstrip('@')}")])
    buttons.append([InlineKeyboardButton(text="✅ Katıldım, devam et", callback_data="check_membership")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_keyboard(is_vip=False):
    """Ana menü inline klavyesi"""
    vip_text = "💎 VIP MODU AKTİF" if is_vip else "💎 VIP AL"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚙️ Komutlar", callback_data="commands"),
            InlineKeyboardButton(text="👤 Hakkımızda", callback_data="about"),
        ],
        [InlineKeyboardButton(text=vip_text, callback_data="buy_vip" if not is_vip else "vip_info")],
    ])

async def fetch_logs(domain: str, source_num: int = 0) -> str:
    """
    Log çekme fonksiyonu.
    source_num=0 → ücretsiz kaynak
    source_num=1..4 → VIP kaynaklar
    
    NOT: Buraya kendi log API'nizi veya veritabanı sorgularınızı entegre edin.
    Şu an örnek/demo veri döndürüyor.
    """
    sources = config.LOG_SOURCES
    if source_num >= len(sources):
        return None
    
    source_url = sources[source_num]
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                source_url,
                params={"domain": domain, "key": config.API_KEY},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # API'nizin döndürdüğü formata göre düzenleyin
                    results = data.get("results", [])
                    if not results:
                        return None
                    lines = []
                    for r in results[:20]:  # max 20 sonuç
                        user = r.get("username", r.get("user", ""))
                        pwd  = r.get("password", r.get("pass", ""))
                        url  = r.get("url", domain)
                        if user and pwd:
                            lines.append(f"{url}:{user}:{pwd}")
                    return "\n".join(lines) if lines else None
                return None
    except Exception as e:
        logger.error(f"Log çekme hatası ({domain}): {e}")
        return None

def clean_url(text: str) -> str:
    """URL temizleme: tracking parametrelerini kaldır"""
    import re
    # UTM parametrelerini temizle
    text = re.sub(r'\?utm_[^&\s]+(&[^&\s]+)*', '', text)
    text = re.sub(r'&utm_[^&\s]+', '', text)
    # Diğer tracking parametreler
    text = re.sub(r'\?(fbclid|gclid|ref|source)=[^&\s]+(&[^&\s]+)*', '', text)
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else "Temizlenecek URL bulunamadı."

# ─────────────────────────────────────────
# /start KOMUTU
# ─────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Kullanıcı"
    first_name = message.from_user.first_name or username

    # Kullanıcıyı kaydet
    db.add_user(user_id, username)

    # Kanal üyeliği kontrolü
    is_member = await check_membership(user_id)
    if not is_member:
        await message.answer(
            "🚫 Botu kullanmak için tüm kanallara katılmalısınız!\n\n"
            "✅ Katıldıktan sonra tekrar /start yazın.\n\n"
            f"📌 Katılmanız gereken kanal sayısı: {len(config.REQUIRED_CHANNELS)}",
            reply_markup=get_join_keyboard()
        )
        return

    is_vip = db.is_vip(user_id)
    vip_badge = " 💎" if is_vip else ""

    await message.answer(
        f"👋 Hoş geldin <b>{first_name}{vip_badge}</b>!\n\n"
        "Log kaynaklarından istediğiniz hesabı çekmek için komutları kullanın.",
        reply_markup=get_main_keyboard(is_vip),
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# KANAl ÜYELİK CALLBACK
# ─────────────────────────────────────────

@dp.callback_query(F.data == "check_membership")
async def check_membership_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_member = await check_membership(user_id)
    
    if is_member:
        is_vip = db.is_vip(user_id)
        first_name = callback.from_user.first_name or "Kullanıcı"
        await callback.message.edit_text(
            f"👋 Hoş geldin <b>{first_name}</b>!\n\n"
            "Log kaynaklarından istediğiniz hesabı çekmek için komutları kullanın.",
            reply_markup=get_main_keyboard(is_vip),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Henüz tüm kanallara katılmadınız!", show_alert=True)

# ─────────────────────────────────────────
# HAKKIMIZDA
# ─────────────────────────────────────────

@dp.callback_query(F.data == "about")
async def about_callback(callback: types.CallbackQuery):
    text = (
        "┌─────────────────┐\n"
        "│    📖 HAKKIMIZDA    │\n"
        "└─────────────────┘\n\n"
        f"🧑‍💻 Yapımcı: @{config.ADMIN_USERNAME}\n\n"
        "📌 Özellikler:\n"
        "✅ 7/24 kesintisiz hizmet\n"
        "✅ Günlük log güncellemesi\n"
        "✅ 5 farklı log kaynağı\n"
        "✅ Hızlı arama algoritması\n"
        "✅ Link temizleme aracı\n"
        "✅ Akıllı önbellek sistemi\n\n"
        "💎 VIP Avantajları:\n"
        "💠 Sınırsız çekim hakkı\n"
        "💠 4 ekstra log kaynağı\n"
        "💠 Öncelikli destek"
    )
    back_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=back_btn)

# ─────────────────────────────────────────
# KOMUT LİSTESİ
# ─────────────────────────────────────────

@dp.callback_query(F.data == "commands")
async def commands_callback(callback: types.CallbackQuery):
    text = (
        "┌─────────────────┐\n"
        "│  🧵 KOMUT LİSTESİ  │\n"
        "└─────────────────┘\n\n"
        "🗂 Log Çekme Komutları\n\n"
        "⚡ /log site.com\n"
        "└ Ücretsiz log kaynağı\n\n"
        "⚡ /viplog1 site.com\n"
        "└ VIP 1. ekstra kaynak\n\n"
        "⚡ /viplog2 site.com\n"
        "└ VIP 2. ekstra kaynak\n\n"
        "⚡ /viplog3 site.com\n"
        "└ VIP 3. ekstra kaynak\n\n"
        "⚡ /viplog4 site.com\n"
        "└ VIP 4. ekstra kaynak\n\n"
        "🔧 Araçlar\n"
        "⚡ /urltemizle → Link temizleme\n\n"
        "📌 Free: 4 çekim/gün\n"
        "💎 VIP: Sınırsız çekim"
    )
    back_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=back_btn)

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery):
    is_vip = db.is_vip(callback.from_user.id)
    first_name = callback.from_user.first_name or "Kullanıcı"
    await callback.message.edit_text(
        f"👋 Hoş geldin <b>{first_name}</b>!\n\n"
        "Log kaynaklarından istediğiniz hesabı çekmek için komutları kullanın.",
        reply_markup=get_main_keyboard(is_vip),
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# VIP SATIN ALMA — Telegram Stars (15 ⭐)
# ─────────────────────────────────────────

@dp.callback_query(F.data == "buy_vip")
async def buy_vip_callback(callback: types.CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="💎 VIP Üyelik — Aylık",
        description=(
            "✅ Sınırsız log çekme\n"
            "✅ 4 ekstra VIP kaynağa erişim\n"
            "✅ Öncelikli destek\n"
            "✅ 30 gün geçerli"
        ),
        payload="vip_monthly",
        currency="XTR",           # Telegram Stars
        prices=[LabeledPrice(label="VIP Üyelik (30 gün)", amount=15)],
        provider_token="",         # Stars için boş bırakılır
    )
    await callback.answer()

@dp.callback_query(F.data == "vip_info")
async def vip_info_callback(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    expire = user.get("vip_expire", "")
    await callback.answer(f"💎 VIP aktif! Bitiş: {expire}", show_alert=True)

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    user_id = message.from_user.id
    expire_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    db.set_vip(user_id, expire_date)

    # Admin'e bildir
    try:
        await bot.send_message(
            config.ADMIN_ID,
            f"💎 Yeni VIP satışı!\n"
            f"👤 @{message.from_user.username} ({user_id})\n"
            f"💰 15 ⭐ Stars\n"
            f"📅 Bitiş: {expire_date}"
        )
    except Exception:
        pass

    await message.answer(
        "🎉 <b>VIP satın alındı!</b>\n\n"
        f"💎 VIP üyeliğiniz aktif edildi.\n"
        f"📅 Bitiş tarihi: <b>{expire_date}</b>\n\n"
        "Artık tüm VIP komutlarını kullanabilirsiniz!",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_vip=True)
    )

# ─────────────────────────────────────────
# /log KOMUTU — Ücretsiz
# ─────────────────────────────────────────

@dp.message(Command("log"))
async def cmd_log(message: types.Message):
    user_id = message.from_user.id

    if not await check_membership(user_id):
        await message.answer("🚫 Önce kanallara katılın!", reply_markup=get_join_keyboard())
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚡ Kullanım: /log site.com")
        return

    domain = args[1].strip().lower().replace("https://", "").replace("http://", "").strip("/")

    # Günlük limit kontrolü (Free: 4/gün)
    if not db.is_vip(user_id):
        count = db.get_daily_count(user_id)
        if count >= config.FREE_DAILY_LIMIT:
            await message.answer(
                f"⛔ Günlük ücretsiz limitiniz doldu! ({config.FREE_DAILY_LIMIT}/gün)\n\n"
                "💎 VIP alarak sınırsız çekim yapabilirsiniz.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💎 VIP AL — 15 ⭐", callback_data="buy_vip")]
                ])
            )
            return

    wait_msg = await message.answer(f"⏳ <b>{domain}</b> için log aranıyor...", parse_mode="HTML")

    result = await fetch_logs(domain, source_num=0)
    db.inc_daily_count(user_id)

    await wait_msg.delete()

    if result:
        # Dosya olarak gönder
        filename = f"{domain}_logs.txt"
        content = (
            f"🌐 Domain: {domain}\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"📦 Kaynak: Ücretsiz Kaynak\n"
            f"{'─'*40}\n\n"
            f"{result}"
        )
        file_bytes = content.encode("utf-8")
        from aiogram.types import BufferedInputFile
        await message.answer_document(
            BufferedInputFile(file_bytes, filename=filename),
            caption=f"✅ <b>{domain}</b> için log bulundu!\n📄 {len(result.splitlines())} kayıt",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ <b>{domain}</b> için log bulunamadı.\n\n"
            "💡 VIP kaynaklarını deneyin: /viplog1 /viplog2",
            parse_mode="HTML"
        )

# ─────────────────────────────────────────
# /viplog1 - /viplog4 KOMUTLARI — VIP
# ─────────────────────────────────────────

async def handle_viplog(message: types.Message, source_num: int):
    user_id = message.from_user.id

    if not await check_membership(user_id):
        await message.answer("🚫 Önce kanallara katılın!", reply_markup=get_join_keyboard())
        return

    if not db.is_vip(user_id):
        await message.answer(
            f"💎 Bu komut sadece VIP üyelere özel!\n\n"
            "VIP almak için aşağıdaki butona tıklayın:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 VIP AL — 15 ⭐", callback_data="buy_vip")]
            ])
        )
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"⚡ Kullanım: /viplog{source_num} site.com")
        return

    domain = args[1].strip().lower().replace("https://", "").replace("http://", "").strip("/")
    wait_msg = await message.answer(f"⚡ <b>VIP Kaynak {source_num}</b> — <b>{domain}</b> aranıyor...", parse_mode="HTML")

    result = await fetch_logs(domain, source_num=source_num)
    await wait_msg.delete()

    if result:
        filename = f"{domain}_viplog{source_num}.txt"
        content = (
            f"🌐 Domain: {domain}\n"
            f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"💎 Kaynak: VIP Kaynak {source_num}\n"
            f"{'─'*40}\n\n"
            f"{result}"
        )
        from aiogram.types import BufferedInputFile
        await message.answer_document(
            BufferedInputFile(content.encode("utf-8"), filename=filename),
            caption=f"✅ <b>VIP Kaynak {source_num}</b> — <b>{domain}</b>\n📄 {len(result.splitlines())} kayıt",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ VIP Kaynak {source_num}'de <b>{domain}</b> için log bulunamadı.",
            parse_mode="HTML"
        )

@dp.message(Command("viplog1"))
async def cmd_viplog1(message: types.Message): await handle_viplog(message, 1)

@dp.message(Command("viplog2"))
async def cmd_viplog2(message: types.Message): await handle_viplog(message, 2)

@dp.message(Command("viplog3"))
async def cmd_viplog3(message: types.Message): await handle_viplog(message, 3)

@dp.message(Command("viplog4"))
async def cmd_viplog4(message: types.Message): await handle_viplog(message, 4)

# ─────────────────────────────────────────
# /urltemizle KOMUTU
# ─────────────────────────────────────────

@dp.message(Command("urltemizle"))
async def cmd_urltemizle(message: types.Message):
    if not await check_membership(message.from_user.id):
        await message.answer("🚫 Önce kanallara katılın!", reply_markup=get_join_keyboard())
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "⚡ Kullanım: /urltemizle [URL veya metin]\n\n"
            "Örnek:\n/urltemizle https://site.com?utm_source=google&fbclid=abc123"
        )
        return

    raw = args[1].strip()
    cleaned = clean_url(raw)
    await message.answer(
        f"🔗 <b>Temizlenen URL:</b>\n\n"
        f"<code>{cleaned}</code>",
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# ADMİN KOMUTLARI
# ─────────────────────────────────────────

@dp.message(Command("istatistik"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    stats = db.get_stats()
    await message.answer(
        f"📊 <b>Bot İstatistikleri</b>\n\n"
        f"👥 Toplam kullanıcı: {stats['total_users']}\n"
        f"💎 VIP kullanıcı: {stats['vip_users']}\n"
        f"📈 Bugün aktif: {stats['today_active']}\n"
        f"🔍 Bugün log çekme: {stats['today_queries']}",
        parse_mode="HTML"
    )

@dp.message(Command("vipver"))
async def cmd_give_vip(message: types.Message):
    """Admin: /vipver user_id gün"""
    if message.from_user.id != config.ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Kullanım: /vipver user_id gün_sayısı")
        return
    try:
        target_id = int(parts[1])
        days = int(parts[2])
        expire = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        db.set_vip(target_id, expire)
        await message.answer(f"✅ {target_id} kullanıcısına {days} günlük VIP verildi.")
        await bot.send_message(target_id, f"💎 VIP üyeliğiniz aktif edildi! Bitiş: {expire}")
    except Exception as e:
        await message.answer(f"Hata: {e}")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    """Admin: /broadcast mesaj"""
    if message.from_user.id != config.ADMIN_ID:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Kullanım: /broadcast mesaj")
        return
    text = args[1]
    users = db.get_all_users()
    success, fail = 0, 0
    for uid in users:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
    await message.answer(f"📢 Broadcast tamamlandı!\n✅ {success} başarılı\n❌ {fail} başarısız")

# ─────────────────────────────────────────
# BAŞLAT
# ─────────────────────────────────────────

async def main():
    logger.info("Bot başlatılıyor...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
