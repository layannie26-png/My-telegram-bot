import telebot
from flask import Flask, request, jsonify
import requests

# --- Your Credentials ---
TOKEN = "8394102086:AAHnV5Fg8DUS4rz2rzrXD3zVHuBIQ3ri4II"   # Telegram bot token
VAPI_API_KEY = "ab83d1e7-ddf9-4f08-b4e8-bab6f91c42c0"               # Get from Vapi dashboard
RENDER_URL = "https://my-telegram-bot-ivas.onrender.com"  # Your Render app URL

# --- Setup ---
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# Store mapping of user -> chat_id so we can reply after Vapi callback
user_chat_map = {}

# --- Telegram Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Hello! Send `/callme <phone_number>` and I’ll call you.")

@bot.message_handler(commands=['callme'])
def call_user(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /callme <phone_number>")
            return

        phone_number = parts[1]
        user_chat_map[message.from_user.id] = message.chat.id

        # --- Call Vapi API ---
        headers = {"Authorization": f"Bearer {VAPI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "phoneNumber": phone_number,
            "assistant": {
                "firstMessage": "Hello! What’s your age?",
                "model": "gpt-4o-mini"
            },
            "metadata": {
                "telegram_user_id": message.from_user.id
            },
            "webhookUrl": f"{RENDER_URL}/vapi-callback"
        }

        res = requests.post("https://api.vapi.ai/call", json=payload, headers=headers)

        if res.status_code == 200:
            bot.reply_to(message, f"📞 Calling {phone_number}... Answer and I’ll ask your age!")
        else:
            bot.reply_to(message, f"⚠️ Call failed: {res.text}")

    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

# --- Vapi Webhook ---
@app.route("/vapi-callback", methods=['POST'])
def vapi_callback():
    data = request.json
    print("📞 Vapi callback:", data)

    transcript = data.get("transcript", "")
    user_id = data.get("metadata", {}).get("telegram_user_id")

    if user_id and user_id in user_chat_map:
        chat_id = user_chat_map[user_id]
        bot.send_message(chat_id, f"✅ You said your age is: {transcript}")

    return jsonify(success=True)

# --- Telegram Webhook ---
@app.route("/webhook", methods=['POST'])
def telegram_webhook():
    if request.headers.get("content-type") == "application/json":
        update = telebot.types.Update.de_json(request.get_data().decode("UTF-8"))
        bot.process_new_updates([update])
        return "", 200
    return "Unsupported Media Type", 415

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
