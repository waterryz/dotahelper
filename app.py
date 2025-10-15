import os
import logging
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Настройка окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise Exception("❌ Убедись, что BOT_TOKEN и OPENAI_API_KEY заданы в .env или Environment Variables Render")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ──────────────────────────────────────────────
# SYSTEM PROMPT для GPT
SYSTEM_PROMPT = """
Ты — эксперт по Dota 2, называешься DotaAI. 
Ты советуешь игрокам, кого пикнуть против других героев, какие предметы собирать, и как вести себя на линии.
Отвечай кратко, но точно, как опытный киберспортсмен.
"""

# ──────────────────────────────────────────────
# ✅ ФУНКЦИЯ для парсинга DotaBuff
async def get_meta_heroes():
    url = "https://api.opendota.com/api/heroStats"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Ошибка OpenDota API ({response.status})")
            
            data = await response.json()
            # Вычисляем винрейт из статистики про-игр
            heroes = []
            for hero in data:
                if hero["pro_pick"] and hero["pro_pick"] > 0:
                    win_rate = (hero["pro_win"] / hero["pro_pick"]) * 100
                    heroes.append((hero["localized_name"], win_rate))
            
            # Сортируем и выбираем топ-5
            heroes.sort(key=lambda x: x[1], reverse=True)
            return [(name, f"{rate:.2f}%") for name, rate in heroes[:5]]

# ──────────────────────────────────────────────
# Команда /start
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("👋 Привет! Я DotaAI. Напиши мне имя героя или команду /meta — покажу топ-героев по винрейту.")

# ──────────────────────────────────────────────
# ✅ Команда /meta — показывает актуальную мету с DotaBuff
@dp.message(Command("meta"))
async def show_meta(message: Message):
    try:
        heroes = await get_meta_heroes()
        text = "🔥 Топ-5 героев по винрейту (данные DotaBuff):\n\n"
        for name, rate in heroes:
            text += f"• {name} — {rate}\n"
        await message.answer(text)
    except Exception as e:
        await message.answer(f"⚠ Не удалось загрузить мету: {e}")

# ──────────────────────────────────────────────
# Общие запросы к GPT
@dp.message()
async def ask_ai(message: Message):
    user_input = message.text.strip()

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
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
# Запуск бота
async def main():
    logging.info("🚀 DotaAI запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")
