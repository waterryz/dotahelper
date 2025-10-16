import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import aiohttp
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Настройка окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise Exception("❌ BOT_TOKEN и OPENAI_API_KEY не заданы в Render Environment")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ──────────────────────────────────────────────
# Telegram Mini App (WebApp) — кнопка "📊 Мета"
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    webapp_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/metaapp"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📊 Открыть мету", web_app=WebAppInfo(url=webapp_url))
    ]])

    await message.answer(
        "👋 Привет! Это DotaAI — я показываю актуальную мету героев.\n\n"
        "Нажми на кнопку ниже, чтобы открыть мини-приложение ⬇️",
        reply_markup=keyboard
    )

# ──────────────────────────────────────────────
# Обработка всех остальных сообщений
@dp.message()
async def default_message(message: types.Message):
    await message.answer("💡 Используй кнопку внизу, чтобы открыть мини-приложение!")

# ──────────────────────────────────────────────
# Функция получения меты (OpenDota)
async def fetch_meta():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.opendota.com/api/heroStats") as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            top = sorted(
                data,
                key=lambda h: h["pro_win"] / max(h["pro_pick"], 1),
                reverse=True
            )[:15]
            return [
                {
                    "name": h["localized_name"],
                    "winrate": round(h["pro_win"] / max(h["pro_pick"], 1) * 100, 2),
                    "img": f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{h['name'][14:]}.png"
                }
                for h in top
            ]

# ──────────────────────────────────────────────
# Mini App страница (рендерится внутри Telegram)
async def meta_webapp(request):
    meta = await fetch_meta()
    if not meta:
        return web.Response(text="<h2>⚠ Не удалось получить данные OpenDota</h2>", content_type="text/html")

    heroes_html = "".join([
        f"""
        <div class="hero">
            <img src="{h['img']}" alt="{h['name']}" loading="lazy">
            <div class="name">{h['name']}</div>
            <div class="rate">🏆 {h['winrate']}%</div>
        </div>
        """ for h in meta
    ])

    html = f"""
    <html>
    <head>
        <title>Dota 2 Meta</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', sans-serif;
                background-color: #0e1117;
                color: #f0f0f0;
                text-align: center;
                padding: 20px;
                margin: 0;
            }}
            h1 {{
                color: #00aaff;
                margin-bottom: 20px;
            }}
            .hero {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: #1c1f26;
                border-radius: 10px;
                margin: 10px 0;
                padding: 10px 15px;
            }}
            img {{
                width: 64px;
                height: 36px;
                border-radius: 5px;
            }}
            .name {{
                flex: 1;
                text-align: left;
                margin-left: 10px;
                font-size: 16px;
            }}
            .rate {{
                font-weight: bold;
                color: #00ff95;
            }}
        </style>
    </head>
    <body>
        <h1>📊 Текущая мета Dota 2</h1>
        {heroes_html}
        <p style="color: gray; font-size: 12px;">Данные из OpenDota API</p>
    </body>
    </html>
    """

    return web.Response(text=html, content_type="text/html")

# ──────────────────────────────────────────────
# Webhook и health-check
async def handle(request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_webhook_update(bot=bot, update=update)
        return web.Response(status=200)
    except Exception as e:
        logging.error(f"Ошибка обработки webhook: {e}")
        return web.Response(status=500)

async def health(request):
    return web.Response(text="✅ Bot is running!")

# ──────────────────────────────────────────────
# Main
async def main():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/metaapp", meta_webapp)
    app.router.add_post(f"/{BOT_TOKEN}", handle)

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

# ──────────────────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")
