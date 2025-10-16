import os
import json
import logging
import asyncio
from datetime import datetime
from collections import Counter
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiohttp import web
import aiohttp
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ─────────────────────────────
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
STATE_FILE = "state.json"

# ─────────────────────────────
# ЛОГИ
def log_message(user_id, username, text):
    entry = {
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
        "username": username or "—",
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


# ─────────────────────────────
# HTML ОБЁРТКА
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
                padding: 20px;
                text-align: center;
            }}
            .hero {{
                background: #1c1f26;
                border-radius: 10px;
                padding: 10px;
                margin: 10px auto;
                width: 70%;
            }}
            button {{
                background: #0078ff;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                cursor: pointer;
            }}
            button:hover {{ background: #005ecc; }}
            input {{ padding: 8px; border-radius: 5px; border: none; width: 200px; }}
            .error {{ color: #ff4b4b; }}
            .green {{ color: #00ff95; }}
            hr {{ border: 1px solid #333; }}
        </style>
    </head>
    <body>
        <h1>⚙️ DotaAI — Панель администратора</h1>
        {content}
    </body>
    </html>
    """

# ─────────────────────────────
# АДМИН-ПАНЕЛЬ
async def admin_panel(request):
    pwd = request.rel_url.query.get("pwd", "")
    if pwd != ADMIN_PASSWORD:
        return web.Response(text=admin_html("<p class='error'>⛔ Доступ запрещён</p>"), content_type="text/html")

    logs = read_logs()
    state = {"disabled": False}
    if os.path.exists(STATE_FILE):
        state = json.load(open(STATE_FILE, "r", encoding="utf-8"))

    query = request.rel_url.query.get("q", "").lower()
    if query:
        logs = [x for x in logs if query in (x["username"] or "").lower() or query in x["text"].lower()]

    users = [l["username"] for l in logs]
    stats_html = f"<p>👥 Уникальных пользователей: {len(set(users))}<br>💬 Всего сообщений: {len(logs)}</p>"
    top_users = Counter(users).most_common(5)
    if top_users:
        stats_html += "<h3>🏆 Топ активных:</h3><ul>" + "".join([f"<li>{u} — {c}</li>" for u, c in top_users]) + "</ul>"

    log_html = "".join([f"<div class='hero'><b>{l['username']}</b> — {l['time']}<br>{l['text']}</div>" for l in logs[-50:]])

    status = "🟢 Включен" if not state.get("disabled") else "🔴 Выключен"
    controls = f"""
    <form method='get'>
        <input type='hidden' name='pwd' value='{pwd}'>
        <input name='q' placeholder='🔍 Поиск по имени или тексту'>
        <button type='submit'>Найти</button>
    </form>
    <form method='post' action='/clear'>
        <input type='hidden' name='pwd' value='{pwd}'>
        <button type='submit'>🧹 Очистить логи</button>
    </form>
    <form method='post' action='/toggle'>
        <input type='hidden' name='pwd' value='{pwd}'>
        <button type='submit'>⚡ {status}</button>
    </form>
    <form method='post' action='/force_on'>
        <input type='hidden' name='pwd' value='{pwd}'>
        <button type='submit' style='background:#00ff95;color:black;'>🆘 Принудительно включить бота</button>
    </form>
    """

    html = admin_html(f"{controls}<hr>{stats_html}<hr>{log_html}")
    return web.Response(text=html, content_type="text/html")


async def clear_handler(request):
    data = await request.post()
    if data.get("pwd") == ADMIN_PASSWORD:
        clear_logs()
        return web.Response(text=admin_html("<p class='green'>✅ Логи очищены</p>"), content_type="text/html")
    return web.Response(text=admin_html("<p class='error'>⛔ Ошибка доступа</p>"), content_type="text/html")


async def toggle_handler(request):
    data = await request.post()
    if data.get("pwd") == ADMIN_PASSWORD:
        state = {"disabled": False}
        if os.path.exists(STATE_FILE):
            state = json.load(open(STATE_FILE, "r", encoding="utf-8"))
        state["disabled"] = not state.get("disabled", False)
        json.dump(state, open(STATE_FILE, "w", encoding="utf-8"))
        status = "🟢 Включен" if not state["disabled"] else "🔴 Выключен"
        return web.Response(text=admin_html(f"<p class='green'>⚙️ Бот теперь: {status}</p>"), content_type="text/html")
    return web.Response(text=admin_html("<p class='error'>⛔ Ошибка доступа</p>"), content_type="text/html")


async def force_on_handler(request):
    data = await request.post()
    if data.get("pwd") == ADMIN_PASSWORD:
        json.dump({"disabled": False}, open(STATE_FILE, "w", encoding="utf-8"))
        return web.Response(text=admin_html("<p class='green'>🆘 Бот принудительно включен!</p>"), content_type="text/html")
    return web.Response(text=admin_html("<p class='error'>⛔ Ошибка доступа</p>"), content_type="text/html")


# ─────────────────────────────
# МИНИ-ПРИЛОЖЕНИЕ (META)
async def fetch_meta():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.opendota.com/api/heroStats") as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            heroes = sorted(
                data, key=lambda h: h["pro_win"] / max(h["pro_pick"], 1), reverse=True
            )[:15]
            return [
                {
                    "name": h["localized_name"],
                    "winrate": round(h["pro_win"] / max(h["pro_pick"], 1) * 100, 2),
                    "img": f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{h['name'][14:]}.png"
                }
                for h in heroes
            ]


async def meta_webapp(request):
    meta = await fetch_meta()
    if not meta:
        return web.Response(text="<h3>⚠ Не удалось получить данные</h3>", content_type="text/html")
    heroes_html = "".join(
        f"<div class='hero'><img src='{h['img']}' width='64'><b>{h['name']}</b> — 🏆 {h['winrate']}%</div>"
        for h in meta
    )
    return web.Response(text=f"<html><body><h2>📊 Мета Dota 2</h2>{heroes_html}</body></html>", content_type="text/html")


# ─────────────────────────────
# БОТ
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    webapp_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/metaapp"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📊 Открыть мету", web_app=WebAppInfo(url=webapp_url))
    ]])
    await message.answer(
        "👋 Привет! Это DotaAI — эксперт по Dota 2.\n"
        "Задай вопрос о герое или стратегии, или открой мету ниже 👇",
        reply_markup=keyboard
    )


@dp.message()
async def handle_message(message: types.Message):
    log_message(message.from_user.id, message.from_user.username, message.text)

    # Проверяем выключен ли бот
    if os.path.exists(STATE_FILE):
        state = json.load(open(STATE_FILE))
        if state.get("disabled"):
            await message.answer("🚫 Бот временно отключён администратором.")
            return

    webapp_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/metaapp"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📊 Показать мету", web_app=WebAppInfo(url=webapp_url))
    ]])

    try:
        SYSTEM_PROMPT = (
            "Ты — DotaAI, эксперт по Dota 2. "
            "Отвечай как аналитик DotaBuff: кратко, точно, с акцентом на пользу."
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
        await message.answer(f"⚠ Ошибка: {e}", reply_markup=keyboard)


# ─────────────────────────────
# SERVER & WEBHOOK
async def handle(request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_webhook_update(bot=bot, update=update)
    return web.Response(status=200)


async def health(request):
    return web.Response(text="✅ Bot is running!")


async def main():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/metaapp", meta_webapp)
    app.router.add_get("/admin", admin_panel)
    app.router.add_post("/clear", clear_handler)
    app.router.add_post("/toggle", toggle_handler)
    app.router.add_post("/force_on", force_on_handler)
    app.router.add_post(f"/{BOT_TOKEN}", handle)

    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    logging.info(f"🚀 Webhook установлен: {webhook_url}")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()

    logging.info("🌐 Сервер запущен.")
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
