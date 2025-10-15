import asyncio
import os
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# === Настройка окружения ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Укажи его в .env или переменных окружения.")

# === Инициализация бота ===
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# === Вспомогательные функции ===
def get_meta_heroes():
    """Парсинг топ-10 героев с Dotabuff."""
    url = "https://www.dotabuff.com/heroes/meta"
    headers = {"User-Agent": "Mozilla/5.0"}
    soup = BeautifulSoup(requests.get(url, headers=headers).text, "lxml")
    rows = soup.find_all("tr")[1:11]
    return [
        f"{r.find_all('td')[1].text.strip()} — 🏆 {r.find_all('td')[2].text.strip()} | 📈 {r.find_all('td')[3].text.strip()}"
        for r in rows
    ]

def get_hero_items(hero: str):
    """Парсинг топ-10 предметов для героя."""
    url = f"https://www.dotabuff.com/heroes/{hero}/items"
    headers = {"User-Agent": "Mozilla/5.0"}
    soup = BeautifulSoup(requests.get(url, headers=headers).text, "lxml")
    rows = soup.find_all("tr")[1:11]
    return [f"{r.find_all('td')[1].text.strip()} — {r.find_all('td')[2].text.strip()}" for r in rows]

# === Хендлеры ===
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
    await callback.message.answer(
        "Введи имя героя латиницей (например, <b>sven</b>, <b>lion</b>, <b>invoker</b>)."
    )
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

# === Основной запуск ===
async def main():
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)
    print("🚀 Удаляем старый webhook (если был)...")
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook удалён. Запускаем polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
