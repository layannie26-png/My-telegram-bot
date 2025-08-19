import os
import logging
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio

# --- Config ---
TELEGRAM_TOKEN = "8394102086:AAHnV5Fg8DUS4rz2rzrXD3zVHuBIQ3ri4II"
VAPI_API_KEY = "ab83d1e7-ddf9-4f08-b4e8-bab6f91c42c0"
RENDER_URL = "https://my-telegram-bot-ivas.onrender.com"

bot = Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /call <phone_number> to start a Vapi call and ask their age.")

async def call_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Provide a phone number.\nExample: /call +14155551234")
        return

    phone_number = context.args[0]
    chat_id = update.message.chat_id

    await update.message.reply_text(f"📞 Starting call to {phone_number}...")

    headers = {"Authorization": f"Bearer {VAPI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "assistantId": "assistant_default",
        "phoneNumber": phone_number,
        "metadata": {"telegram_chat_id": chat_id},
        "webhook": f"{RENDER_URL}/vapi-webhook"
    }

    res = requests.post("https://api.vapi.ai/call", headers=headers, json=payload)
    if res.status_code == 200:
        await update.message.reply_text("✅ Call initiated. I’ll send the response here when the call ends.")
    else:
        await update.message.reply_text(f"❌ Failed to start call: {res.text}")

# --- PTB Application ---
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("call", call_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

# --- Flask routes ---
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return "ok", 200

@app.route("/vapi-webhook", methods=["POST"])
def vapi_webhook():
    data = request.json
    logger.info(f"📩 Vapi webhook: {data}")

    metadata = data.get("metadata", {})
    chat_id = metadata.get("telegram_chat_id")
    transcript = data.get("transcript", "")

    if chat_id and transcript:
        bot.send_message(chat_id=chat_id, text=f"🗣 Call finished. Transcript:\n\n{transcript}")

    return {"status": "ok"}

@app.route("/")
def home():
    return "🤖 Bot is running!", 200

# --- Startup webhook registration ---
async def set_webhook():
    await bot.set_webhook(f"{RENDER_URL}/{TELEGRAM_TOKEN}")

if __name__ == "__main__":
    # Register Telegram webhook
    asyncio.get_event_loop().run_until_complete(set_webhook())
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
