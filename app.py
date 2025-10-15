import asyncio
import aiohttp
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Загрузка токена
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN не найден. Убедись, что он задан в .env или в Render Environment Variables.")

# ──────────────────────────────────────────────
# Настройка логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ──────────────────────────────────────────────
# Функция для получения меты героев (пример с OpenDota API)
async def get_meta_heroes():
    API_URL = "https://api.opendota.com/api/heroes"
    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(API_URL, timeout=15) as response:
                if response.status != 200:
                    logging.error(f"Ошибка при запросе: {response.status}")
                    return None
                data = await response.json()
                return data
    except Exception as e:
        logging.error(f"Ошибка при получении меты: {e}")
        return None

# ──────────────────────────────────────────────
# Команда /start
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "Привет! ⚡ Введи имя героя латиницей (например, sven, lion, invoker)."
    )

# ──────────────────────────────────────────────
# Поиск героя по имени
@dp.message()
async def find_hero(message: Message):
    hero_name = message.text.strip().lower()
    heroes = await get_meta_heroes()

    if not heroes:
        await message.answer("❌ Данные временно недоступны. Попробуй позже.")
        return

    for hero in heroes:
        if hero_name == hero["name"].split("_")[-1]:  # "npc_dota_hero_lion" → "lion"
            localized = hero["localized_name"]
            id_ = hero["id"]
            await message.answer(
                f"🦸 Герой найден!\n\n"
                f"ID: {id_}\n"
                f"Имя: {localized}\n"
                f"API-имя: {hero['name']}"
            )
            return

    await message.answer("❌ Герой не найден или данные временно недоступны.")

# ──────────────────────────────────────────────
# Основной запуск (без Flask)
async def main():
    logging.info("🚀 Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")
