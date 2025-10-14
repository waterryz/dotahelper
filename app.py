import os
import asyncio
import requests
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# === Загружаем переменные окружения ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения!")

# === Инициализация Flask и Aiogram ===
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Функции парсинга Dotabuff ===
def get_meta_heroes():
    url = "https://www.dotabuff.com/heroes/meta"
    headers = {"User-Agent": "Mozilla/5.0"}
    soup = BeautifulSoup(requests.get(url, headers=headers).text, "lxml")
    rows = soup.find_all("tr")[1:11]
    return [
        f"{r.find_all('td')[1].text.strip()} — 🏆 {r.find_all('td')[2].text.strip()} | 📈 {r.find_all('td')[3].text.strip()}"
        for r in rows
    ]

def get_hero_items(hero: str):
    url = f"https://www.dotabuff.com/heroes/{hero}/items"
    headers = {"User-Agent": "Mozilla/5.0"}
    soup = BeautifulSoup(requests.get(url, headers=headers).text, "lxml")
    rows = soup.find_all("tr")[1:11]
    return [f"{r.find_all('td')[1].text.strip()} — {r.find_all('td')[2].text.strip()}" for r in rows]

# === Aiogram Handlers ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Актуальная мета", callback_data="meta")],
        [InlineKeyboardButton(text="⚔️ Актуальные сборки", callback_data="builds")]
    ])
    await message.answer(
        "Привет! 💎 Я Dota 2 помощник.\nВыбери, что хочешь узнать:",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data == "meta")
async def show_meta(callback: types.CallbackQuery):
    heroes = get_meta_heroes()
    text = "🔥 Топ-10 героев по мете:\n\n" + "\n".join(heroes)
    await bot.send_message(callback.from_user.id, text)

@dp.callback_query(lambda c: c.data == "builds")
async def ask_hero(callback: types.CallbackQuery):
    await bot.send_message(
        callback.from_user.id,
        "Введи имя героя латиницей (например, `sven`, `lion`, `invoker`)."
    )

@dp.message()
async def show_hero_build(message: types.Message):
    hero = message.text.lower().replace(" ", "-")
    try:
        items = get_hero_items(hero)
        result = "\n".join([f"{i+1}. {x}" for i, x in enumerate(items)])
        await message.answer(f"⚔️ Актуальная сборка для *{hero.title()}*:\n\n{result}", parse_mode="Markdown")
    except Exception:
        await message.answer("❌ Не удалось найти такого героя. Попробуй, например: `juggernaut`, `pudge`, `storm-spirit`")

# === Flask endpoint для webhook ===
@app.route("/webhook", methods=["POST"])
async def webhook():
    update = types.Update.model_validate(await request.json)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.route("/")
def home():
    return "✅ Бот работает на Flask + Aiogram 3.13"

# === Запуск и настройка webhook ===
async def on_startup():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    await bot.set_webhook(webhook_url)
    print(f"🌐 Вебхук установлен: {webhook_url}")

def start():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_startup())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    start()
