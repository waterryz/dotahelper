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

bot.polling(non_stop=True)
