import os
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://dotahelper.onrender.com")

app = Flask(__name__)

# создаём глобальный event loop
loop = asyncio.get_event_loop()

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


# ======= Вспомогательные функции =======

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


# ======= Хендлеры Telegram =======

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
    await callback.message.answer("Введи имя героя латиницей (например, <b>sven</b>, <b>lion</b>, <b>invoker</b>).")
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


# ======= Flask webhook =======

@app.route("/", methods=["GET"])
def index():
    return "✅ Dota 2 Bot работает!"


@app.route("/webhook", methods=["POST"])
def webhook():
    update_data = request.get_json()
    update = types.Update.model_validate(update_data)
    print("📩 Получен апдейт:", update_data)

    # создаём асинхронную задачу, не закрывая event loop
    loop.create_task(dp.feed_update(bot, update))

    return {"ok": True}


# ======= Установка webhook =======
if __name__ == "__main__":
    webhook_url = f"{RENDER_URL}/webhook"
    print(f"🔗 Установка webhook: {webhook_url}")
    resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")
    print(resp.json())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
