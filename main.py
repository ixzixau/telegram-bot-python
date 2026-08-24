import os
import time
import requests
import uuid
from telebot import TeleBot
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
METAAPI_TOKEN = os.getenv('METAAPI_TOKEN')
MASTER_ACCOUNT_ID = "45f41e44-44ff-47e0-ab4b-4780605a0c39"

bot = TeleBot(TELEGRAM_BOT_TOKEN)

VALID_CODES = {'9Z1XAU': True, '9Z1GOLD': True}
user_sessions = {}

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    user_id = message.chat.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {'accounts': []}

    accounts = user_sessions[user_id].get('accounts', [])

    if accounts:
        accounts_text = "Welcome back to 9Z1\n\nYour Accounts:\n\n"
        for i, account in enumerate(accounts, 1):
            accounts_text += f"{i}. {account['full_name']}\n   MT5: {account['mt5_login']} | Lot: {account['lot_size']}x\n\n"
        accounts_text += f"Reply with:\n1-{len(accounts)} - Select account\nNEW - Add account\nVIEW - View all"
        msg = bot.send_message(user_id, accounts_text)
        bot.register_next_step_handler(msg, handle_start_selection)
    else:
        msg = bot.send_message(user_id, "Welcome to 9Z1\n\nPlease enter your access code:")
        bot.register_next_step_handler(msg, validate_code)

def handle_start_selection(message):
    user_id = message.chat.id
    choice = message.text.strip().upper()
    accounts = user_sessions[user_id]['accounts']

    if choice == 'NEW':
        msg = bot.send_message(user_id, "Please enter your access code:")
        bot.register_next_step_handler(msg, validate_code)
    elif choice == 'VIEW':
        view_accounts(message)
    elif choice.isdigit():
        try:
            account_num = int(choice) - 1
            if 0 <= account_num < len(accounts):
                account = accounts[account_num]
                user_sessions[user_id]['selected_account_index'] = account_num
                msg = bot.send_message(user_id, f"{account['full_name']}\nMT5: {account['mt5_login']}\nLot: {account['lot_size']}x\n\nReply: UPDATE, REMOVE, or BACK")
                bot.register_next_step_handler(msg, handle_account_action)
        except:
            pass

def handle_account_action(message):
    user_id = message.chat.id
    action = message.text.strip().upper()
    if action == 'BACK':
        send_welcome(message)
    elif action == 'UPDATE':
        ask_for_new_lot_size(user_id)
    elif action == 'REMOVE':
        remove_account_from_metaapi(user_id, message.chat.id)

def validate_code(message):
    user_id = message.chat.id
    code = message.text.strip()

    if code in VALID_CODES:
        user_sessions[user_id]['code'] = code
        user_sessions[user_id]['chat_id'] = message.chat.id
        msg = bot.send_message(user_id, "Code valid! What is your full name?")
        bot.register_next_step_handler(msg, get_full_name)
    else:
        msg = bot.send_message(user_id, "Invalid code. Try again:")
        bot.register_next_step_handler(msg, validate_code)

def get_full_name(message):
    user_id = message.chat.id
    full_name = message.text.strip()

    if len(full_name) < 2:
        msg = bot.send_message(user_id, "Please enter a valid full name:")
        bot.register_next_step_handler(msg, get_full_name)
        return

    user_sessions[user_id]['full_name'] = full_name
    msg = bot.send_message(user_id, f"Hello {full_name}.\n\nWelcome to the 9Z1 lifestyle.\n\nEnter MT5 login (e.g., 34412323):")
    bot.register_next_step_handler(msg, get_mt5_login)

def get_mt5_login(message):
    user_id = message.chat.id
    login = message.text.strip()

    if not login.isdigit():
        msg = bot.send_message(user_id, "Invalid login. Numbers only:")
        bot.register_next_step_handler(msg, get_mt5_login)
        return

    user_sessions[user_id]['mt5_login'] = login
    msg = bot.send_message(user_id, "Password type?\n1 - Investor (read-only)\n2 - Terminal (full access)\n\nReply: 1 or 2")
    bot.register_next_step_handler(msg, get_password_type)

def get_password_type(message):
    user_id = message.chat.id
    password_type = message.text.strip()

    if password_type == '1':
        user_sessions[user_id]['mt5_password_type'] = 'investor'
        msg = bot.send_message(user_id, "Enter investor password:")
        bot.register_next_step_handler(msg, get_mt5_password)
    elif password_type == '2':
        user_sessions[user_id]['mt5_password_type'] = 'terminal'
        msg = bot.send_message(user_id, "Enter terminal password:")
        bot.register_next_step_handler(msg, get_mt5_password)
    else:
        msg = bot.send_message(user_id, "Invalid. Reply 1 or 2:")
        bot.register_next_step_handler(msg, get_password_type)

def get_mt5_password(message):
    user_id = message.chat.id
    password = message.text.strip()

    if len(password) < 4:
        msg = bot.send_message(user_id, "Password too short:")
        bot.register_next_step_handler(msg, get_mt5_password)
        return

    user_sessions[user_id]['mt5_password'] = password
    msg = bot.send_message(user_id, "Enter MT5 server (e.g., VantageMarkets-Live 14):")
    bot.register_next_step_handler(msg, get_mt5_server)

def get_mt5_server(message):
    user_id = message.chat.id
    server = message.text.strip()

    if len(server) < 3:
        msg = bot.send_message(user_id, "Invalid server. Try again:")
        bot.register_next_step_handler(msg, get_mt5_server)
        return

    user_sessions[user_id]['mt5_server'] = server
    msg = bot.send_message(user_id, "Lot size? (0.01-10, e.g., 0.5):")
    bot.register_next_step_handler(msg, get_lot_size)

def get_lot_size(message):
    user_id = message.chat.id
    lot_size_str = message.text.strip()

    try:
        lot_size = float(lot_size_str)
        if lot_size <= 0 or lot_size > 10:
            raise ValueError()
    except:
        msg = bot.send_message(user_id, "Invalid lot size (0.01-10):")
        bot.register_next_step_handler(msg, get_lot_size)
        return

    user_sessions[user_id]['lot_size'] = lot_size
    chat_id = user_sessions[user_id]['chat_id']

    status_msg = bot.send_message(chat_id, "Registering account...\nStep 1/3: Connecting to MetaAPI...")
    register_account_with_metaapi(user_id, chat_id, status_msg.message_id)

def register_account_with_metaapi(user_id, chat_id, status_msg_id):
    try:
        if not METAAPI_TOKEN:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text="Error: No MetaAPI token")
            return

        session_data = user_sessions.get(user_id, {})
        mt5_login = session_data['mt5_login']
        mt5_password = session_data['mt5_password']
        mt5_password_type = session_data['mt5_password_type']
        mt5_server = session_data['mt5_server']
        lot_size = session_data['lot_size']
        full_name = session_data['full_name']

        headers = {
            'auth-token': METAAPI_TOKEN,
            'Content-Type': 'application/json',
            'transaction-id': str(uuid.uuid4())
        }

        account_data = {
            "login": mt5_login,
            "password": mt5_password,
            "name": f"9Z1 - {full_name} - {mt5_login}",
            "server": mt5_server,
            "platform": "mt5",
            "magic": 123456,
            "type": "cloud-g2",
            "manualTrades": False,
            "copyFactoryRoles": ["SUBSCRIBER"]
        }

        add_account_url = "https://mt-provisioning-api-v1.agiliumtrade.ai/users/current/accounts"

        response = requests.post(add_account_url, json=account_data, headers=headers, timeout=30, verify=False)

        if response.status_code not in [200, 201, 202]:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=f"Step 1 Failed\nStatus: {response.status_code}\nError: {response.text[:100]}")
            return

        slave_account_data = response.json()
        slave_account_id = slave_account_data.get('id')

        if not slave_account_id:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text="No account ID returned")
            return

        bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=f"Step 1 OK\nStep 2/3: Configuring CopyFactory...")
        time.sleep(2)

        copy_config = {
            "name": f"9Z1 Subscriber - {full_name}",
            "subscriptions": [{"strategyId": MASTER_ACCOUNT_ID, "multiplier": lot_size}]
        }

        subscription_url = f"https://copyfactory-api-v1.new-york.agiliumtrade.ai/users/current/configuration/subscribers/{slave_account_id}"
        sub_headers = {'auth-token': METAAPI_TOKEN, 'Content-Type': 'application/json'}

        sub_response = requests.put(subscription_url, json=copy_config, headers=sub_headers, timeout=30, verify=False)

        if sub_response.status_code not in [200, 201, 204]:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=f"Step 2 Failed\nStatus: {sub_response.status_code}")
            return

        bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text="Steps 1-3 Complete\n\nSUCCESS!")
        time.sleep(1)

        confirmation_message = f"Account Linked!\n\nName: {full_name}\nMT5: {mt5_login}\nServer: {mt5_server}\nLot: {lot_size}x\nID: {slave_account_id}\n\nTrades copying now!\n\nUse /start anytime."

        bot.send_message(chat_id, confirmation_message)

        new_account = {
            'full_name': full_name,
            'mt5_login': mt5_login,
            'mt5_password': mt5_password,
            'password_type': mt5_password_type,
            'server': mt5_server,
            'lot_size': lot_size,
            'slave_account_id': slave_account_id
        }

        user_sessions[user_id]['accounts'].append(new_account)

    except Exception as e:
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=f"Error: {str(e)[:100]}")

def ask_for_new_lot_size(user_id):
    msg = bot.send_message(user_id, "New lot size (0.01-10)?")
    bot.register_next_step_handler(msg, process_new_lot_size)

def process_new_lot_size(message):
    user_id = message.chat.id
    lot_size_str = message.text.strip()

    try:
        new_lot_size = float(lot_size_str)
        if new_lot_size <= 0 or new_lot_size > 10:
            raise ValueError()
    except:
        msg = bot.send_message(user_id, "Invalid lot size:")
        bot.register_next_step_handler(msg, process_new_lot_size)
        return

    bot.send_message(user_id, f"Lot size updated to {new_lot_size}x")

def remove_account_from_metaapi(user_id, chat_id):
    bot.send_message(user_id, "Account removed")

def view_accounts(message):
    user_id = message.chat.id
    accounts = user_sessions[user_id]['accounts']

    accounts_text = "Your Accounts:\n\n"
    for i, account in enumerate(accounts, 1):
        accounts_text += f"{i}. {account['full_name']} - {account['mt5_login']} ({account['lot_size']}x)\n"

    accounts_text += "\nUse /start to manage"
    bot.send_message(user_id, accounts_text)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, "Use /start to access 9Z1")

print("Bot is running...")
bot.infinity_polling()
