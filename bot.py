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


# --- توابع مدیریت دیتابیس برای دکمه‌ها (شامل بک‌لینک و message_thread_id) ---
def get_button_state(original_msg_id):
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        SELECT bot_emoji_msg_id, korrektur_link, grammatik_link, vokabel_link, übersetzung_link, back_link, message_thread_id 
        FROM feedbacks WHERE original_msg_id = ?
    """,
      (original_msg_id,),
  )
  row = cursor.fetchone()
  conn.close()
  return row


def save_or_update_button_state(
    original_msg_id,
    chat_id,
    bot_emoji_msg_id,
    korrektur_link=None,
    grammatik_link=None,
    vokabel_link=None,
    übersetzung_link=None,
    back_link=None,
    message_thread_id=None,
):
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()

  cursor.execute(
      "SELECT original_msg_id FROM feedbacks WHERE original_msg_id = ?",
      (original_msg_id,),
  )
  exists = cursor.fetchone()

  if exists:
    if korrektur_link is not None:
      cursor.execute(
          "UPDATE feedbacks SET korrektur_link = ? WHERE original_msg_id = ?",
          (korrektur_link, original_msg_id),
      )
    if grammatik_link is not None:
      cursor.execute(
          "UPDATE feedbacks SET grammatik_link = ? WHERE original_msg_id = ?",
          (grammatik_link, original_msg_id),
      )
    if vokabel_link is not None:
      cursor.execute(
          "UPDATE feedbacks SET vokabel_link = ? WHERE original_msg_id = ?",
          (vokabel_link, original_msg_id),
      )
    if übersetzung_link is not None:
      cursor.execute(
          "UPDATE feedbacks SET übersetzung_link = ? WHERE original_msg_id = ?",
          (übersetzung_link, original_msg_id),
      )
    if back_link is not None:
      cursor.execute(
          "UPDATE feedbacks SET back_link = ? WHERE original_msg_id = ?",
          (back_link, original_msg_id),
      )
    if message_thread_id is not None:
      cursor.execute(
          "UPDATE feedbacks SET message_thread_id = ? WHERE original_msg_id = ?",
          (message_thread_id, original_msg_id),
      )
  else:
    cursor.execute(
        """
            INSERT INTO feedbacks (original_msg_id, chat_id, bot_emoji_msg_id, korrektur_link, grammatik_link, vokabel_link, übersetzung_link, back_link, message_thread_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            original_msg_id,
            chat_id,
            bot_emoji_msg_id,
            korrektur_link,
            grammatik_link,
            vokabel_link,
            übersetzung_link,
            back_link,
            message_thread_id,
        ),
    )

  conn.commit()
  conn.close()


# --- تابع ساخت کیبورد هوشمند (با چیدمان هوشمند ۲تایی) ---
def create_dynamic_keyboard(
    korrektur_link=None,
    grammatik_link=None,
    vokabel_link=None,
    übersetzung_link=None,
    back_link=None,
):
  markup = types.InlineKeyboardMarkup()
  row1 = []
  row2 = []
  row_back = []

  all_main_buttons = []
  if übersetzung_link:
    all_main_buttons.append(
        types.InlineKeyboardButton("📝 übersetzung", url=übersetzung_link)
    )
  if korrektur_link:
    all_main_buttons.append(
        types.InlineKeyboardButton("🔍 korrektur", url=korrektur_link)
    )
  if vokabel_link:
    all_main_buttons.append(
        types.InlineKeyboardButton("📁 vokabel", url=vokabel_link)
    )
  if grammatik_link:
    all_main_buttons.append(
        types.InlineKeyboardButton("✍ grammatik", url=grammatik_link)
    )

  total_main = len(all_main_buttons)

  if total_main == 1:
    row1.append(all_main_buttons[0])
  elif total_main == 2:
    row1.extend(all_main_buttons)
  elif total_main == 3:
    row1.append(all_main_buttons[0])
    row1.append(all_main_buttons[1])
    row2.append(all_main_buttons[2])
  elif total_main == 4:
    row1.append(all_main_buttons[0])
    row1.append(all_main_buttons[1])
    row2.append(all_main_buttons[2])
    row2.append(all_main_buttons[3])

  if back_link:
    row_back.append(
        types.InlineKeyboardButton("⬅️ Deutsch sprechen", url=back_link)
    )

  if row1:
    markup.row(*row1)
  if row2:
    markup.row(*row2)
  if row_back:
    markup.row(*row_back)

  return markup


# --- هندلر دستور دستی addbtn ---
@bot.message_handler(commands=["addbtn"])
def handle_add_button(message):
  if not message.reply_to_message:
    return

  original_msg_id = message.reply_to_message.message_id
  chat_id = message.chat.id

  # استخراج دقیق شناسه تاپیک (اول از پیام ریپلای‌شده، اگر نبود از دیتابیس)
  state = get_button_state(original_msg_id)

  message_thread_id = getattr(
      message.reply_to_message, "message_thread_id", None
  )
  if not message_thread_id and state and len(state) > 6:
    message_thread_id = state[6]

  parts = message.text.split(maxsplit=2)
  if len(parts) < 3:
    return

  btn_name = parts[1].strip().lower()
  btn_link = parts[2].strip()

  korrektur_l = state[1] if state and state[1] else None
  grammatik_l = state[2] if state and state[2] else None
  vokabel_l = state[3] if state and state[3] else None
  übersetzung_l = state[4] if state and state[4] else None
  back_l = state[5] if state and len(state) > 5 and state[5] else None
  bot_emoji_msg_id = state[0] if state and state[0] else None

  if btn_name == "übersetzung":
    übersetzung_l = btn_link
  elif btn_name == "korrektur":
    korrektur_l = btn_link
  elif btn_name == "vokabel":
    vokabel_l = btn_link
  elif btn_name == "grammatik":
    grammatik_l = btn_link
  elif btn_name == "back":
    back_l = btn_link
  else:
    return

  markup = create_dynamic_keyboard(
      korrektur_link=korrektur_l,
      grammatik_link=grammatik_l,
      vokabel_link=vokabel_l,
      übersetzung_link=übersetzung_l,
      back_link=back_l,
  )

  if bot_emoji_msg_id:
    try:
      bot.edit_message_text(
          chat_id=chat_id,
          message_id=bot_emoji_msg_id,
          text=EMOJI_TEXT,
          reply_markup=markup,
      )
    except Exception:
      # ارسال پیام جدید با رعایت کامل message_thread_id
      kwargs = {
          "chat_id": chat_id,
          "text": EMOJI_TEXT,
          "reply_markup": markup,
          "reply_to_message_id": original_msg_id,
      }
      if message_thread_id:
        kwargs["message_thread_id"] = message_thread_id

      new_msg = bot.send_message(**kwargs)
      bot_emoji_msg_id = new_msg.message_id
  else:
    kwargs = {
        "chat_id": chat_id,
        "text": EMOJI_TEXT,
        "reply_markup": markup,
        "reply_to_message_id": original_msg_id,
    }
    if message_thread_id:
      kwargs["message_thread_id"] = message_thread_id

    new_msg = bot.send_message(**kwargs)
    bot_emoji_msg_id = new_msg.message_id

  save_or_update_button_state(
      original_msg_id=original_msg_id,
      chat_id=chat_id,
      bot_emoji_msg_id=bot_emoji_msg_id,
      korrektur_link=korrektur_l,
      grammatik_link=grammatik_l,
      vokabel_link=vokabel_l,
      übersetzung_link=übersetzung_l,
      back_link=back_l,
      message_thread_id=message_thread_id,
  )

  try:
    bot.delete_message(chat_id, message.message_id)
  except Exception:
    pass


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
  return "Bot is running successfully with all components!", 200


if __name__ == "__main__":
  WEBHOOK_URL = f"https://my-bot-0jtw.onrender.com/{TOKEN}"
  bot.remove_webhook()
  bot.set_webhook(url=WEBHOOK_URL)

  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
