import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
import aiohttp
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Настройка окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise Exception("❌ Убедись, что BOT_TOKEN и OPENAI_API_KEY заданы в .env или переменных Render")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
Ты — эксперт по Dota 2, называешься DotaAI. 
Ты советуешь игрокам, кого пикнуть против других героев, какие предметы собирать, и как вести себя на линии.
Отвечай кратко, но точно, как опытный аналитик DotaBuff.
"""

# ──────────────────────────────────────────────
# Команда /start
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Я DotaAI. Напиши имя героя или задай вопрос — и я помогу тебе с билдом, контрпиками или стратегией.\n\n"
                         "Также можешь использовать /meta, чтобы узнать текущую мету!")

# ──────────────────────────────────────────────
# Команда /meta (через OpenDota)
@dp.message(Command("meta"))
async def get_meta(message: types.Message):
    try:
        url = "https://api.opendota.com/api/heroStats"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await message.answer("⚠ Не удалось получить данные OpenDota.")
                    return

                data = await resp.json()
                heroes = []
                for hero in data:
                    pro_pick = hero.get("pro_pick", 0)
                    pro_win = hero.get("pro_win", 0)
                    if pro_pick > 20:
                        winrate = (pro_win / pro_pick) * 100
                        heroes.append((hero["localized_name"], winrate))

                heroes.sort(key=lambda x: x[1], reverse=True)
                top5 = heroes[:5]

                text = "🔥 Топ-5 героев по винрейту (данные OpenDota):\n\n"
                for name, rate in top5:
                    text += f"• {name} — {rate:.2f}%\n"

                await message.answer(text)
    except Exception as e:
        logging.error(f"Ошибка при /meta: {e}")
        await message.answer(f"⚠ Ошибка при получении меты: {e}")

# ──────────────────────────────────────────────
# Обработка всех остальных сообщений
@dp.message()
async def ask_ai(message: types.Message):
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
# Настройка webhook для Render
from aiogram import types

async def handle(request):
    try:
        data = await request.json()
        update = types.Update(**data)  # преобразуем dict → Update
        await dp.feed_webhook_update(bot=bot, update=update)
        return web.Response(status=200)
    except Exception as e:
        logging.error(f"Ошибка обработки webhook: {e}")
        return web.Response(status=500)


async def main():
    app = web.Application()
    app.router.add_post(f"/{BOT_TOKEN}", handle)

    # Настройка webhook
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    logging.info(f"🚀 Webhook установлен: {webhook_url}")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()

    logging.info("🌐 Сервер запущен и слушает порт.")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")
