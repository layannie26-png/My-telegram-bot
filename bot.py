import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import requests

# ========================
# CONFIG
# ========================
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"   # replace with your bot token
VAPI_API_KEY   = "YOUR_VAPI_API_KEY"         # replace with your Vapi API key
RENDER_URL     = "https://your-render-app.onrender.com"  # replace with your Render app url

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
# VAPI WEBHOOK ENDPOINT
# ========================
@app.route("/vapi-webhook", methods=["POST"])
def vapi_webhook():
    data = request.json
    logging.info(f"📩 Incoming Vapi webhook: {data}")

    if data.get("transcript"):
        text = data["transcript"]
        # Send transcript to Telegram chat (use your own chat_id if needed)
        telegram_app.bot.send_message(
            chat_id=data.get("metadata", {}).get("chat_id", "<your_chat_id_here>"),
            text=f"📝 Call result: {text}"
        )

    return {"ok": True}

# ========================
# START FLASK + TELEGRAM
# ========================
if __name__ == "__main__":
    import threading

    # Run Telegram bot in a thread
    def run_telegram():
        telegram_app.run_polling()

    threading.Thread(target=run_telegram, daemon=True).start()

    # Run Flask app
    app.run(host="0.0.0.0", port=5000)
