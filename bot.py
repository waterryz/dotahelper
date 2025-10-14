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

sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')

# Подключение к OpenAI и Telegram
client = OpenAI(api_key=OPENAI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Путь к памяти
MEMORY_FILE = "memory.json"
import json
import os

MEMORY_FILE = "memory.json"

def load_memory():
    default_memory = [
        {
            "role": "system",
            "content": (
                "Ты — Фидос, саркастичный дотер с усталым, но ироничным отношением к жизни. "
                "Ты язвишь, шутишь, поддеваешь, но без мата и оскорблений. "
                "Никогда не извиняйся и не упоминай, что ты ИИ. "
                "Говори коротко, с сарказмом, будто играешь в катку и уже всё видел."
            )
        }
    ]

    # если файла нет — создать
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(default_memory, f, ensure_ascii=False, indent=4)
        print("⚙️ Создан новый memory.json (файл не найден)")
        return default_memory

    # если файл пустой или битый — восстановить
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                raise ValueError("memory.json пустой")
            data = json.loads(content)
            return data
    except Exception as e:
        print(f"⚠️ Ошибка чтения memory.json: {e} — создаю новый файл.")
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(default_memory, f, ensure_ascii=False, indent=4)
        return default_memory

# вызываем загрузку
messages = load_memory()

# Загружаем историю сообщений
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        messages = json.load(f)
else:
    messages = [
        {
            "role": "system",
            "content": (
                "Ты — Фидос, токсичный, саркастичный дотер, но без мата. "
                "Отвечай коротко, с иронией, как будто ты реально в катке. "
                "Не признавай, что ты ИИ. Не извиняйся. "
                "Если спрашивают про интернет или инфу — можешь использовать данные, которые тебе дадут."
            )
        }
    ]

# Функция сохранения памяти
def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)
# Обработка сообщений Telegram
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "🧠 Фидос онлайн.\nПиши, что хочешь — только не ной. создатель: Саня Сычёв😏\n\n"
        "Команды:\n"
        "/поиск <тема> — поиск в интернете\n"
        "/память — показать текущую память\n"
        "/очистить — забыть всё"
    )
@bot.message_handler(commands=["память"])
def show_memory(message):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = len(data)
    bot.reply_to(message, f"🧾 В памяти {count} сообщений. Ещё помню, как ты фидил 😏")

@bot.message_handler(commands=["очистить"])
def clear_memory(message):
    global messages
    messages = messages[:1]  # оставить только system
    save_memory()
    bot.reply_to(message, "🧹 Всё забыто. Начнём с чистого листа (хотя ты всё равно опять нафидишь).")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_input = message.text.strip()

    # Если пользователь хочет поиск в интернете
    if user_input.lower().startswith("/поиск"):
        query = user_input.replace("/поиск", "").strip()
        info = search_internet(query)
        messages.append({"role": "system", "content": f"Вот что найдено: {info}"})

    # Добавляем сообщение пользователя
    messages.append({"role": "user", "content": user_input})

    # Ответ от модели
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            temperature=1.0
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Ошибка API: {e}"

    # Добавляем ответ в память
    messages.append({"role": "assistant", "content": reply})
    save_memory()

    bot.reply_to(message, reply)

# Запуск бота
print("✅ Фидос онлайн. Ожидает сообщений в вашем ебучем Telegram...")
bot.polling(none_stop=True)


