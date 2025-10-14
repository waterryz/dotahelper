import os
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- Telegram handlers ---
@dp.message()
async def start_handler(message: types.Message):
    await message.answer("✅ Бот запущен и работает через Flask + Render!")

# --- Webhook route ---
@app.route("/webhook", methods=["POST"])
async def webhook():
    data = await request.get_json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return "OK", 200

# --- Index route ---
@app.route("/", methods=["GET"])
def home():
    return "🌐 Flask сервер жив! Вебхук будет установлен при старте."

# --- Webhook setup (один раз, асинхронно при старте gunicorn) ---
@app.before_serving
async def setup_webhook():
    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    webhook_url = f"https://{hostname}/webhook"
    print(f"🌐 Устанавливаем вебхук: {webhook_url}")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(webhook_url)
    print("✅ Вебхук установлен!")

# --- Gunicorn entrypoint ---
# ничего не меняем здесь, Render будет вызывать gunicorn app:app
