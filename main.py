import os
import time
from telebot import TeleBot
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = TeleBot(TELEGRAM_BOT_TOKEN)

VALID_CODES = {
    '9Z1_XAU': True,
    '9Z1_GOLD': True,
}

user_sessions = {}

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    user_id = message.chat.id
    user_sessions[user_id] = {'step': 'waiting_for_code'}
    msg = bot.send_message(user_id, "Please enter your access code:")
    bot.register_next_step_handler(msg, validate_code)

def validate_code(message):
    user_id = message.chat.id
    code = message.text.strip()
    
    if code in VALID_CODES:
        user_sessions[user_id] = {'step': 'authenticated', 'code': code}
        bot.send_message(user_id, "Code valid! You can now link your MT5 account.")
    else:
        msg = bot.send_message(user_id, "Invalid code. Please try again:")
        bot.register_next_step_handler(msg, validate_code)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Hello! I'm a simple Telegram bot.")

try:
    print("Bot is running...")
    bot.infinity_polling()
except Exception as e:
    print(f"Error: {e}")
    bot.stop_polling()
