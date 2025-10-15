import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Настройка окружения
load_dotenv()
BOT_TOKEN = os.getenv("7641143202:AAHN6GuQQrGXI4tsGwlmUR0rC3ABPohiqlc")
OPENAI_API_KEY = os.getenv("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")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise Exception("❌ Убедись, что BOT_TOKEN и OPENAI_API_KEY заданы в .env")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ──────────────────────────────────────────────
# Подключаем клиента OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
Ты — эксперт по Dota 2, называешься DotaAI. 
Ты советуешь игрокам, кого пикнуть против других героев, какие предметы собирать, и как вести себя на линии.
Отвечай кратко, но точно, как опытный киберспортсмен.
"""

# ──────────────────────────────────────────────
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("👋 Привет! Я DotaAI. Напиши мне имя героя или задай вопрос — и я помогу тебе с билдом, контрпиками или стратегией.")

# ──────────────────────────────────────────────
@dp.message()
async def ask_ai(message: Message):
    user_input = message.text.strip()

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # можно gpt-4o или gpt-5, если доступно
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=400
        )

        answer = response.choices[0].message.content.strip()
        await message.answer(f"🎯 {answer}")

    except Exception as e:
        logging.error(f"Ошибка при запросе к ИИ: {e}")
        await message.answer("⚠ Что-то пошло не так. Попробуй позже.")

# ──────────────────────────────────────────────
async def main():
    logging.info("🚀 DotaAI запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")
