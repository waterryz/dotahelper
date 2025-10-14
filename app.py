import os
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from bot_handlers import register_handlers

# Загружаем .env
load_dotenv()

# Инициализация токена
TOKEN = os.getenv("7641143202:AAHN6GuQQrGXI4tsGwlmUR0rC3ABPohiqlc")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Регистрируем хендлеры
register_handlers(dp)

# Flask
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Flask и Telegram бот запущены.", 200

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = types.Update.model_validate(request.json)
    await dp.feed_update(bot, update)
    return "ok", 200

@app.before_first_request
def setup_webhook():
    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if not hostname:
        print("⚠️ RENDER_EXTERNAL_HOSTNAME не найден! Проверь Environment Variables в Render.")
    else:
        webhook_url = f"https://{hostname}/webhook"
        print(f"🌐 Устанавливаем вебхук: {webhook_url}")
        asyncio.run(bot.set_webhook(webhook_url))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    print(f"🚀 Flask запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)
