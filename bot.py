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
            übersetzung_link TEXT,
            back_link TEXT
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
      " vokabel_link, übersetzung_link, back_link FROM feedbacks WHERE"
      " original_msg_id = ?",
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
    back_link,
):
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT OR REPLACE INTO feedbacks 
        (original_msg_id, chat_id, bot_emoji_msg_id, korrektur_link, grammatik_link, vokabel_link, übersetzung_link, back_link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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

  # اضافه کردن دکمه بک در صورت وجود لینک
  if back_link:
    markup.add(types.InlineKeyboardButton("⬅️ Deutsch sprechen", url=back_link))

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
          message, "✅ قابلیت خوشامدگویی با موفقیت **روشن (ON)** شد."
      )
      return
    elif action == "off":
      settings["welcome_active"] = False
      save_settings(settings)
      bot.reply_to(
          message, "❌ قابلیت خوشامدگویی با موفقیت **خاموش (OFF)** شد."
      )
      return

  status = (
      "روشن (ON)" if settings.get("welcome_active", True) else "خاموش (OFF)"
  )
  bot.reply_to(
      message,
      f"وضعیت فعلی خوشامدگویی: {status}\nبرای تغییر از `/welcome on` یا"
      " `/welcome off` استفاده کنید.",
  )


# --- هندلر ورود عضو جدید به گروه ---
@bot.message_handler(content_types=["new_chat_members"])
def handle_new_member(message):
  settings = load_settings()
  if not settings.get("welcome_active", True):
    return

  for new_member in message.new_chat_members:
    if new_member.is_bot:
      continue

    raw_name = new_member.first_name
    if not raw_name or raw_name.strip() in ["", ".", "-", "_"]:
      user_name = "mein Freund"
    else:
      user_name = raw_name.strip()

    counter = settings.get("counter", 0)
    template = GREETING_TEMPLATES[counter]
    greeting_text = template.format(name=user_name)

    bot.send_message(message.chat.id, greeting_text, parse_mode="Markdown")

    settings["counter"] = (counter + 1) % len(GREETING_TEMPLATES)
    save_settings(settings)


# --- دستور دستی ست کردن لینک‌ها (/setlink) ---
@bot.message_handler(
    func=lambda message: message.text
    and message.text.startswith("/setlink")
    and message.from_user.id in ADMIN_IDS
)
def set_link_manually(message):
  parts = message.text.split()
  if len(parts) < 3:
    return

  link_type = parts[1].lower()
  new_link = parts[2]
  chat_id = message.chat.id
  thread_id = getattr(message, "message_thread_id", None)

  if not message.reply_to_message:
    return
  target_msg_id = message.reply_to_message.message_id

  data = db_get(target_msg_id)
  if data:
    _, bot_emoji_msg_id, k_link, g_link, v_link, ü_link, b_link = data
  else:
    bot_emoji_msg_id = None
    k_link, g_link, v_link, ü_link, b_link = None, None, None, None, None

  if link_type == "korrektur":
    k_link = new_link
  elif link_type == "grammatik":
    g_link = new_link
  elif link_type == "vokabel":
    v_link = new_link
  elif link_type in ["übersetzung", "ubersetzung"]:
    ü_link = new_link
  elif link_type == "back":
    b_link = new_link
  else:
    return

  markup = create_dynamic_keyboard(k_link, g_link, v_link, ü_link, b_link)

  if bot_emoji_msg_id:
    try:
      bot.edit_message_text(
          chat_id=chat_id,
          message_id=bot_emoji_msg_id,
          text=EMOJI_TEXT,
          reply_markup=markup,
      )
    except Exception:
      pass
  else:
    try:
      sent_msg = bot.send_message(
          chat_id=chat_id,
          text=EMOJI_TEXT,
          reply_markup=markup,
          reply_to_message_id=target_msg_id,
          message_thread_id=thread_id,
      )
      bot_emoji_msg_id = sent_msg.message_id
    except Exception:
      pass

  db_save(
      target_msg_id,
      chat_id,
      bot_emoji_msg_id,
      k_link,
      g_link,
      v_link,
      ü_link,
      b_link,
  )

  try:
    bot.delete_message(chat_id, message.message_id)
  except Exception:
    pass


# --- دستور افزودن دستی دکمه (نسخه مخفف: /addbtn) ---
@bot.message_handler(
    func=lambda message: message.text
    and message.text.startswith("/addbtn")
    and message.from_user.id in ADMIN_IDS
)
def add_button_with_link(message):
  parts = message.text.split(maxsplit=2)
  if len(parts) < 3:
    return

  button_type = parts[1].lower()
  new_link = parts[2]
  chat_id = message.chat.id
  thread_id = getattr(message, "message_thread_id", None)

  if "back" in button_type:
    try:
      back_markup = types.InlineKeyboardMarkup()
      back_markup.add(
          types.InlineKeyboardButton("⬅️ Deutsch sprechen", url=new_link)
      )
      bot.send_message(
          chat_id=chat_id,
          text=EMOJI_TEXT,
          reply_markup=back_markup,
          message_thread_id=thread_id,
      )
    except Exception:
      pass
  else:
    if not message.reply_to_message:
      return
    target_msg_id = message.reply_to_message.message_id

    data = db_get(target_msg_id)
    if data:
      _, bot_emoji_msg_id, k_link, g_link, v_link, ü_link, b_link = data
    else:
      bot_emoji_msg_id = None
      k_link, g_link, v_link, ü_link, b_link = None, None, None, None, None

    if "korrektur" in button_type:
      k_link = new_link
    elif "grammatik" in button_type:
      g_link = new_link
    elif "vokabel" in button_type:
      v_link = new_link
    elif "übersetzung" in button_type or "ubersetzung" in button_type:
      ü_link = new_link
    else:
      return

    markup = create_dynamic_keyboard(k_link, g_link, v_link, ü_link, b_link)

    if bot_emoji_msg_id:
      try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=bot_emoji_msg_id,
            text=EMOJI_TEXT,
            reply_markup=markup,
        )
      except Exception:
        pass
    else:
      try:
        sent_msg = bot.send_message(
            chat_id=chat_id,
            text=EMOJI_TEXT,
            reply_markup=markup,
            reply_to_message_id=target_msg_id,
            message_thread_id=thread_id,
        )
        bot_emoji_msg_id = sent_msg.message_id
      except Exception:
        pass

    db_save(
        target_msg_id,
        chat_id,
        bot_emoji_msg_id,
        k_link,
        g_link,
        v_link,
        ü_link,
        b_link,
    )

  try:
    bot.delete_message(chat_id, message.message_id)
  except Exception:
    pass


# --- دستور جدید حذف دکمه (نسخه مخفف: /delbtn) ---
@bot.message_handler(
    func=lambda message: message.text
    and message.text.startswith("/delbtn")
    and message.from_user.id in ADMIN_IDS
)
def delete_button_handler(message):
  parts = message.text.split()
  if len(parts) < 2 or not message.reply_to_message:
    return

  button_type = parts[1].lower()
  target_msg_id = message.reply_to_message.message_id
  chat_id = message.chat.id

  data = db_get(target_msg_id)
  if not data:
    return

  _, bot_emoji_msg_id, k_link, g_link, v_link, ü_link, b_link = data

  if "korrektur" in button_type:
    k_link = None
  elif "grammatik" in button_type:
    g_link = None
  elif "vokabel" in button_type:
    v_link = None
  elif "übersetzung" in button_type or "ubersetzung" in button_type:
    ü_link = None
  elif "back" in button_type:
    b_link = None
  else:
    return

  markup = create_dynamic_keyboard(k_link, g_link, v_link, ü_link, b_link)

  if bot_emoji_msg_id:
    try:
      if not any([k_link, g_link, v_link, ü_link, b_link]):
        bot.delete_message(chat_id, bot_emoji_msg_id)
        bot_emoji_msg_id = None
      else:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=bot_emoji_msg_id,
            text=EMOJI_TEXT,
            reply_markup=markup,
        )
    except Exception:
      pass

  db_save(
      target_msg_id,
      chat_id,
      bot_emoji_msg_id,
      k_link,
      g_link,
      v_link,
      ü_link,
      b_link,
  )

  try:
    bot.delete_message(chat_id, message.message_id)
  except Exception:
    pass


# --- هندلر کلی پیام‌های گروه برای فیدبک‌‌خوانی ---
@bot.message_handler(
    func=lambda message: True,
    content_types=["text", "audio", "voice", "document", "photo"],
)
def handle_messages(message):
  if message.text and (
      message.text.startswith("/setlink")
      or message.text.startswith("/addbtn")
      or message.text.startswith("/delbtn")
  ):
    return

  if message.from_user.id in ADMIN_IDS:
    chat_id = message.chat.id
    thread_id = getattr(message, "message_thread_id", None)

    # حالت اول: پیام در تاپیک Übersetzung
    if thread_id == TOPIC_ÜBERSETZUNG and message.reply_to_message:
      match = re.search(r"t\.me/c/\d+/(?P<orig_id>\d+)", message.text or "")
      if match:
        original_msg_id = int(match.group("orig_id"))

        chat_username_or_id = str(chat_id).replace("-100", "")
        feedback_link = f"https://t.me/c/{chat_username_or_id}/{message.reply_to_message.message_id}"

        data = db_get(original_msg_id)
        if data:
          _, bot_emoji_msg_id, k_link, g_link, v_link, ü_link, b_link = data
        else:
          bot_emoji_msg_id = None
          k_link, g_link, v_link, ü_link, b_link = None, None, None, None, None

        ü_link = feedback_link
        markup = create_dynamic_keyboard(
            k_link, g_link, v_link, ü_link, b_link
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
            pass
        else:
          try:
            sent_msg = bot.send_message(
                chat_id=chat_id,
                text=EMOJI_TEXT,
                reply_markup=markup,
                reply_to_message_id=original_msg_id,
                message_thread_id=thread_id,
            )
            bot_emoji_msg_id = sent_msg.message_id
          except Exception:
            pass

        db_save(
            original_msg_id,
            chat_id,
            bot_emoji_msg_id,
            k_link,
            g_link,
            v_link,
            ü_link,
            b_link,
        )

        try:
          original_chat_username = str(chat_id).replace("-100", "")
          original_message_link = (
              f"https://t.me/c/{original_chat_username}/{original_msg_id}"
          )

          back_markup = types.InlineKeyboardMarkup()
          back_markup.add(
              types.InlineKeyboardButton(
                  "⬅️ Deutsch sprechen", url=original_message_link
              )
          )

          bot.edit_message_reply_markup(
              chat_id=chat_id,
              message_id=message.reply_to_message.message_id,
              reply_markup=back_markup,
          )
        except Exception:
          pass

        try:
          bot.delete_message(chat_id, message.message_id)
        except Exception:
          pass
        return

    # حالت دوم: پیام در سایر تاپیک‌ها
    if message.reply_to_message:
      original_msg = message.reply_to_message
      original_msg_id = original_msg.message_id

      chat_username_or_id = str(chat_id).replace("-100", "")
      feedback_link = f"https://t.me/c/{chat_username_or_id}/{message.message_id}"

      data = db_get(original_msg_id)
      if data:
        _, bot_emoji_msg_id, k_link, g_link, v_link, ü_link, b_link = data
      else:
        bot_emoji_msg_id = None
        k_link, g_link, v_link, ü_link, b_link = None, None, None, None, None

      if thread_id == TOPIC_KORREKTUR or message.forward_from_chat:
        k_link = feedback_link
      elif thread_id == TOPIC_GRAMMATIK:
        g_link = feedback_link
      elif thread_id == TOPIC_VOKABEL:
        v_link = feedback_link

      markup = create_dynamic_keyboard(k_link, g_link, v_link, ü_link, b_link)

      if bot_emoji_msg_id:
        try:
          bot.edit_message_text(
              chat_id=chat_id,
              message_id=bot_emoji_msg_id,
              text=EMOJI_TEXT,
              reply_markup=markup,
          )
        except Exception:
          pass
      else:
        try:
          data_sent_msg = bot.send_message(
              chat_id=chat_id,
              text=EMOJI_TEXT,
              reply_markup=markup,
              reply_to_message_id=original_msg_id,
              message_thread_id=thread_id,
          )
          bot_emoji_msg_id = data_sent_msg.message_id
        except Exception:
          pass

      db_save(
          original_msg_id,
          chat_id,
          bot_emoji_msg_id,
          k_link,
          g_link,
          v_link,
          ü_link,
          b_link,
      )

      try:
        original_chat_username = str(chat_id).replace("-100", "")
        original_message_link = (
            f"https://t.me/c/{original_chat_username}/{original_msg_id}"
        )

        back_markup = types.InlineKeyboardMarkup()
        back_markup.add(
            types.InlineKeyboardButton(
                "⬅️ Deutsch sprechen", url=original_message_link
            )
        )

        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message.message_id,
            reply_markup=back_markup,
        )
      except Exception:
        pass


# --- راه‌اندازی برای هاست ابری (Webhook) ---
from flask import Flask, request

app = Flask(__name__)


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


@app.route("/")
def index():
  return "Bot is running!", 200


if __name__ == "__main__":
  # تنظیم خودکار وب‌هوک روی رندر
  WEBHOOK_URL = f"https://my-bot-0jtw.onrender.com/{TOKEN}"
  bot.remove_webhook()
  bot.set_webhook(url=WEBHOOK_URL)

  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
