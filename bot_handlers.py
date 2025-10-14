from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup

router = Router()

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

@router.message(F.text == "/start")
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Мета", callback_data="meta")],
        [InlineKeyboardButton(text="⚔️ Сборки", callback_data="builds")]
    ])
    await message.answer("Привет! Я Dota 2 бот 💎\nВыбери действие:", reply_markup=kb)

@router.callback_query(F.data == "meta")
async def show_meta(callback_query: types.CallbackQuery):
    heroes = get_meta_heroes()
    await callback_query.message.answer("🔥 Топ-10 героев:\n\n" + "\n".join(heroes))
    await callback_query.answer()

@router.callback_query(F.data == "builds")
async def ask_hero(callback_query: types.CallbackQuery):
    await callback_query.message.answer("Введи имя героя латиницей (например, `sven`, `lion`, `invoker`).")
    await callback_query.answer()

@router.message()
async def hero_build(message: types.Message):
    hero = message.text.lower().replace(" ", "-")
    items = get_hero_items(hero)
    result = "\n".join([f"{i+1}. {x}" for i, x in enumerate(items)])
    await message.answer(f"⚔️ Сборка для {hero.title()}:\n\n{result}")
