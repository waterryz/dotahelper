import os
import asyncio
import requests
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --- Загрузка переменных ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- Парсеры ---
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

# --- Telegram handlers ---
@dp.message(commands=["start"])
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔥 Актуальная мета", callback_data="meta"),
        InlineKeyboardButton("⚔️ Актуальные сборки", callback_data="builds")
    )
    await message.answer("Привет! 💎 Я Dota 2 помощник.\nВыбери, что хочешь узнать:", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "meta")
async def show_meta(callback: types.CallbackQuery):
    heroes = get_meta_heroes()
    text = "🔥 Топ-10 героев по мете:\n\n" + "\n".join(heroes)
    await bot.send_message(callback.from_user.id, text)

@dp.callback_query(lambda c: c.data == "builds")
async def ask_hero(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, "Введи имя героя латиницей (например, `sven`, `lion`, `invoker`).")

@dp.message()
async def show_hero_build(message: types.Message):
    hero = message.text.lower().replace(" ", "-")
    try:
        items = get_hero_items(hero)
        result = "\n".join([f"{i+1}. {x}" for i, x in enumerate(items)])
        await message.answer(f"⚔️ Актуальная сборка для *{hero.title()}*:\n\n{result}", parse_mode="Markdown")
    except Exception:
        await message.answer("❌ Не удалось найти такого героя. Попробуй, например: `juggernaut`, `pudge`, `storm-spirit`")

# --- Flask routes ---
@app.route("/", methods=["GET"])
def home():
    return "✅ Flask бот для Dota 2 работает!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.model_validate(data)
    asyncio.get_event_loop().create_task(dp.feed_update(bot, update))
    return "OK", 200

# --- Webhook setup ---
@app.before_serving
async def setup_webhook():
    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    webhook_url = f"https://{hostname}/webhook"
    print(f"🌐 Устанавливаем вебхук: {webhook_url}")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(webhook_url)
    print("✅ Вебхук установлен и бот готов к работе!")
