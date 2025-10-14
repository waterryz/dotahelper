import os
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import asyncio

load_dotenv()
BOT_TOKEN = os.getenv("7641143202:AAHN6GuQQrGXI4tsGwlmUR0rC3ABPohiqlc")
WEBHOOK_URL = os.getenv("https://dotasanyahelper.onrender.com/webhook")  # пример: https://твой-домен.onrender.com/webhook

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# =======================
# 🔥 ПАРСИНГ DOTABUFF
# =======================
def get_meta_heroes():
    url = "https://www.dotabuff.com/heroes/meta"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")

    heroes = []
    table = soup.find("table", class_="sortable")
    if not table:
        return ["❌ Не удалось получить данные с Dotabuff"]

    for row in table.find_all("tr")[1:11]:
        cols = row.find_all("td")
        hero = cols[1].text.strip()
        win_rate = cols[2].text.strip()
        popularity = cols[3].text.strip()
        heroes.append(f"{hero} — 🏆 {win_rate} | 📈 {popularity}")
    return heroes

def get_hero_items(hero: str):
    url = f"https://www.dotabuff.com/heroes/{hero}/items"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")

    items = []
    table = soup.find("table", class_="sortable")
    if not table:
        return ["❌ Не удалось получить сборку."]

    for row in table.find_all("tr")[1:11]:
        cols = row.find_all("td")
        item_name = cols[1].text.strip()
        win_rate = cols[2].text.strip()
        items.append(f"{item_name} — {win_rate}")
    return items

# =======================
# 🤖 ОБРАБОТЧИКИ БОТА
# =======================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Мета", callback_data="meta")],
        [InlineKeyboardButton(text="⚔️ Сборки", callback_data="builds")]
    ])
    await message.answer("Привет! Я Dota 2 бот 💎\nВыбери действие:", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "meta")
async def show_meta(callback: types.CallbackQuery):
    heroes = get_meta_heroes()
    result = "\n".join(heroes)
    await callback.message.answer(f"🔥 *Топ-10 героев меты:*\n\n{result}", parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "builds")
async def ask_hero(callback: types.CallbackQuery):
    await callback.message.answer("Введи имя героя латиницей (пример: `sven`, `lion`, `invoker`):", parse_mode="Markdown")

@dp.message()
async def send_build(message: types.Message):
    hero = message.text.lower().replace(" ", "-")
    items = get_hero_items(hero)
    result = "\n".join([f"{i+1}. {x}" for i, x in enumerate(items)])
    await message.answer(f"⚔️ *Актуальная сборка для {hero.title()}:*\n\n{result}", parse_mode="Markdown")

# =======================
# 🌐 FLASK + WEBHOOK
# =======================
@app.route("/")
def home():
    return "✅ Dota 2 Bot is running!"

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = types.Update.model_validate(request.json)
    await dp.feed_update(bot, update)
    return "ok", 200

@app.before_first_request
def setup_webhook():
    asyncio.run(bot.set_webhook(WEBHOOK_URL))
    print(f"Webhook установлен на {WEBHOOK_URL}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
