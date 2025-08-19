import os
import logging
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# --- Config ---
TELEGRAM_TOKEN = "8394102086:AAHnV5Fg8DUS4rz2rzrXD3zVHuBIQ3ri4II"
VAPI_API_KEY = "ab83d1e7-ddf9-4f08-b4e8-bab6f91c42c0"
RENDER_URL = "https://my-telegram-bot-ivas.onrender.com"  # your Render URL

bot = Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Telegram Handlers ---
def start(update: Update, context):
    update.message.reply_text("Send /call <phone_number> to start a Vapi call and ask their age.")

def call_command(update: Update, context):
    if len(context.args) == 0:
        update.message.reply_text("⚠️ Please provide a phone number.\nExample: /call +14155551234")
        return

    phone_number = context.args[0]
    chat_id = update.message.chat_id

    update.message.reply_text(f"📞 Starting call to {phone_number}...")

    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "assistantId": "assistant_default",  # replace with your assistant ID
        "phoneNumber": phone_number,
        "metadata": {
            "telegram_chat_id": chat_id
        },
        "webhook": f"{RENDER_URL}/vapi-webhook"
    }

    res = requests.post("https://api.vapi.ai/call", headers=headers, json=payload)
    if res.status_code == 200:
        update.message.reply_text("✅ Call initiated. I’ll send the response here when the call ends.")
    else:
        update.message.reply_text(f"❌ Failed to start call: {res.text}")

# --- Vapi Webhook ---
@app.route("/vapi-webhook", methods=["POST"])
def vapi_webhook():
    data = request.json
    logger.info(f"📩 Vapi webhook: {data}")

    # Extract transcript / final age answer
    metadata = data.get("metadata", {})
    chat_id = metadata.get("telegram_chat_id")
    transcript = data.get("transcript", "")

    if chat_id and transcript:
        bot.send_message(chat_id=chat_id, text=f"🗣 Call finished. Transcript:\n\n{transcript}")

    return {"status": "ok"}

# --- Telegram Webhook Setup ---
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok", 200

@app.route("/")
def home():
    return "🤖 Bot is running!", 200

# Dispatcher for Telegram
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("call", call_command))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, start))

# --- Main ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
