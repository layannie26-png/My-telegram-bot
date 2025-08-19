import telebot
from flask import Flask, request

TOKEN = "8394102086:AAHnV5Fg8DUS4rz2rzrXD3zVHuBIQ3ri4II"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Test Handlers ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "✅ Bot is alive on Render!")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    bot.reply_to(message, f"You said: {message.text}")

# --- Flask Webhook Route ---
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Unsupported Media Type', 415

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
