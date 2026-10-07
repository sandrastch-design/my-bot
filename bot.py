import json
import os
import re
sqlite3
import telebot
from telebot import types
from flask import Flask, request

# --- تنظیمات اولیه ربات ---
TOKEN = "8879831216:AAF1Qs8S1Yaz_GkbNgIYrnkYQ31pJzqStCE"
bot = telebot.TeleBot(TOKEN)

# متن پیام ربات شامل ایموجی‌ها
EMOJI_TEXT = "💫✨"

# --- استثنائات هشتگ ---
EXCEPTION_KEYWORDS = ["vokabel", "grammatik", "korrektur"]

# --- تنظیمات تاپیک‌ها و ادمین‌ها ---
TOPIC_KORREKTUR = 191  # شناسه تاپیک کرکتور
TOPIC_GRAMMATIK = 188  # شناسه تاپیک گرامر
TOPIC_VOKABEL = 189  # شناسه تاپیک لغت
TOPIC_ÜBERSETZUNG = 334  # شناسه تاپیک ترجمه

ADMIN_IDS = [103743272]


# --- تابع ساخت کیبورد هوشمند (با چیدمان هوشمند ۲تایی) ---
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
        all_main_buttons.append(types.InlineKeyboardButton("📝 übersetzung", url=übersetzung_link))
    if korrektur_link:
        all_main_buttons.append(types.InlineKeyboardButton("🔍 korrektur", url=korrektur_link))
    if vokabel_link:
        all_main_buttons.append(types.InlineKeyboardButton("📁 vokabel", url=vokabel_link))
    if grammatik_link:
        all_main_buttons.append(types.InlineKeyboardButton("✍ grammatik", url=grammatik_link))

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


# --- بررسی اینکه آیا پیام در چت اصلی است یا تاپیک ---
def is_main_chat(message):
    if getattr(message, "message_thread_id", None):
        return False
    return True


# --- استخراج امن متن از پیام ---
def get_message_text(message):
    if message.text:
        return message.text
    elif message.caption:
        return message.caption
    return None


# --- تشخیص خودکار هشتگ (مخصوص چت اصلی) ---
def process_hashtag_logic(message):
    if not is_main_chat(message):
        return

    text = get_message_text(message)
    if not text:
        return

    text_stripped = text.strip()
    
    # بررسی حالت دستی reply
    if text_stripped.lower() == "reply" and message.reply_to_message:
        chat_id = message.chat.id
        target_msg = message.reply_to_message
        
        bot.send_message(
            chat_id=chat_id, text=EMOJI_TEXT, reply_to_message_id=target_msg.message_id
        )
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return

    # بررسی هشتگ‌ها
    if "#" in text_stripped:
        words_after_hash = [
            w.lower() for w in text_stripped.replace("#", " ").split() if w.strip()
        ]

        if any(ex in words_after_hash for ex in EXCEPTION_KEYWORDS):
            return

        bot.send_message(chat_id=message.chat.id, text=EMOJI_TEXT)


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


# --- هندلر دستور دستی addbtn (نسخه هوشمند بدون وابستگی به دیتابیس) ---
@bot.message_handler(commands=["addbtn"])
def handle_add_button(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if not message.reply_to_message:
        return

    target_msg = message.reply_to_message
    chat_id = message.chat.id

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return

    btn_name = parts[1].strip().lower()
    btn_link = parts[2].strip()

    # استخراج دکمه‌های قبلی از روی کیبورد شیشه‌ایِ خودِ پیام هدف (اگر وجود داشته باشد)
    korrektur_l = None
    grammatik_l = None
    vokabel_l = None
    übersetzung_l = None
    back_l = None

    if target_msg.reply_markup and target_msg.reply_markup.keyboard:
        for row in target_msg.reply_markup.keyboard:
            for btn in row:
                text = btn.text.lower()
                url = btn.url
                if "übersetzung" in text:
                    übersetzung_l = url
                elif "korrektur" in text:
                    korrektur_l = url
                elif "vokabel" in text:
                    vokabel_l = url
                elif "grammatik" in text:
                    grammatik_l = url
                elif "deutsch sprechen" in text:
                    back_l = url

    # اضافه یا آپدیت کردن لینک جدید
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

    # ساخت کیبورد جدید
    markup = create_dynamic_keyboard(
        korrektur_link=korrektur_l,
        grammatik_link=grammatik_l,
        vokabel_link=vokabel_l,
        übersetzung_link=übersetzung_l,
        back_link=back_l
    )

    # ویرایش مستقیم همان پیام ایموجیِ هدف
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=target_msg.message_id,
            text=EMOJI_TEXT,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error editing message: {e}")

    # پاک کردن دستور addbtn ادمین برای مرتب ماندن چت
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
