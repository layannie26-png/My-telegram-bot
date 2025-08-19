import telebot
from flask import Flask, request

TOKEN = "8394102086:AAHnV5Fg8DUS4rz2rzrXD3zVHuBIQ3ri4II"
bot = telebot.TeleBot(TOKEN, threaded=False)  # safer for Render
app = Flask(__name__)

# --- Handlers ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    print(f"📩 /start or /help from {message.from_user.id}")  # log incoming
    bot.reply_to(message, "✅ Bot is alive on Render!")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    print(f"📩 Message from {message.from_user.id}: {message.text}")  # log
    bot.reply_to(message, f"You said: {message.text}")

# --- Webhook Route ---
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        print(f"🌐 Incoming update JSON: {json_str}")  # log raw update
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return '', 200
    else:
        print("⚠️ Unsupported content type")
        return 'Unsupported Media Type', 415

if __name__ == "__main__":
    print("🚀 Flask server starting...")
    app.run(host="0.0.0.0", port=5000)
