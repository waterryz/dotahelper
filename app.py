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
    <html><head><title>DotaAI Admin</title>
    <style>
        body{{font-family:Segoe UI;background:#0e1117;color:#fff;padding:20px;text-align:center}}
        .hero{{background:#1c1f26;border-radius:10px;padding:10px;margin:10px auto;width:70%}}
        input,button{{padding:8px;margin:5px;border:none;border-radius:5px}}
        button{{background:#0078ff;color:white;cursor:pointer}}button:hover{{background:#005ecc}}
        .error{{color:#ff4b4b}}
        table{{width:100%;border-collapse:collapse}}th,td{{padding:6px;border-bottom:1px solid #333;text-align:left}}
        th{{background:#1f232a}}.green{{color:#00ff95}}
    </style></head><body>
    <h1>⚙️ DotaAI — Панель администратора</h1>
    <nav>
        <a href='/admin?password={ADMIN_PASSWORD}'>📜 Логи</a> |
        <a href='/admin?password={ADMIN_PASSWORD}&stats=1'>📊 Статистика</a> |
        <a href='/admin?password={ADMIN_PASSWORD}&clear=1'>🧹 Очистить</a> |
        <a href='/admin?password={ADMIN_PASSWORD}&toggle=1'>⚡ Вкл/Выкл</a>
    </nav><hr>
    {content}
    </body></html>"""

# ──────────────────────────────────────────────
# Админ-панель
async def admin_page(request):
    password = request.query.get("password", "")
    if password != ADMIN_PASSWORD:
        return web.Response(text=admin_html("<h3 class='error'>❌ Доступ запрещён.</h3>"), content_type="text/html")

    logs = json.load(open(LOG_FILE, encoding="utf-8")) if os.path.exists(LOG_FILE) else []
    params = request.query

    # Очистка логов
    if "clear" in params:
        open(LOG_FILE, "w").write("[]")
        return web.Response(text=admin_html("<h3 class='green'>✅ Логи очищены!</h3>"), content_type="text/html")

    # Вкл/выкл
    if "toggle" in params:
        state = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
        state["disabled"] = not state.get("disabled", False)
        json.dump(state, open(STATE_FILE, "w"))
        status = "🟢 Включен" if not state["disabled"] else "🔴 Выключен"
        return web.Response(text=admin_html(f"<h3 class='green'>⚙️ Бот теперь: {status}</h3>"), content_type="text/html")

    # Поиск
    query = params.get("search", "").lower()
    if query:
        logs = [x for x in logs if query in (x["username"] or "").lower()]

    # Статистика
    if "stats" in params:
        users = [x["username"] for x in logs]
        unique = len(set(users))
        top_users = Counter(users).most_common(5)
        rows = "".join(f"<tr><td>{u}</td><td>{c}</td></tr>" for u, c in top_users)
        content = f"""
        <h3>📊 Статистика</h3>
        <p>Всего сообщений: {len(logs)} | Уникальных пользователей: {unique}</p>
        <table><tr><th>👤 Пользователь</th><th>💬 Сообщений</th></tr>{rows}</table>
        """
        return web.Response(text=admin_html(content), content_type="text/html")

    # Просмотр логов
    content = "<form><input name='search' placeholder='🔍 Поиск по username'><input type='hidden' name='password' value='" + ADMIN_PASSWORD + "'><button>Искать</button></form><br>"
    if not logs:
        content += "<p>Нет сообщений.</p>"
    else:
        for msg in reversed(logs[-100:]):
            content += f"<div class='hero'><b>{msg['username']}</b> — {msg['time']}<br>{msg['text']}</div>"

    return web.Response(text=admin_html(content), content_type="text/html")

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
