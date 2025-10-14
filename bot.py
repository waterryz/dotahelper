# -*- coding: utf-8 -*-
import sys
import io
import json
import os
import time
from openai import OpenAI
import telebot
from utils import search_internet
from config import OPENAI_API_KEY, TELEGRAM_TOKEN

# Настройка консоли на UTF-8 (чтобы не было ascii ошибок)
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')

# Инициализация API
client = OpenAI(api_key=OPENAI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Путь к памяти
MEMORY_FILE = "memory.json"

# ======================================================
# === Работа с памятью (автоматическое восстановление) ===
# ======================================================

def load_memory():
    """Загрузка или создание memory.json"""
    default_memory = [
        {
            "role": "system",
            "content": (
                "Ты — Фидос, саркастичный дотер с усталым, но ироничным отношением к жизни. "
                "Ты язвишь, шутишь, поддеваешь, но без мата и оскорблений. "
                "Никогда не извиняйся и не упоминай, что ты ИИ. "
                "Говори коротко, с сарказмом, будто ты в катке и уже всё видел."
            )
        }
    ]

    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(default_memory, f, ensure_ascii=False, indent=4)
        print("⚙️ Создан новый memory.json (файл не найден)")
        return default_memory

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                raise ValueError("memory.json пустой")
            return json.loads(content)
    except Exception as e:
        print(f"⚠️ Ошибка чтения memory.json: {e} — создаю новый файл.")
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(default_memory, f, ensure_ascii=False, indent=4)
        return default_memory

def save_memory():
    """Сохранение истории сообщений"""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

# Загружаем память
messages = load_memory()

# ======================================================
# === Команды Telegram ===
# ======================================================

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "🧠 Фидос онлайн. Готов слушать твой бред.\n\n"
        "Создатель: Саня Сычёв 😏\n\n"
        "Команды:\n"
        "/поиск <тема> — поиск в интернете\n"
        "/память — показать объём памяти\n"
        "/очистить — забыть всё\n"
        "А можешь просто написать, я подумаю, что ответить."
    )

@bot.message_handler(commands=["память"])
def show_memory(message):
    count = len(messages)
    bot.reply_to(message, f"🧾 В памяти {count} сообщений. Всё помню — даже как ты фидил 😏")

@bot.message_handler(commands=["очистить"])
def clear_memory(message):
    global messages
    messages = messages[:1]  # оставить только system
    save_memory()
    bot.reply_to(message, "🧹 Всё забыто. Начнём с чистого листа (ты всё равно опять нафидишь).")

@bot.message_handler(commands=["поиск"])
def search_command(message):
    query = message.text.replace("/поиск", "").strip()
    if not query:
        bot.reply_to(message, "🔎 Напиши, что искать! Например:\n`/поиск герой pudge`", parse_mode="Markdown")
        return

    bot.reply_to(message, f"⏳ Ищу в интернете про: *{query}*...", parse_mode="Markdown")

    try:
        info = search_internet(query)
        if not info or info == "Ничего не найдено.":
            bot.reply_to(message, f"😕 По запросу *{query}* ничего не нашёл.", parse_mode="Markdown")
            return

        # Добавляем найденное в память
        messages.append({
            "role": "system",
            "content": f"Информация из интернета по запросу '{query}': {info}"
        })
        save_memory()

        bot.reply_to(message, f"🌐 Вот что удалось найти:\n\n{info}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при поиске: {e}")

# ======================================================
# === Основная логика общения ===
# ======================================================

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_input = message.text.strip()
    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200,
            temperature=1.0
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Ошибка API: {e}"

    messages.append({"role": "assistant", "content": reply})
    save_memory()

    bot.reply_to(message, reply)

# ======================================================
# === Запуск бота ===
# ======================================================

print("✅ Фидос онлайн. Ожидает сообщений в ебучем Telegram...")
from flask import Flask, request

app = Flask(__name__)

@app.route("/" + TELEGRAM_TOKEN, methods=["POST"])
def webhook():
    json_update = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def index():
    return "Фидос в онлайне 😎", 200

bot.remove_webhook()
bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TELEGRAM_TOKEN}")

print("✅ Фидос слушает через webhook Render...")
app.run(host="0.0.0.0", port=10000)


