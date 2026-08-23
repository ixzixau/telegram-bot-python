import os
import time
import requests
from telebot import TeleBot
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
METAAPI_TOKEN = os.getenv('METAAPI_TOKEN')
MASTER_ACCOUNT_ID = "45f41e44-44ff-47e0-ab4b-4780605a0c39"

bot = TeleBot(TELEGRAM_BOT_TOKEN)

VALID_CODES = {
    '9Z1XAU': True,
    '9Z1GOLD': True,
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
        user_sessions[user_id] = {
            'step': 'authenticated',
            'code': code,
            'mt5_login': None,
            'mt5_password': None,
            'mt5_password_type': None,
            'mt5_server': None,
            'lot_size': None,
            'chat_id': message.chat.id
        }
        msg = bot.send_message(
            user_id,
            "Code valid! Let's link your MT5 account.\n\n"
            "Please enter your MT5 account login number (e.g., 34412323):"
        )
        bot.register_next_step_handler(msg, get_mt5_login)
    else:
        msg = bot.send_message(user_id, "Invalid code. Please try again:")
        bot.register_next_step_handler(msg, validate_code)

def get_mt5_login(message):
    user_id = message.chat.id
    login = message.text.strip()

    if not login.isdigit():
        msg = bot.send_message(user_id, "Invalid login format. Please enter only numbers:")
        bot.register_next_step_handler(msg, get_mt5_login)
        return

    user_sessions[user_id]['mt5_login'] = login
    msg = bot.send_message(
        user_id,
        "Thank you. Which MT5 password do you have?\n\n"
        "Reply with:\n"
        "1 - Investor Password (read-only, recommended for security)\n"
        "2 - Terminal Password (full access)\n\n"
        "Type 1 or 2:"
    )
    bot.register_next_step_handler(msg, get_password_type)

def get_password_type(message):
    user_id = message.chat.id
    password_type = message.text.strip()

    if password_type == '1':
        user_sessions[user_id]['mt5_password_type'] = 'investor'
        msg = bot.send_message(
            user_id,
            "Great! Please enter your MT5 investor (read-only) password:"
        )
        bot.register_next_step_handler(msg, get_mt5_password)
    elif password_type == '2':
        user_sessions[user_id]['mt5_password_type'] = 'terminal'
        msg = bot.send_message(
            user_id,
            "Great! Please enter your MT5 terminal password:"
        )
        bot.register_next_step_handler(msg, get_mt5_password)
    else:
        msg = bot.send_message(
            user_id,
            "Invalid choice. Please reply with 1 or 2:\n"
            "1 - Investor Password\n"
            "2 - Terminal Password"
        )
        bot.register_next_step_handler(msg, get_password_type)

def get_mt5_password(message):
    user_id = message.chat.id
    password = message.text.strip()

    if len(password) < 4:
        msg = bot.send_message(user_id, "Password too short. Please enter your password:")
        bot.register_next_step_handler(msg, get_mt5_password)
        return

    user_sessions[user_id]['mt5_password'] = password
    msg = bot.send_message(
        user_id,
        "Great. Now enter your MT5 server name (e.g., VantageMarkets-Live 14):"
    )
    bot.register_next_step_handler(msg, get_mt5_server)

def get_mt5_server(message):
    user_id = message.chat.id
    server = message.text.strip()

    if len(server) < 3:
        msg = bot.send_message(user_id, "Invalid server name. Please try again:")
        bot.register_next_step_handler(msg, get_mt5_server)
        return

    user_sessions[user_id]['mt5_server'] = server
    msg = bot.send_message(
        user_id,
        "Perfect! Now for the most important part:\n\n"
        "<b>Lot Size Configuration</b>\n\n"
        "Your account capital and lot size must match your risk profile. "
        "Enter your desired lot size as a decimal (e.g., 0.5, 1.0, 2.0):\n\n"
        "Examples:\n"
        "• Small account (£10k-25k): 0.25-0.5\n"
        "• Medium account (£25k-50k): 0.5-1.0\n"
        "• Large account (£50k+): 1.0-2.0\n\n"
        "What lot size would you like?",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, get_lot_size)

def get_lot_size(message):
    user_id = message.chat.id
    lot_size_str = message.text.strip()

    try:
        lot_size = float(lot_size_str)
        if lot_size <= 0 or lot_size > 10:
            raise ValueError("Lot size out of range")
    except:
        msg = bot.send_message(
            user_id,
            "Invalid lot size. Please enter a number between 0.01 and 10 (e.g., 0.5 or 1.0):"
        )
        bot.register_next_step_handler(msg, get_lot_size)
        return

    user_sessions[user_id]['lot_size'] = lot_size

    # Start the registration process with step-by-step updates
    chat_id = user_sessions[user_id]['chat_id']

    # Initial message - NO EMOJIS in HTML mode
    status_msg = bot.send_message(
        chat_id,
        "<b>Starting account registration...</b>\n\n"
        "Step 1/3: Registering your MT5 account with MetaAPI...",
        parse_mode='HTML'
    )

    register_account_with_metaapi(user_id, chat_id, status_msg.message_id)

def register_account_with_metaapi(user_id, chat_id, status_msg_id):
    """Register MT5 account with MetaAPI and set up CopyFactory - with live updates"""

    try:
        session_data = user_sessions.get(user_id, {})
        mt5_login = session_data['mt5_login']
        mt5_password = session_data['mt5_password']
        mt5_password_type = session_data['mt5_password_type']
        mt5_server = session_data['mt5_server']
        lot_size = session_data['lot_size']

        headers = {
            'Authorization': f'Bearer {METAAPI_TOKEN}',
            'Content-Type': 'application/json'
        }

        # ===== STEP 1: Register Account with MetaAPI =====
        account_data = {
            "login": mt5_login,
            "password": mt5_password,
            "server": mt5_server,
            "type": "cloud",
            "manualTrades": False
        }

        add_account_url = "https://mt-provisioning-api-v1.herokuapp.com/accounts"
        response = requests.post(add_account_url, json=account_data, headers=headers, timeout=10)

        if response.status_code not in [200, 201]:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg_id,
                text=f"<b>Registration Failed at Step 1</b>\n\n"
                     f"Error: {response.text}\n\n"
                     f"Please check your MT5 credentials and try again with /start",
                parse_mode='HTML'
            )
            return

        slave_account_data = response.json()
        slave_account_id = slave_account_data.get('_id')

        # Update status message - Step 1 complete
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"<b>Starting account registration...</b>\n\n"
                 f"✓ Step 1/3: Account registered with MetaAPI\n"
                 f"Account ID: <code>{slave_account_id}</code>\n\n"
                 f"Step 2/3: Connecting to master account (CopyFactory)...",
            parse_mode='HTML'
        )

        time.sleep(2)

        # ===== STEP 2: Configure CopyFactory Subscription (Slave) =====
        copy_config = {
            "subscriberAccount": slave_account_id,
            "providerAccount": MASTER_ACCOUNT_ID,
            "multiplier": lot_size,
            "copyPendingOrders": True,
            "copyPositionCloseOrders": True,
            "copyCommissions": False
        }

        subscription_url = f"https://copy-trading-api-v1.herokuapp.com/accounts/{slave_account_id}/subscriber"
        sub_response = requests.post(subscription_url, json=copy_config, headers=headers, timeout=10)

        if sub_response.status_code not in [200, 201]:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg_id,
                text=f"<b>Partial Success</b>\n\n"
                     f"Account registered but CopyFactory setup failed.\n"
                     f"Account ID: {slave_account_id}\n"
                     f"Please contact support.",
                parse_mode='HTML'
            )
            return

        # Update status message - Step 2 complete
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"<b>Starting account registration...</b>\n\n"
                 f"✓ Step 1/3: Account registered with MetaAPI\n"
                 f"✓ Step 2/3: Connected to 9Z1 Master Account\n\n"
                 f"Step 3/3: Applying lot size multiplier...",
            parse_mode='HTML'
        )

        time.sleep(1)

        # ===== STEP 3: Apply Lot Size Multiplier =====
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"✓ Step 1/3: Account registered with MetaAPI\n"
                 f"✓ Step 2/3: Connected to 9Z1 Master Account\n"
                 f"✓ Step 3/3: Lot size multiplier applied\n\n"
                 f"Lot Size: {lot_size}x",
            parse_mode='HTML'
        )

        time.sleep(1)

        # ===== FINAL CONFIRMATION =====
        password_type_display = "Investor (Read-Only)" if mt5_password_type == 'investor' else "Terminal (Full Access)"

        confirmation_message = (
            f"<b>SUCCESS! Your MT5 account is now live!</b>\n\n"
            f"<b>Account Details:</b>\n"
            f"Login: <code>{mt5_login}</code>\n"
            f"Password Type: <code>{password_type_display}</code>\n"
            f"Server: <code>{mt5_server}</code>\n"
            f"Lot Size: <code>{lot_size}x</code>\n"
            f"Account ID: <code>{slave_account_id}</code>\n\n"
            f"<b>Status:</b> Connected to 9Z1 Master Account\n"
            f"<b>Trades:</b> Now copying XAU/USD trades with your lot size\n\n"
            f"Your account is ready! Trades will begin copying immediately when the master account executes them."
        )

        bot.send_message(chat_id, confirmation_message, parse_mode='HTML')

        # Update session
        user_sessions[user_id]['step'] = 'account_linked'
        user_sessions[user_id]['slave_account_id'] = slave_account_id

    except requests.exceptions.Timeout:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"<b>Registration Timeout</b>\n\n"
                 f"MetaAPI took too long to respond. Please try again with /start",
            parse_mode='HTML'
        )
    except Exception as e:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"<b>Registration Error</b>\n\n"
                 f"Error: {str(e)}\n\n"
                 f"Please try again with /start or contact support.",
            parse_mode='HTML'
        )

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Hello! Use /start to link your MT5 account to 9Z1.")

try:
    print("Bot is running...")
    bot.infinity_polling()
except Exception as e:
    print(f"Error: {e}")
    bot.stop_polling()
