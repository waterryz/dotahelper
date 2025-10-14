import os
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from bot_handlers import router
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в переменных окружения!")


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
dp.include_router(router)

app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Бот онлайн!", 200

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = types.Update.model_validate(request.json)
    await dp.feed_update(bot, update)
    return "ok", 200

@app.before_first_request
def setup_webhook():
    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    webhook_url = f"https://{hostname}/webhook"
    print(f"🌐 Устанавливаем вебхук: {webhook_url}")
    asyncio.run(bot.set_webhook(webhook_url))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    print(f"🚀 Flask запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)
