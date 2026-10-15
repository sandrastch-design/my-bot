import json
import os
import re
import sqlite3
import telebot
from telebot import types
from flask import Flask, request

# --- تنظیمات اولیه ربات ---
TOKEN = "8879831216:AAGVuAnAH7SgDwniBNGxd0jF_grYUgPZm0o"
bot = telebot.TeleBot(TOKEN)

# متن پیام ربات شامل ایموجی‌ها
EMOJI_TEXT = "⚜" 

# --- تنظیمات تاپیک‌ها و ادمین‌ها ---
TOPIC_KORREKTUR = 198  # شناسه تاپیک کرکتور
TOPIC_GRAMMATIK = 132  # شناسه تاپیک گرامر
TOPIC_VOKABEL = 133  # شناسه تاپیک لغت
TOPIC_ÜBERSETZUNG = 131  # شناسه تاپیک ترجمه

ADMIN_IDS = [103743272]

# کلماتی که ربات نباید برایشان ایموجی خودکار بفرستد
EXCEPTION_KEYWORDS = ["vokabel", "grammatik", "korrektur"]

# مسیر فایل ذخیره تنظیمات و شمارنده چرخش خوش‌آمدگویی
SETTINGS_FILE = "welcome_settings.json"

# تنظیمات پیش‌فرضِ اولیه خوشآمدگویی
DEFAULT_SETTINGS = {
    "welcome_active": True,
    "counter": 0,
}


# --- توابع مربوط به تنظیمات خوش‌آمدگویی ---
def load_welcome_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_welcome_settings(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_SETTINGS


def save_welcome_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)


# متن‌های خوش‌آمدگویی
GREETING_TEMPLATES = [
    (
        "**` ─────────────────── ✦`**\n"
        "**`  Hallo {name} ⚘, herzlich willkommen in unserer Runde!`**\n"
        "**`✦ ─────────────────── `**\n\n"
        "**_Schön, dass du da bist! Hier lernen wir gemeinsam Deutsch. "
        "Du kannst üben, neue Wörter lernen und auf Deutsch sprechen. Wir freuen"
        " uns auf dich! ♡_**\n\n"
        "ㅤ"
    ),
    (
        "**` ─────────────────── ✦`**\n"
        "**`  Ein warmes Willkommen an dich, {name} ⚘!`**\n"
        "**`✦ ─────────────────── `**\n\n"
        "**_Mach dir keinen Stress beim Lernen. Jeder Fehler hilft dir! "
        "Nimm dir Zeit, lies mit und sprich einfach auf Deutsch mit uns. Wir"
        " freuen uns auf dich! ♡_**\n\n"
        "ㅤ"
    ),
    (
        "**` ─────────────────── ✦`**\n"
        "**`  Hallo {name} ⚘, toll, dass du hier bist!`**\n"
        "**`✦ ─────────────────── `**\n\n"
        "**_Jeder Tag ist eine neue Chance zum Üben. Sprich einfach mit den"
        " anderen auf Deutsch und mach aktiv mit. Zusammen schaffen wir das!"
        " Wir freuen uns auf dich! ♡_**\n\n"
        "ㅤ"
    ),         
    (
        "**` ─────────────────── ✦`**\n"
        "**`  Schön, dass du zu uns gefunden hast, {name} ⚘!`**\n"
        "**`✦ ─────────────────── `**\n\n"
        "**_Hier zählen nicht perfekte Sätze, sondern das Sprechen. Trau dich"
        " einfach, sprich frei auf Deutsch und lerne jeden Tag ein bisschen"
        " mehr. Wir freuen uns auf dich! ♡_**\n"
        "ㅤ"
    ),
    (
        "**` ─────────────────── ✦`**\n"
        "**`  Hallo, schön dass du dabei bist, {name} ⚘!`**\n"
        "**`✦ ─────────────────── `**\n\n"
        "**_Zusammen macht Deutsch lernen mehr Spaß. Trau dich und sprich"
        " einfach mit. Wir freuen uns auf dich! ♡_**\n\n"
        "ㅤ"
    ),
]


# --- بررسی اینکه آیا پیام در چت اصلی است یا تاپیک ---
def is_main_chat(message):
    if getattr(message, "message_thread_id", None):
        return False
    return True


# --- استخراج امن متن از پیام (متن یا کپشن) ---
def get_message_text(message):
    if message.text:
        return message.text
    elif message.caption:
        return message.caption
    return None


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


# --- توابع مدیریت دیتابیس برای دکمه‌ها ---
def get_button_state(original_msg_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bot_emoji_msg_id, korrektur_link, grammatik_link, vokabel_link, übersetzung_link, back_link, message_thread_id 
        FROM feedbacks WHERE original_msg_id = ?
    """, (original_msg_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_state_by_bot_emoji_id(bot_emoji_msg_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT original_msg_id, bot_emoji_msg_id, korrektur_link, grammatik_link, vokabel_link, übersetzung_link, back_link, message_thread_id 
        FROM feedbacks WHERE bot_emoji_msg_id = ?
    """, (bot_emoji_msg_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def save_or_update_button_state(
    original_msg_id, chat_id, bot_emoji_msg_id,
    korrektur_link=None, grammatik_link=None, vokabel_link=None,
    übersetzung_link=None, back_link=None, message_thread_id=None
):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT original_msg_id FROM feedbacks WHERE original_msg_id = ?", (original_msg_id,))
    exists = cursor.fetchone()

    if exists:
        if korrektur_link is not None:
            cursor.execute("UPDATE feedbacks SET korrektur_link = ? WHERE original_msg_id = ?", (korrektur_link, original_msg_id))
        if grammatik_link is not None:
            cursor.execute("UPDATE feedbacks SET grammatik_link = ? WHERE original_msg_id = ?", (grammatik_link, original_msg_id))
        if vokabel_link is not None:
            cursor.execute("UPDATE feedbacks SET vokabel_link = ? WHERE original_msg_id = ?", (vokabel_link, original_msg_id))
        if übersetzung_link is not None:
            cursor.execute("UPDATE feedbacks SET übersetzung_link = ? WHERE original_msg_id = ?", (übersetzung_link, original_msg_id))
        if back_link is not None:
            cursor.execute("UPDATE feedbacks SET back_link = ? WHERE original_msg_id = ?", (back_link, original_msg_id))
        if message_thread_id is not None:
            cursor.execute("UPDATE feedbacks SET message_thread_id = ? WHERE original_msg_id = ?", (message_thread_id, original_msg_id))
    else:
        cursor.execute("""
            INSERT INTO feedbacks (original_msg_id, chat_id, bot_emoji_msg_id, korrektur_link, grammatik_link, vokabel_link, übersetzung_link, back_link, message_thread_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (original_msg_id, chat_id, bot_emoji_msg_id, korrektur_link, grammatik_link, vokabel_link, übersetzung_link, back_link, message_thread_id))

    conn.commit()
    conn.close()


# --- تابع ساخت کیبورد هوشمند ---
def create_dynamic_keyboard(
    korrektur_link=None, grammatik_link=None,
    vokabel_link=None, übersetzung_link=None, back_link=None
):
    markup = types.InlineKeyboardMarkup()
    row1 = []
    row2 = []
    row_back = []

    all_main_buttons = []
    if übersetzung_link:
        all_main_buttons.append(types.InlineKeyboardButton("📝 Übersetzungㅤ", url=übersetzung_link))
    if korrektur_link:
        all_main_buttons.append(types.InlineKeyboardButton("🔍 Korrekturㅤ", url=korrektur_link))
    if vokabel_link:
        all_main_buttons.append(types.InlineKeyboardButton("📁 Vokabelㅤ", url=vokabel_link))
    if grammatik_link:
        all_main_buttons.append(types.InlineKeyboardButton("✍ Grammatikㅤ", url=grammatik_link))

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
        row_back.append(types.InlineKeyboardButton("⬅️ Deutsch sprechen", url=back_link))

    if row1:
        markup.row(*row1)
    if row2:
        markup.row(*row2)
    if row_back:
        markup.row(*row_back)

    return markup


# ==========================================
# ۰. دستور کنترل خوش‌آمدگویی (/welcome)
# ==========================================
@bot.message_handler(commands=["welcome"])
def handle_welcome_command(message):
    args = message.text.split()
    settings = load_welcome_settings()

    if len(args) > 1:
        action = args[1].lower()
        if action == "on":
            settings["welcome_active"] = True
            save_welcome_settings(settings)
            bot.reply_to(message, "✅ قابلیت خوشامدگویی با موفقیت **روشن (ON)** شد.")
            return
        elif action == "off":
            settings["welcome_active"] = False
            save_welcome_settings(settings)
            bot.reply_to(message, "❌ قابلیت خوشامدگویی با موفقیت **خاموش (OFF)** شد.")
            return

    status = "روشن (ON)" if settings.get("welcome_active", True) else "خاموش (OFF)"
    bot.reply_to(
        message,
        f"وضعیت فعلی خوشامدگویی: {status}\nبرای تغییر از `/welcome on` یا `/welcome off` استفاده کنید."
    )


# ==========================================
# ۰.۱. هندلر ورود عضو جدید به گروه
# ==========================================
@bot.message_handler(content_types=["new_chat_members"])
def handle_new_member(message):
    settings = load_welcome_settings()
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
        save_welcome_settings(settings)


# ==========================================
# ۱. هندلر دستور دستی addbtn
# ==========================================
@bot.message_handler(commands=["addbtn"])
def handle_add_button(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if not message.reply_to_message:
        return

    replied_msg = message.reply_to_message
    chat_id = message.chat.id

    state = get_button_state(replied_msg.message_id)
    original_msg_id = replied_msg.message_id

    if not state:
        bot_state_check = get_state_by_bot_emoji_id(replied_msg.message_id)
        if bot_state_check:
            original_msg_id = bot_state_check[0]
            state = get_button_state(original_msg_id)

    message_thread_id = getattr(replied_msg, "message_thread_id", None)
    if not message_thread_id and state and len(state) > 6 and state[6]:
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
        back_link=back_l
    )

    if bot_emoji_msg_id:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=bot_emoji_msg_id,
                text=EMOJI_TEXT,
                reply_markup=markup
            )
        except Exception:
            kwargs = {"chat_id": chat_id, "text": EMOJI_TEXT, "reply_markup": markup}
            if message_thread_id:
                kwargs["message_thread_id"] = message_thread_id
            
            new_msg = bot.send_message(**kwargs)
            bot_emoji_msg_id = new_msg.message_id
    else:
        kwargs = {"chat_id": chat_id, "text": EMOJI_TEXT, "reply_markup": markup}
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
        message_thread_id=message_thread_id
    )

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass


# ==========================================
# ۲. هندلر دستور حذف دستی دکمه (delbtn)
# ==========================================
@bot.message_handler(commands=["delbtn", "removebtn"])
def handle_delete_button(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if not message.reply_to_message:
        return

    replied_msg = message.reply_to_message
    chat_id = message.chat.id

    state = get_button_state(replied_msg.message_id)
    original_msg_id = replied_msg.message_id

    if not state:
        bot_state_check = get_state_by_bot_emoji_id(replied_msg.message_id)
        if bot_state_check:
            original_msg_id = bot_state_check[0]
            state = get_button_state(original_msg_id)

    if not state:
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return

    message_thread_id = state[6] if len(state) > 6 and state[6] else getattr(replied_msg, "message_thread_id", None)

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return

    btn_name = parts[1].strip().lower()

    bot_emoji_msg_id = state[0]
    korrektur_l = state[1]
    grammatik_l = state[2]
    vokabel_l = state[3]
    übersetzung_l = state[4]
    back_l = state[5] if len(state) > 5 else None

    if btn_name == "übersetzung":
        übersetzung_l = None
    elif btn_name == "korrektur":
        korrektur_l = None
    elif btn_name == "vokabel":
        vokabel_l = None
    elif btn_name == "grammatik":
        grammatik_l = None
    elif btn_name == "back":
        back_l = None
    else:
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return

    markup = create_dynamic_keyboard(
        korrektur_link=korrektur_l,
        grammatik_link=grammatik_l,
        vokabel_link=vokabel_l,
        übersetzung_link=übersetzung_l,
        back_link=back_l
    )

    try:
        has_buttons = any([korrektur_l, grammatik_l, vokabel_l, übersetzung_l, back_l])
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=bot_emoji_msg_id,
            text=EMOJI_TEXT,
            reply_markup=markup if has_buttons else None
        )
    except Exception as e:
        print(f"Error updating message: {e}")

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE feedbacks 
        SET korrektur_link = ?, grammatik_link = ?, vokabel_link = ?, übersetzung_link = ?, back_link = ?
        WHERE original_msg_id = ?
    """, (korrektur_l, grammatik_l, vokabel_l, übersetzung_l, back_l, original_msg_id))
    conn.commit()
    conn.close()

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass


# ==========================================
# ۳. هندلر دستور reply 
# ==========================================
@bot.message_handler(
    func=lambda m: m.text and m.text.strip().lower() == "reply",
    content_types=["text", "audio", "voice", "photo", "document", "video", "sticker"]
)
def handle_manual_reply(message):
    if not is_main_chat(message):
        return

    if not message.reply_to_message:
        return

    target_msg = message.reply_to_message
    chat_id = message.chat.id

    sent_msg = bot.send_message(
        chat_id=chat_id, text=EMOJI_TEXT, reply_to_message_id=target_msg.message_id
    )
    
    save_or_update_button_state(
        original_msg_id=target_msg.message_id,
        chat_id=chat_id,
        bot_emoji_msg_id=sent_msg.message_id,
        message_thread_id=getattr(target_msg, "message_thread_id", None)
    )

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass


# --- منطق تشخیص هشتگ ---
def process_hashtag_logic(message):
    if not is_main_chat(message):
        return

    text = get_message_text(message)
    if not text:
        return

    text_stripped = text.strip()
    if "#" in text_stripped:
        words_after_hash = [
            w.lower() for w in text_stripped.replace("#", " ").split() if w.strip()
        ]

        if any(ex in words_after_hash for ex in EXCEPTION_KEYWORDS):
            return

        sent_msg = bot.send_message(chat_id=message.chat.id, text=EMOJI_TEXT)
        
        save_or_update_button_state(
            original_msg_id=message.message_id,
            chat_id=message.chat.id,
            bot_emoji_msg_id=sent_msg.message_id,
            message_thread_id=getattr(message, "message_thread_id", None)
        )


# ==========================================
# ۴. هندلر عمومی برای بقیه پیام‌ها و هشتگ‌ها
# ==========================================
@bot.message_handler(
    func=lambda m: True,
    content_types=[
        "text",
        "audio",
        "voice",
        "photo",
        "document",
        "video",
        "sticker",
    ],
)
def handle_all_messages(message):
    process_hashtag_logic(message)


@bot.edited_message_handler(
    func=lambda m: True,
    content_types=[
        "text",
        "audio",
        "voice",
        "photo",
        "document",
        "video",
        "sticker",
    ],
)
def handle_edited_messages(message):
    process_hashtag_logic(message)


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
