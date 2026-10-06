import json
import os
import re
import sqlite3
import telebot
from telebot import types
from flask import Flask, request

# --- تنظیمات اولیه ربات ---
TOKEN = "8879831216:AAF1Qs8S1Yaz_GkbNgIYrnkYQ31pJzqStCE"
bot = telebot.TeleBot(TOKEN)

# متن پیام ربات شامل ایموجی‌ها
EMOJI_TEXT = "💫✨"

# --- تنظیمات تاپیک‌ها و ادمین‌ها ---
TOPIC_KORREKTUR = 191  # شناسه تاپیک کرکتور
TOPIC_GRAMMATIK = 188  # شناسه تاپیک گرامر
TOPIC_VOKABEL = 189  # شناسه تاپیک لغت
TOPIC_ÜBERSETZUNG = 334  # شناسه تاپیک ترجمه

ADMIN_IDS = [103743272]


# --- راه‌اندازی دیتابیس SQLite ---
def init_db():
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            original_msg_id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            bot_emoji_msg_id INTEGER,
            korrektur_link TEXT,
            grammatik_link TEXT,
            vokabel_link TEXT,
            übersetzung_link TEXT,
            back_link TEXT,
            message_thread_id INTEGER
        )
    """)
  conn.commit()
  conn.close()


init_db()


# --- تابع ساخت کیبورد هوشمند دکمه‌های لینک‌دار ---
def create_dynamic_keyboard(
    korrektur_link=None,
    grammatik_link=None,
    vokabel_link=None,
    übersetzung_link=None,
    back_link=None,
):
  markup = types.InlineKeyboardMarkup()
  buttons = []

  if übersetzung_link:
    buttons.append(
        types.InlineKeyboardButton("📝 Übersetzung", url=übersetzung_link)
    )
  if korrektur_link:
    buttons.append(
        types.InlineKeyboardButton("🔍 Korrektur", url=korrektur_link)
    )
  if grammatik_link:
    buttons.append(
        types.InlineKeyboardButton("✍ Grammatik", url=grammatik_link)
    )
  if vokabel_link:
    buttons.append(
        types.InlineKeyboardButton("📁 Vokabel", url=vokabel_link)
    )

  count = len(buttons)
  if count == 1:
    markup.add(buttons[0])
  elif count == 2:
    markup.add(buttons[0], buttons[1])
  elif count == 3:
    markup.add(buttons[0], buttons[1])
    markup.add(buttons[2])
  elif count >= 4:
    markup.add(buttons[0], buttons[1])
    markup.add(buttons[2], buttons[3])

  if back_link:
    markup.add(types.InlineKeyboardButton("⬅️ Deutsch sprechen", url=back_link))

  return markup


# --- راه‌‌اندازی برای هاست ابری (Webhook) ---
app = Flask(__name__)


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


@app.route("/")
def index():
  return "Bot is running with core configuration and keyboard function!", 200


if __name__ == "__main__":
  WEBHOOK_URL = f"https://my-bot-0jtw.onrender.com/{TOKEN}"
  bot.remove_webhook()
  bot.set_webhook(url=WEBHOOK_URL)

  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
