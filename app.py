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

# === Обработчики Telegram ===
@dp.message()
async def echo_handler(message: types.Message):
    await message.answer(f"Привет, {message.from_user.first_name}! 👋")

# === Flask routes ===
@app.route("/", methods=["GET"])
def index():
    return "✅ Bot is running via Flask + Render!"

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.model_validate(await request.get_json())
    await dp.feed_update(bot, update)
    return "OK", 200

# === Настройка вебхука (один раз при старте) ===
async def on_startup():
    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    webhook_url = f"https://{hostname}/webhook"
    print(f"🌐 Устанавливаем вебхук: {webhook_url}")

    # Удаляем старый, если есть
    await bot.delete_webhook(drop_pending_updates=True)
    # Устанавливаем новый
    await bot.set_webhook(webhook_url)
    print("✅ Вебхук успешно установлен!")

# === Запуск ===
if __name__ == "__main__":
    asyncio.run(on_startup())  # Запускаем один раз при старте
    from waitress import serve
    serve(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
