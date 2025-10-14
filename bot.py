# -*- coding: utf-8 -*-
import telebot
import random

TOKEN = "твой_токен_бота_от_BotFather"

bot = telebot.TeleBot(TOKEN)

# 📜 база ответов
responses = {
    "привет": [
        "Здарова, ну чё, опять фидить пришёл? 😏",
        "О, привет... уже вижу, как ты снова саппортом лезешь на мид 🤦‍♂️",
    ],
    "как дела": [
        "Как у крипов на 5-й минуте — не очень, но живу 😒",
        "Лучше, чем у тебя после последней катки 😂",
    ],
    "дота": [
        "Дота — это не игра, это диагноз, братишка 💀",
        "Если ты ещё не tilted — значит, не играл сегодня.",
    ],
    "пока": [
        "Ну всё, ливай с позором 🤣",
        "Счастливо, но ты всё равно нафидишь 😎",
    ]
}

# 🧠 ответ по ключевым словам
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.lower()

    for key in responses:
        if key in text:
            reply = random.choice(responses[key])
            bot.reply_to(message, reply)
            break
    else:
        bot.reply_to(message, "Чё ты несёшь вообще? 🤨")

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
    return "Фидос онлайн 🧠", 200

# Устанавливаем вебхук (Render даёт HTTPS)
bot.remove_webhook()
bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TELEGRAM_TOKEN}")

print("✅ Фидос слушает через webhook Render...")
app.run(host="0.0.0.0", port=10000)

