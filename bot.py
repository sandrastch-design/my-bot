import json
import os
import re
import sqlite3
import telebot
from telebot import types

# --- تنظیمات اولیه ربات ---
TOKEN = "8879831216:AAF1Qs8S1Yaz_GkbNgIYrnkYQ31pJzqStCE"
bot = telebot.TeleBot(TOKEN)

# شناسه تاپیک‌های گروه تست شما
TOPIC_KORREKTUR = 191  # شناسه تاپیک کرکتور
TOPIC_GRAMMATIK = 188  # شناسه تاپیک گرامر
TOPIC_VOKABEL = 189  # شناسه تاپیک لغت
TOPIC_ÜBERSETZUNG = 334  # شناسه تاپیک ترجمه

# لیست آیدی‌های ادمین‌ها (شناسه عددی تلگرام شما)
ADMIN_IDS = [103743272]

# متن پیام ربات شامل ایموجی‌ها
EMOJI_TEXT = "💫✨"

# مسیر فایل ذخیره تنظیمات و شمارنده چرخش خوش‌آمدگویی
SETTINGS_FILE = "welcome_settings.json"

# تنظیمات پیش‌فرضِ اولیه خوشآمدگویی
DEFAULT_SETTINGS = {
    "welcome_active": True,
    "counter": 0,
}


# --- توابع مربوط به تنظیمات خوش‌آمدگویی ---
def load_settings():
  if not os.path.exists(SETTINGS_FILE):
    save_settings(DEFAULT_SETTINGS)
  try:
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return DEFAULT_SETTINGS


def save_settings(settings):
  with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
    json.dump(settings, f, ensure_ascii=False, indent=4)


# متن‌های خوش‌آمدگویی
GREETING_TEMPLATES = [
    (
        "**`✦ ──────────────────────────────────────────────────────── ✦`**\n"
        "**`  Hallo {name} ⚘, herzlich willkommen in unserer Runde!`**\n"
        "**`✦ ──────────────────────────────────────────────────────── ✦`**\n\n"
        "**_Schön, dass du da bist! Hier lernen wir gemeinsam Deutsch. "
        "Du kannst üben, neue Wörter lernen und auf Deutsch sprechen. Wir freuen"
        " uns auf dich!_**"
    ),
    (
        "**`✦ ─────────────────────────────────────────── ✦`**\n"
        "**`  Ein warmes Willkommen an dich, {name} ⚘!`**\n"
        "**`✦ ─────────────────────────────────────────── ✦`**\n\n"
        "**_Mach dir keinen Stress beim Lernen. Jeder Fehler hilft dir! "
        "Nimm dir Zeit, lies mit und sprich einfach auf Deutsch mit uns. Wir"
        " freuen uns auf dich!_**"
    ),
    (
        "**`✦ ────────────────────────────────────────── ✦`**\n"
        "**`  Hallo {name} ⚘, toll, dass du hier bist!`**\n"
        "**`✦ ────────────────────────────────────────── ✦`**\n\n"
        "**_Jeder Tag ist eine neue Chance zum Üben. Sprich einfach mit den"
        " anderen auf Deutsch und mach aktiv mit. Zusammen schaffen wir das!"
        " Wir freuen uns auf dich!_**"
    ),
    (
        "**`✦ ──────────────────────────────────────────────── ✦`**\n"
        "**`  Schön, dass du zu uns gefunden hast, {name} ⚘!`**\n"
        "**`✦ ──────────────────────────────────────────────── ✦`**\n\n"
        "**_Hier zählen nicht perfekte Sätze, sondern das Sprechen. Trau dich"
        " einfach, sprich frei auf Deutsch und lerne jeden Tag ein bisschen"
        " mehr. Wir freuen uns auf dich!_**"
    ),
    (
        "**`✦ ───────────────────────────────────────────── ✦`**\n"
        "**`  Hallo, schön dass du dabei bist, {name} ⚘!`**\n"
        "**`✦ ───────────────────────────────────────────── ✦`**\n\n"
        "**_Zusammen macht Deutsch lernen mehr Spaß. Trau dich und sprich"
        " einfach mit. Wir freuen uns auf dich!_**"
    ),
]


# --- راه‌اندازی دیتابیس SQLite برای مدیریت فیدبک‌ها ---
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
            übersetzung_link TEXT
        )
    """)
  conn.commit()
  conn.close()


init_db()


def db_get(original_msg_id):
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT chat_id, bot_emoji_msg_id, korrektur_link, grammatik_link,"
      " vokabel_link, übersetzung_link FROM feedbacks WHERE original_msg_id ="
      " ?",
      (original_msg_id,),
  )
  row = cursor.fetchone()
  conn.close()
  return row


def db_save(
    original_msg_id,
    chat_id,
    bot_emoji_msg_id,
    korrektur_link,
    grammatik_link,
    vokabel_link,
    übersetzung_link,
):
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT OR REPLACE INTO feedbacks 
        (original_msg_id, chat_id, bot_emoji_msg_id, korrektur_link, grammatik_link, vokabel_link, übersetzung_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
      (
          original_msg_id,
          chat_id,
          bot_emoji_msg_id,
          korrektur_link,
          grammatik_link,
          vokabel_link,
          übersetzung_link,
      ),
  )
  conn.commit()
  conn.close()


# تابع ساخت کیبورد هوشمند فیدبک‌ها
def create_dynamic_keyboard(
    korrektur_link=None,
    grammatik_link=None,
    vokabel_link=None,
    übersetzung_link=None,
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
    buttons.append(types.InlineKeyboardButton("📁 Vokabel", url=vokabel_link))

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

  return markup


# --- دستور کنترل خوش‌آمدگویی (/welcome) ---
@bot.message_handler(commands=["welcome"])
def handle_welcome_command(message):
  args = message.text.split()
  settings = load_settings()

  if len(args) > 1:
    action = args[1].lower()
    if action == "on":
      settings["welcome_active"] = True
      save_settings(settings)
      bot.reply_to(
          message, "✅ قابلیت خوشامد
