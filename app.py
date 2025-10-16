import os
import json
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiohttp import web
import aiohttp
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# НАСТРОЙКА
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

LOG_FILE = "messages.json"

# ──────────────────────────────────────────────
# ЛОГИ
def log_message(user_id, username, text):
    entry = {
        "time": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "username": username,
        "text": text
    }
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    logs.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def read_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_logs():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)


# ──────────────────────────────────────────────
# МИНИ-ПРИЛОЖЕНИЕ DOTA META
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
            }}
            h1 {{ color: #00aaff; }}
            .hero {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: #1c1f26;
                border-radius: 10px;
                margin: 8px 0;
                padding: 8px 15px;
            }}
            img {{
                width: 64px;
                height: 36px;
                border-radius: 5px;
            }}
            .name {{ flex: 1; text-align: left; margin-left: 10px; font-size: 16px; }}
            .rate {{ font-weight: bold; color: #00ff95; }}
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
# АДМИН-ПАНЕЛЬ
def admin_html(content: str):
    return f"""
    <html>
    <head>
        <title>DotaAI Admin</title>
        <style>
            body {{
                font-family: 'Segoe UI', sans-serif;
                background-color: #0e1117;
                color: #f0f0f0;
                padding: 30px;
                text-align: center;
            }}
            .hero {{
                background: #1c1f26;
                border-radius: 10px;
                padding: 10px;
                margin: 10px auto;
                width: 60%;
            }}
            button {{
                background: #0078ff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
            }}
            button:hover {{ background: #005ecc; }}
            .error {{ color: #ff4b4b; }}
            input {{
                padding: 8px;
                border-radius: 5px;
                border: none;
                width: 200px;
            }}
        </style>
    </head>
    <body>
        <h1>⚙️ DotaAI — Панель администратора</h1>
        {content}
    </body>
    </html>
    """


async def admin_panel(request):
    pwd = request.rel_url.query.get("pwd", "")
    if pwd != ADMIN_PASSWORD:
        return web.Response(text=admin_html("<p class='error'>⛔ Доступ запрещён</p>"), content_type="text/html")

    logs = read_logs()
    users = {l["user_id"]: l.get("username", "—") for l in logs}
    log_list = "".join([f"<div class='hero'><b>{l['username']}</b>: {l['text']}</div>" for l in logs[-30:]])

    content = f"""
    <h3>👥 Пользователей: {len(users)}</h3>
    <h3>💬 Сообщений: {len(logs)}</h3>
    <form method='get'>
        <input type='hidden' name='pwd' value='{pwd}'>
        <input type='text' name='q' placeholder='Поиск...'>
        <button type='submit'>🔍 Найти</button>
    </form>
    <form action='/clear' method='post'>
        <input type='hidden' name='pwd' value='{pwd}'>
        <button type='submit'>🧹 Очистить логи</button>
    </form>
    <h2>📜 Последние сообщения:</h2>
    {log_list}
    """
    return web.Response(text=admin_html(content), content_type="text/html")


async def clear_handler(request):
    data = await request.post()
    if data.get("pwd") == ADMIN_PASSWORD:
        clear_logs()
        return web.Response(text=admin_html("<p>✅ Логи очищены</p>"), content_type="text/html")
    return web.Response(text=admin_html("<p class='error'>⛔ Ошибка доступа</p>"), content_type="text/html")

# ──────────────────────────────────────────────
# СТАРТ
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    webapp_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/metaapp"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📊 Открыть мету", web_app=WebAppInfo(url=webapp_url))
    ]])

    await message.answer(
        "👋 Привет! Это DotaAI — эксперт по Dota 2.\n"
        "Задай вопрос о герое или стратегии, а также можешь открыть мету 👇",
        reply_markup=keyboard
    )

# ──────────────────────────────────────────────
# AI-ОТВЕТЫ
@dp.message()
async def handle_message(message: types.Message):
    log_message(message.from_user.id, message.from_user.username, message.text)

    webapp_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/metaapp"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📊 Показать мету", web_app=WebAppInfo(url=webapp_url))
    ]])

    try:
        SYSTEM_PROMPT = (
            "Ты — DotaAI, эксперт по Dota 2. "
            "Отвечай как профессиональный аналитик DotaBuff: кратко, уверенно, точно."
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            temperature=0.7,
            max_tokens=400
        )

        answer = response.choices[0].message.content.strip()
        await message.answer(f"🎯 {answer}", reply_markup=keyboard)

    except Exception as e:
        logging.error(f"Ошибка OpenAI: {e}")
        await message.answer(f"⚠️ Что-то пошло не так: {e}", reply_markup=keyboard)

# ──────────────────────────────────────────────
# WEBHOOK + SERVER
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
async def main():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/metaapp", meta_webapp)
    app.router.add_get("/admin", admin_panel)
    app.router.add_post("/clear", clear_handler)
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


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")
