import os
import asyncio
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from dotenv import load_dotenv

# Загрузка токена из .env
load_dotenv()
BOT_TOKEN = os.getenv("7641143202:AAHN6GuQQrGXI4tsGwlmUR0rC3ABPohiqlc")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===========================
# 🔥 ПАРСИНГ DOTABUFF
# ===========================

def get_meta_heroes():
    """Парсит топ-10 героев из Dotabuff (страница meta)"""
    url = "https://www.dotabuff.com/heroes/meta"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")

    heroes = []
    table = soup.find("table", class_="sortable")
    if not table:
        return ["Не удалось получить данные с Dotabuff"]

    rows = table.find_all("tr")[1:11]  # первые 10 героев
    for row in rows:
        cols = row.find_all("td")
        hero = cols[1].text.strip()
        win_rate = cols[2].text.strip()
        popularity = cols[3].text.strip()
        heroes.append(f"{hero} — 🏆 {win_rate} WR | 📈 {popularity}")
    return heroes


def get_hero_items(hero: str):
    """Парсит топ-10 предметов героя с Dotabuff"""
    url = f"https://www.dotabuff.com/heroes/{hero}/items"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")

    items = []
    table = soup.find("table", class_="sortable")
    if not table:
        return ["Не удалось получить сборку. Возможно, имя героя указано неверно."]

    rows = table.find_all("tr")[1:11]  # топ-10 предметов
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            item_name = cols[1].text.strip()
            win_rate = cols[2].text.strip()
            items.append(f"{item_name} — {win_rate}")
    return items

# ===========================
# 🤖 ОБРАБОТЧИКИ
# ===========================

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Актуальная мета", callback_data="meta")],
        [InlineKeyboardButton(text="⚔️ Сборки героев", callback_data="builds")]
    ])
    await message.answer("Привет! Я Dota 2 бот 💎\nВыбери действие:", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "meta")
async def show_meta(callback: types.CallbackQuery):
    await callback.message.answer("Получаю актуальную мету... ⏳")
    heroes = get_meta_heroes()
    result = "\n".join(heroes)
    await callback.message.answer(f"🔥 **Топ-10 героев меты:**\n\n{result}", parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "builds")
async def show_build_menu(callback: types.CallbackQuery):
    await callback.message.answer("Введи имя героя латиницей (пример: `sven`, `lion`, `invoker`):", parse_mode="Markdown")

@dp.message()
async def get_build(message: types.Message):
    hero = message.text.lower().strip().replace(" ", "-")
    await message.answer(f"🔍 Проверяю сборку для *{hero.title()}*...", parse_mode="Markdown")
    items = get_hero_items(hero)
    result = "\n".join([f"{i+1}. {x}" for i, x in enumerate(items)])
    await message.answer(f"⚔️ **Актуальная сборка для {hero.title()}:**\n\n{result}", parse_mode="Markdown")

# ===========================
# 🚀 ЗАПУСК
# ===========================
async def main():
    print("Bot started... ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
