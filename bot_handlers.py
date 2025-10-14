from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
import os, requests
from bs4 import BeautifulSoup

load_dotenv()
BOT_TOKEN = os.getenv("7641143202:AAHN6GuQQrGXI4tsGwlmUR0rC3ABPohiqlc")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

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

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔥 Мета", callback_data="meta"),
        InlineKeyboardButton("⚔️ Сборки", callback_data="builds"),
    )
    await message.answer("Привет! Я Dota 2 бот 💎\nВыбери действие:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "meta")
async def show_meta(callback_query: types.CallbackQuery):
    heroes = get_meta_heroes()
    await bot.send_message(callback_query.from_user.id, "🔥 Топ-10 героев:\n\n" + "\n".join(heroes))

@dp.callback_query_handler(lambda c: c.data == "builds")
async def ask_hero(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Введи имя героя латиницей (например, `sven`, `lion`, `invoker`).")

@dp.message_handler()
async def hero_build(message: types.Message):
    hero = message.text.lower().replace(" ", "-")
    items = get_hero_items(hero)
    result = "\n".join([f"{i+1}. {x}" for i, x in enumerate(items)])
    await message.answer(f"⚔️ Сборка для {hero.title()}:\n\n{result}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
