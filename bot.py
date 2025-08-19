from flask import Flask, request
import telebot

TOKEN = "8394102086:AAHnV5Fg8DUS4rz2rzrXD3zVHuBIQ3ri4II"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Webhook endpoint (cleaner URL: /webhook)
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# Root route (for testing)
@app.route('/')
def index():
    return "Bot is running!", 200
