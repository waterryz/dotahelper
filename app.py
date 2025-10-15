import os
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# Загружаем переменные окружения (.env)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flask-приложение
app = Flask(__name__)

# Настраиваем бота и диспетчер
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# === Вспомогательные функции ===

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


# === Хендлеры Telegram ===

@dp.message(F.text == "/start")
async def start_handler(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Актуальная мета", callback_data="meta")],
        [InlineKeyboardButton(text="⚔️ Сборки героев", callback_data="builds")]
    ])
    await message.answer("Привет! 💎 Я Dota 2 бот.\nВыбери действие:", reply_markup=kb)


@dp.callback_query(F.data == "meta")
async def show_meta(callback: types.CallbackQuery):
    heroes = get_meta_heroes()
    text = "🔥 Топ-10 героев по мете:\n\n" + "\n".join(heroes)
    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "builds")
async def ask_hero(callback: types.CallbackQuery):
    await callback.message.answer(
        "Введи имя героя латиницей (например, <b>sven</b>, <b>lion</b>, <b>invoker</b>)."
    )
    await callback.answer()


@dp.message()
async def hero_build(message: types.Message):
    hero = message.text.lower().replace(" ", "-")
    try:
        items = get_hero_items(hero)
        result = "\n".join([f"{i+1}. {x}" for i, x in enumerate(items)])
        await message.answer(f"⚔️ Сборка для <b>{hero.title()}</b>:\n\n{result}")
    except Exception:
        await message.answer("❌ Герой не найден или данные временно недоступны.")


# === Flask webhook ===

@app.route("/", methods=["GET"])
def index():
    return "✅ Dota 2 Bot работает!"


@app.route("/webhook", methods=["POST"])
def webhook():
    update_data = request.get_json()
    print("📩 Получен апдейт:", update_data)
    asyncio.run(dp.feed_update(bot, types.Update.model_validate(update_data)))
    return {"ok": True}


# === Установка webhook ===
if __name__ == "__main__":
    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://dotahelper.onrender.com")
    webhook_url = f"{RENDER_URL}/webhook"

    print("🔗 Установка webhook...")
    set_hook = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    ).json()
    print(set_hook)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
