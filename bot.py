import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import requests
import asyncio

# ========================
# CONFIG (your real keys)
# ========================
TELEGRAM_TOKEN = "8394102086:AAHnV5Fg8DUS4rz2rzrXD3zVHuBIQ3ri4II"
VAPI_API_KEY   = "ab83d1e7-ddf9-4f08-b4e8-bab6f91c42c0"
RENDER_URL     = "https://my-telegram-bot-ivas.onrender.com"

# ========================
# FLASK APP
# ========================
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ========================
# TELEGRAM BOT APP
# ========================
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Use /call +1234567890 to make a call.")

# Call command
async def call_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Please provide a phone number.\nExample: /call +14155551234")
        return
    
    phone_number = context.args[0]
    chat_id = update.effective_chat.id  # ✅ fixed

    await update.message.reply_text(f"📞 Calling {phone_number}...")

    # Trigger Vapi call
    response = requests.post(
        "https://api.vapi.ai/call",
        headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
        json={
            "assistant": {
                "model": "gpt-4o-mini",
                "voice": "alloy",
                "firstMessage": "Hi! I just need to ask your age."
            },
            "phoneNumber": phone_number,
            "metadata": {"telegram_chat_id": chat_id},
            "webhook": f"{RENDER_URL}/vapi-webhook"
        }
    )

    if response.status_code == 200:
        await update.message.reply_text("✅ Call started!")
    else:
        await update.message.reply_text(f"❌ Call failed: {response.text}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("call", call_command))

# ========================
# TELEGRAM WEBHOOK ENDPOINT
# ========================
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    """Handle incoming updates from Telegram"""
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))
    return {"ok": True}

# ========================
# VAPI WEBHOOK ENDPOINT
# ========================
@app.route("/vapi-webhook", methods=["POST"])
def vapi_webhook():
    data = request.json
    logging.info(f"📩 Incoming Vapi webhook: {data}")

    chat_id = data.get("metadata", {}).get("telegram_chat_id")
    transcript = data.get("transcript")

    if chat_id and transcript:
        asyncio.run(telegram_app.bot.send_message(  # ✅ fixed (async)
            chat_id=chat_id,
            text=f"📝 Call result: {transcript}"
        ))

    return {"ok": True}

# ========================
# START FLASK ONLY
# ========================
if __name__ == "__main__":
    # ✅ async webhook setup
    async def set_webhook():
        await telegram_app.bot.set_webhook(url=f"{RENDER_URL}/{TELEGRAM_TOKEN}")

    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=5000)
