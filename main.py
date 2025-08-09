import asyncio
import os
import textwrap
from typing import List

import feedparser
import httpx
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set. Put it in .env")

# Джерела
MVA_NEWS_URL = os.getenv("MVA_NEWS_URL", "").strip()
RSS_MINVETERANS = os.getenv("RSS_MINVETERANS", "").strip()
RSS_CITY_DNIPRO = os.getenv("RSS_CITY_DNIPRO", "").strip()

FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "").strip()
FACEBOOK_TOKEN = os.getenv("FACEBOOK_TOKEN", "").strip()
FACEBOOK_POST_LIMIT = int(os.getenv("FACEBOOK_POST_LIMIT", "5"))

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ---------- Тексти ----------
WELCOME = (
    "👋 Вітаємо в чатботі Управління ветеранської політики м. Дніпро!\n"
    "Обери розділ у меню нижче."
)

ABOUT_TEXT = "ℹ️ <b>Про нас</b>\nОберіть підрозділ:"
ABOUT_SUBTEXT = {
    "mission": "🎯 <b>Місія та візія</b>\nКороткий опис місії, цілей та принципів роботи.",
    "contacts": "📞 <b>Контакти та адреса</b>\n• Адреса: ...\n• Телефон: ...\n• Email: ...",
    "schedule": "🗓 <b>Графік прийому</b>\n• Пн-Пт: ...\n• Сб-Нд: вихідні",
}

SERVICES_TEXT = "🧩 <b>Послуги та підтримка</b>\nОберіть підрозділ:"
PROGRAMS_TEXT = "🏛 <b>Програми та проєкти</b>\nОберіть підрозділ:"
NEWS_TEXT = "🗞 <b>Новини та події</b>\nОберіть джерело:"
PSYCH_TEXT = "🧠 <b>Психологічна підтримка</b>\nОберіть підрозділ:"
LEGAL_TEXT = "⚖️ <b>Юридична допомога</b>\nОберіть підрозділ:"
FAQ_TEXT = "❓ <b>FAQ</b>\nОберіть підрозділ:"
FEEDBACK_TEXT = "✉️ <b>Зворотний зв’язок</b>\nОберіть підрозділ:"

LEGAL_CONTACTS = textwrap.dedent("""
📌 <b>БФ «Право на захист»</b>
🌐 https://r2p.org.ua/

📌 <b>ГО «Січ»</b>
🌐 https://sich-pravo.org/
""").strip()

# ---------- Клавіатури ----------
def main_menu_kb() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="1⃣ Про нас"), KeyboardButton(text="2⃣ Послуги та підтримка")],
        [KeyboardButton(text="3⃣ Програми та проекти"), KeyboardButton(text="4⃣ Новини та події")],
        [KeyboardButton(text="5⃣ Психологічна підтримка"), KeyboardButton(text="6⃣ Юридична допомога")],
        [KeyboardButton(text="7⃣ FAQ"), KeyboardButton(text="8⃣ Зворотний зв’язок")],
        [KeyboardButton(text="🔍 Пошук"), KeyboardButton(text="📍 Найближчі ветеранські центри")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def about_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1.1 Місія та візія", callback_data="about:mission")],
        [InlineKeyboardButton(text="1.2 Контакти та адреса", callback_data="about:contacts")],
        [InlineKeyboardButton(text="1.3 Графік прийому", callback_data="about:schedule")],
        [InlineKeyboardButton(text="⬅ Головне меню", callback_data="nav:home")],
    ])

def services_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2.1 Перелік послуг", callback_data="svc:list")],
        [InlineKeyboardButton(text="2.2 Статус УБД / інвалід війни", callback_data="svc:status")],
        [InlineKeyboardButton(text="2.3 Соціальні консультації", callback_data="svc:social")],
        [InlineKeyboardButton(text="2.4 Медична та психологічна допомога", callback_data="svc:medpsych")],
        [InlineKeyboardButton(text="2.5 Юридичні консультації", callback_data="svc:legal")],
        [InlineKeyboardButton(text="2.6 Профперепідготовка", callback_data="svc:retrain")],
        [InlineKeyboardButton(text="2.7 Запис на прийом 📅", callback_data="svc:appointment")],
        [InlineKeyboardButton(text="⬅ Головне меню", callback_data="nav:home")],
    ])

def programs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="3.1 Поточні програми підтримки", callback_data="prog:current")],
        [InlineKeyboardButton(text="3.2 Гранти та пільги", callback_data="prog:grants")],
        [InlineKeyboardButton(text="3.3 Навчальні курси", callback_data="prog:courses")],
        [InlineKeyboardButton(text="3.4 Спортивні заходи", callback_data="prog:sport")],
        [InlineKeyboardButton(text="3.5 Культурні та соціальні події", callback_data="prog:culture")],
        [InlineKeyboardButton(text="3.6 Працевлаштування ветеранів", callback_data="prog:jobs")],
        [InlineKeyboardButton(text="3.7 Менторські та волонтерські ініціативи", callback_data="prog:mentor")],
        [InlineKeyboardButton(text="⬅ Головне меню", callback_data="nav:home")],
    ])

def news_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4.1 Анонси заходів (місто)", callback_data="news:city")],
        [InlineKeyboardButton(text="4.2 Останні новини (Мінветеранів)", callback_data="news:minv")],
        [InlineKeyboardButton(text="4.3 Facebook Управління", callback_data="news:fb")],
        [InlineKeyboardButton(text="⬅ Головне меню", callback_data="nav:home")],
    ])

def psych_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5.1 Екстрена допомога (гарячі лінії)", callback_data="psy:hotlines")],
        [InlineKeyboardButton(text="5.2 Онлайн-чат з психологом", callback_data="psy:chat")],
        [InlineKeyboardButton(text="5.3 Запис на консультацію", callback_data="psy:appointment")],
        [InlineKeyboardButton(text="5.4 Статті та відео по адаптації", callback_data="psy:materials")],
        [InlineKeyboardButton(text="⬅ Головне меню", callback_data="nav:home")],
    ])

def legal_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="6.1 Зразки заяв та документів", callback_data="law:templates")],
        [InlineKeyboardButton(text="6.2 Як оформити пільги", callback_data="law:benefits")],
        [InlineKeyboardButton(text="6.3 Контакти юристів", callback_data="law:contacts")],
        [InlineKeyboardButton(text="⬅ Головне меню", callback_data="nav:home")],
    ])

def faq_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="7.1 Поширені питання", callback_data="faq:common")],
        [InlineKeyboardButton(text="7.2 Задати питання оператору", callback_data="faq:operator")],
        [InlineKeyboardButton(text="⬅ Головне меню", callback_data="nav:home")],
    ])

def feedback_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="8.1 Повідомити про проблему", callback_data="fb:issue")],
        [InlineKeyboardButton(text="8.2 Залишити відгук", callback_data="fb:review")],
        [InlineKeyboardButton(text="8.3 Подати пропозицію", callback_data="fb:suggest")],
        [InlineKeyboardButton(text="⬅ Головне меню", callback_data="nav:home")],
    ])

# ---------- Утиліти для новин ----------
async def fetch_rss(feed_url: str, limit: int = 5) -> List[str]:
    if not feed_url:
        return ["⚠️ RSS-стрічка не налаштована."]
    try:
        parsed = feedparser.parse(feed_url)
        items = []
        for entry in parsed.entries[:limit]:
            title = entry.get("title", "Без назви")
            link = entry.get("link", "")
            items.append(f"• <a href=\"{link}\">{title}</a>")
        return items or ["ℹ️ Наразі немає нових публікацій."]
    except Exception as e:
        return [f"❌ Помилка завантаження RSS: {e}"]

async def fetch_fb_posts(page_id: str, token: str, limit: int = 5) -> List[str]:
    if not page_id or not token:
        return ["⚠️ Facebook не налаштовано. Додайте FACEBOOK_PAGE_ID і FACEBOOK_TOKEN у .env"]
    url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
    params = {"access_token": token, "limit": max(1, min(limit, 10))}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            posts = []
            for p in data.get("data", []):
                post_id = p.get("id")
                message = (p.get("message") or "Публікація").split("\n")[0]
                link = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"
                posts.append(f"• <a href=\"{link}\">{message[:120]}...</a>")
            return posts or ["ℹ️ Поки що немає нових дописів."]
    except Exception as e:
        return [f"❌ Помилка Facebook API: {e}"]

async def fetch_mva_news_html(url: str, limit: int = 6) -> List[str]:
    if not url:
        return ["⚠️ URL для Мінветеранів не налаштований."]
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, follow_redirects=True)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            items: List[str] = []
            for a in soup.select("article a, .views-row a, .news a"):
                title = (a.get_text() or "").strip()
                href = (a.get("href") or "").strip()
                if not title or not href:
                    continue
                if len(title) < 6:
                    continue
                if href.startswith("/"):
                    href = "https://mva.gov.ua" + href
                if href.startswith("https://mva.gov.ua") and "#comment" not in href:
                    items.append(f"• <a href=\"{href}\">{title}</a>")
                if len(items) >= limit:
                    break

            if not items:
                for a in soup.find_all("a"):
                    title = (a.get_text() or "").strip()
                    href = (a.get("href") or "").strip()
                    if not title or not href:
                        continue
                    if href.startswith("/"):
                        href = "https://mva.gov.ua" + href
                    if href.startswith("https://mva.gov.ua") and len(title) > 6:
                        items.append(f"• <a href=\"{href}\">{title}</a>")
                    if len(items) >= limit:
                        break

            return items[:limit] or ["ℹ️ Наразі не вдалося знайти новини на сторінці."]
    except Exception as e:
        return [f"❌ Помилка парсингу Мінветеранів: {e}"]

# ---------- Хендлери ----------
@dp.message(CommandStart())
async def on_start(message: Message):
    await message.answer(WELCOME, reply_markup=main_menu_kb())

@dp.message(F.text == "1⃣ Про нас")
async def about(message: Message):
    await message.answer(ABOUT_TEXT, reply_markup=about_kb())

@dp.callback_query(F.data.startswith("about:"))
async def about_sub(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    text = ABOUT_SUBTEXT.get(key, "ℹ️ Інформація буде додана найближчим часом.")
    await cb.message.edit_text(text, reply_markup=about_kb())
    await cb.answer()

@dp.message(F.text == "2⃣ Послуги та підтримка")
async def services(message: Message):
    await message.answer(SERVICES_TEXT, reply_markup=services_kb())

@dp.message(F.text == "3⃣ Програми та проекти")
async def programs(message: Message):
    await message.answer(PROGRAMS_TEXT, reply_markup=programs_kb())

@dp.message(F.text == "4⃣ Новини та події")
async def news(message: Message):
    await message.answer(NEWS_TEXT, reply_markup=news_kb())

@dp.callback_query(F.data == "news:minv")
async def news_minv(cb: CallbackQuery):
    items = await fetch_mva_news_html(MVA_NEWS_URL, limit=6)
    await cb.message.edit_text("🗞 <b>Останні новини (Мінветеранів)</b>\n\n" + "\n".join(items), reply_markup=news_kb())
    await cb.answer()

@dp.callback_query(F.data == "news:city")
async def news_city(cb: CallbackQuery):
    items = await fetch_rss(RSS_CITY_DNIPRO, limit=5)
    await cb.message.edit_text("📣 <b>Анонси заходів (місто)</b>\n\n" + "\n".join(items), reply_markup=news_kb())
    await cb.answer()

@dp.callback_query(F.data == "news:fb")
async def news_fb(cb: CallbackQuery):
    items = await fetch_fb_posts(FACEBOOK_PAGE_ID, FACEBOOK_TOKEN, FACEBOOK_POST_LIMIT)
    await cb.message.edit_text("📘 <b>Facebook Управління</b>\n\n" + "\n".join(items), reply_markup=news_kb())
    await cb.answer()

@dp.message(F.text == "5⃣ Психологічна підтримка")
async def psych(message: Message):
    await message.answer(PSYCH_TEXT, reply_markup=psych_kb())

@dp.message(F.text == "6⃣ Юридична допомога")
async def legal(message: Message):
    await message.answer(LEGAL_TEXT, reply_markup=legal_kb())

@dp.callback_query(F.data == "law:contacts")
async def law_contacts(cb: CallbackQuery):
    await cb.message.edit_text("📚 <b>Контакти юристів</b>\n\n" + LEGAL_CONTACTS, reply_markup=legal_kb())
    await cb.answer()

@dp.callback_query(F.data == "law:templates")
async def law_templates(cb: CallbackQuery):
    await cb.message.edit_text("📄 Зразки заяв та документів:\n• (додамо посилання на шаблони/Google Drive)\n", reply_markup=legal_kb())
    await cb.answer()

@dp.callback_query(F.data == "law:benefits")
async def law_benefits(cb: CallbackQuery):
    await cb.message.edit_text("💳 Як оформити пільги:\n• Крок 1 ...\n• Крок 2 ...\n(додамо офіційні посилання)", reply_markup=legal_kb())
    await cb.answer()

@dp.message(F.text == "7⃣ FAQ")
async def faq(message: Message):
    await message.answer(FAQ_TEXT, reply_markup=faq_kb())

@dp.message(F.text == "8⃣ Зворотний зв’язок")
async def feedback(message: Message):
    await message.answer(FEEDBACK_TEXT, reply_markup=feedback_kb())

@dp.callback_query(F.data == "nav:home")
async def nav_home(cb: CallbackQuery):
    await cb.message.edit_text(WELCOME)
    await cb.message.answer("⬇️ Головне меню", reply_markup=main_menu_kb())
    await cb.answer()

@dp.callback_query(F.data.startswith(("svc:", "prog:", "psy:", "faq:", "fb:")))
async def placeholders(cb: CallbackQuery):
    section = cb.data.split(":")[0]
    await cb.message.edit_text("ℹ️ Контент цього розділу буде додано найближчим часом.")
    kb_map = {
        "svc": services_kb(),
        "prog": programs_kb(),
        "psy": psych_kb(),
        "faq": faq_kb(),
        "fb": feedback_kb(),
    }
    await cb.message.edit_reply_markup(reply_markup=kb_map.get(section))
    await cb.answer()

@dp.message(F.text == "🔍 Пошук")
async def search(message: Message):
    await message.answer("Введіть ключове слово для пошуку (поки що простий текстовий пошук додамо пізніше).")

@dp.message(F.text == "📍 Найближчі ветеранські центри")
async def nearest_centers(message: Message):
    await message.answer("Надішліть вашу локацію або район — і ми підкажемо найближчі центри (функцію додамо після узгодження джерел).")

@dp.message()
async def fallback(message: Message):
    await message.answer("Не зовсім зрозумів запит. Оберіть розділ у меню або натисніть /start.", reply_markup=main_menu_kb())

# aiogram 3.7: startup handler без аргументів
async def on_startup():
    print("Bot started")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
