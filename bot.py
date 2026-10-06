Import os
import sqlite3
import telebot
from flask import Flask, request

# --- تنظیمات اولیه ربات ---
TOKEN = "8879831216:AAF1Qs8S1Yaz_GkbNgIYrnkYQ31pJzqStCE"
bot = telebot.TeleBot(TOKEN)

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
            back_link TEXT
        )
    """)
  conn.commit()
  conn.close()


init_db()


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
  return "Bot is running and core is active!", 200


if __name__ == "__main__":
  # تنظیم خودکار وب‌هوک روی رندر
  WEBHOOK_URL = f"https://my-bot-0jtw.onrender.com/{TOKEN}"
  bot.remove_webhook()
  bot.set_webhook(url=WEBHOOK_URL)

  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
