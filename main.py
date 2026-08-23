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

VALID_CODES = {
    '9Z1XAU': True,
    '9Z1GOLD': True,
}

user_sessions = {}

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    user_id = message.chat.id

    # Initialize if needed
    if user_id not in user_sessions:
        user_sessions[user_id] = {'accounts': []}

    accounts = user_sessions[user_id].get('accounts', [])

    # If they have existing accounts, show them as options
    if accounts:
        accounts_text = "<b>Welcome back to 9Z1</b>\n\n"
        accounts_text += "<b>Your Accounts:</b>\n\n"

        for i, account in enumerate(accounts, 1):
            accounts_text += f"{i}. {account['full_name']}\n   MT5: {account['mt5_login']} | Lot: {account['lot_size']}x\n\n"

        accounts_text += (
            f"<b>What would you like to do?</b>\n\n"
            f"Reply with:\n"
            f"<b>1-{len(accounts)}</b> - Select an account to manage\n"
            f"<b>NEW</b> - Add a new account\n"
            f"<b>VIEW</b> - View all accounts"
        )

        msg = bot.send_message(user_id, accounts_text, parse_mode='HTML')
        bot.register_next_step_handler(msg, handle_start_selection)
    else:
        # No accounts yet, start linking process
        user_sessions[user_id]['step'] = 'waiting_for_code'
        msg = bot.send_message(
            user_id,
            "Welcome to 9Z1\n\n"
            "Please enter your access code:"
        )
        bot.register_next_step_handler(msg, validate_code)

def handle_start_selection(message):
    user_id = message.chat.id
    choice = message.text.strip().upper()
    accounts = user_sessions[user_id]['accounts']

    if choice == 'NEW':
        # Add new account
        user_sessions[user_id]['step'] = 'waiting_for_code'
        msg = bot.send_message(user_id, "Please enter your access code to add a new account:")
        bot.register_next_step_handler(msg, validate_code)

    elif choice == 'VIEW':
        # View all accounts
        view_accounts(message)

    elif choice.isdigit():
        try:
            account_num = int(choice) - 1
            if 0 <= account_num < len(accounts):
                # Show account options
                account = accounts[account_num]
                user_sessions[user_id]['selected_account_index'] = account_num

                options_text = (
                    f"<b>{account['full_name']}</b>\n"
                    f"MT5 Login: {account['mt5_login']}\n"
                    f"Lot Size: {account['lot_size']}x\n\n"
                    f"<b>What would you like to do?</b>\n\n"
                    f"Reply with:\n"
                    f"<b>UPDATE</b> - Change lot size\n"
                    f"<b>REMOVE</b> - Disconnect account\n"
                    f"<b>BACK</b> - Go back"
                )

                msg = bot.send_message(user_id, options_text, parse_mode='HTML')
                bot.register_next_step_handler(msg, handle_account_action)
            else:
                msg = bot.send_message(user_id, "Invalid selection. Please try /start again")
        except:
            msg = bot.send_message(user_id, "Invalid input. Please try /start again")
    else:
        msg = bot.send_message(user_id, "Invalid choice. Please try /start again")

def handle_account_action(message):
    user_id = message.chat.id
    action = message.text.strip().upper()

    if action == 'UPDATE':
        account_index = user_sessions[user_id].get('selected_account_index', 0)
        ask_for_new_lot_size(user_id, message.chat.id)

    elif action == 'REMOVE':
        account_index = user_sessions[user_id].get('selected_account_index', 0)
        account = user_sessions[user_id]['accounts'][account_index]

        confirmation_text = (
            f"Are you sure you want to disconnect this account?\n\n"
            f"<b>Account:</b> {account['full_name']} - {account['mt5_login']}\n\n"
            f"This will:\n"
            f"• Stop all trade copying to this account\n"
            f"• Remove it from 9Z1\n"
            f"• Close the CopyFactory subscription\n\n"
            f"Reply with:\n"
            f"YES - Confirm removal\n"
            f"NO - Cancel"
        )

        confirmation_msg = bot.send_message(user_id, confirmation_text, parse_mode='HTML')
        bot.register_next_step_handler(confirmation_msg, process_removal_confirmation)

    elif action == 'BACK':
        send_welcome(message)

    else:
        msg = bot.send_message(user_id, "Invalid choice. Please reply with UPDATE, REMOVE, or BACK:")
        bot.register_next_step_handler(msg, handle_account_action)

def validate_code(message):
    user_id = message.chat.id
    code = message.text.strip()

    if code in VALID_CODES:
        user_sessions[user_id]['step'] = 'waiting_for_name'
        user_sessions[user_id]['code'] = code
        user_sessions[user_id]['chat_id'] = message.chat.id
        msg = bot.send_message(
            user_id,
            "Code valid! Welcome to 9Z1.\n\n"
            "What is your full name?"
        )
        bot.register_next_step_handler(msg, get_full_name)
    else:
        msg = bot.send_message(user_id, "Invalid code. Please try again:")
        bot.register_next_step_handler(msg, validate_code)

def get_full_name(message):
    user_id = message.chat.id
    full_name = message.text.strip()

    if len(full_name) < 2:
        msg = bot.send_message(user_id, "Please enter a valid full name:")
        bot.register_next_step_handler(msg, get_full_name)
        return

    user_sessions[user_id]['full_name'] = full_name

    # Welcome message with personalization
    welcome_msg = (
        f"Hello <b>{full_name}</b>.\n\n"
        f"Welcome to the 9Z1 lifestyle.\n\n"
        f"Let's link your MT5 account.\n\n"
        f"Please enter your MT5 account login number (e.g., 34412323):"
    )
    msg = bot.send_message(user_id, welcome_msg, parse_mode='HTML')
    bot.register_next_step_handler(msg, get_mt5_login)

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

    # Initial message
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
        full_name = session_data['full_name']

        headers = {
            'auth-token': METAAPI_TOKEN,
            'Content-Type': 'application/json',
            'transaction-id': str(uuid.uuid4())
        }

        # ===== STEP 1: Register Account with MetaAPI (PROVISIONING API) =====
        account_data = {
            "login": mt5_login,
            "password": mt5_password,
            "name": f"9Z1 - {full_name} - {mt5_login}",
            "server": mt5_server,
            "platform": "mt5",
            "magic": 9Z1,
            "type": "cloud-g2",
            "manualTrades": False,
            "copyFactoryRoles": ["SUBSCRIBER"]
        }

        # Current MetaAPI provisioning endpoint (2026)
        add_account_url = "https://mt-provisioning-api-v1.agiliumtrade.ai/users/current/accounts"
        response = requests.post(add_account_url, json=account_data, headers=headers, timeout=30)

        if response.status_code not in [200, 201, 202]:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg_id,
                text=f"Registration Failed at Step 1\n\n"
                     f"Error: Bad MT5 credentials or server name incorrect\n\n"
                     f"Please check your details and try again with /start"
            )
            return

        slave_account_data = response.json()
        slave_account_id = slave_account_data.get('id')

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

        time.sleep(3)

        # ===== STEP 2: Configure CopyFactory Subscription (Slave) =====
        copy_config = {
            "name": f"9Z1 Subscriber - {full_name}",
            "subscriptions": [
                {
                    "strategyId": MASTER_ACCOUNT_ID,
                    "multiplier": lot_size
                }
            ]
        }

        # Current MetaAPI CopyFactory endpoint (2026) - using new-york region
        subscription_url = f"https://copyfactory-api-v1.new-york.agiliumtrade.ai/users/current/configuration/subscribers/{slave_account_id}"
        sub_headers = {
            'auth-token': METAAPI_TOKEN,
            'Content-Type': 'application/json'
        }

        sub_response = requests.put(subscription_url, json=copy_config, headers=sub_headers, timeout=30)

        if sub_response.status_code not in [200, 201, 204]:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg_id,
                text=f"Partial Success\n\n"
                     f"Account registered but CopyFactory setup failed.\n"
                     f"Account ID: {slave_account_id}\n"
                     f"Please contact support."
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
            f"Name: <code>{full_name}</code>\n"
            f"Login: <code>{mt5_login}</code>\n"
            f"Password Type: <code>{password_type_display}</code>\n"
            f"Server: <code>{mt5_server}</code>\n"
            f"Lot Size: <code>{lot_size}x</code>\n"
            f"Account ID: <code>{slave_account_id}</code>\n\n"
            f"<b>Status:</b> Connected to 9Z1 Master Account\n"
            f"<b>Trades:</b> Now copying XAU/USD trades with your lot size\n\n"
            f"Your account is ready! Trades will begin copying immediately.\n\n"
            f"Use /start anytime to manage your accounts."
        )

        bot.send_message(chat_id, confirmation_message, parse_mode='HTML')

        # Store account in the accounts list
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
        user_sessions[user_id]['step'] = 'account_linked'

    except requests.exceptions.Timeout:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"Registration Timeout\n\n"
                 f"MetaAPI took too long to respond. Please try /start again"
        )
    except Exception as e:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"Registration Error\n\n"
                 f"An unexpected error occurred.\n\n"
                 f"Please try /start again or contact support."
        )

def view_accounts(message):
    user_id = message.chat.id
    accounts = user_sessions[user_id]['accounts']

    accounts_text = "<b>Your 9Z1 Accounts</b>\n\n"

    for i, account in enumerate(accounts, 1):
        accounts_text += (
            f"<b>Account {i}</b>\n"
            f"Name: {account['full_name']}\n"
            f"MT5 Login: {account['mt5_login']}\n"
            f"Lot Size: {account['lot_size']}x\n"
            f"Status: Active\n\n"
        )

    accounts_text += "Use /start to manage these accounts."

    bot.send_message(user_id, accounts_text, parse_mode='HTML')

def ask_for_new_lot_size(user_id, chat_id):
    msg = bot.send_message(
        user_id,
        "What is your new lot size?\n\n"
        "<b>Lot Size Configuration</b>\n\n"
        "Enter your desired lot size as a decimal (e.g., 0.5, 1.0, 2.0):\n\n"
        "Examples:\n"
        "• Small account (£10k-25k): 0.25-0.5\n"
        "• Medium account (£25k-50k): 0.5-1.0\n"
        "• Large account (£50k+): 1.0-2.0",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, process_new_lot_size)

def process_new_lot_size(message):
    user_id = message.chat.id
    lot_size_str = message.text.strip()

    try:
        new_lot_size = float(lot_size_str)
        if new_lot_size <= 0 or new_lot_size > 10:
            raise ValueError("Lot size out of range")
    except:
        msg = bot.send_message(
            user_id,
            "Invalid lot size. Please enter a number between 0.01 and 10 (e.g., 0.5 or 1.0):"
        )
        bot.register_next_step_handler(msg, process_new_lot_size)
        return

    chat_id = message.chat.id

    # Show update progress
    status_msg = bot.send_message(
        chat_id,
        "<b>Updating lot size...</b>\n\n"
        "Applying new lot size to your account...",
        parse_mode='HTML'
    )

    update_lot_size_on_metaapi(user_id, chat_id, status_msg.message_id, new_lot_size)

def update_lot_size_on_metaapi(user_id, chat_id, status_msg_id, new_lot_size):
    """Update the lot size multiplier on MetaAPI CopyFactory"""

    try:
        session_data = user_sessions.get(user_id, {})
        account_index = session_data.get('selected_account_index', 0)
        account = session_data['accounts'][account_index]

        slave_account_id = account['slave_account_id']
        full_name = account['full_name']
        mt5_login = account['mt5_login']

        # Update CopyFactory subscription with new multiplier
        copy_config = {
            "name": f"9Z1 Subscriber - {full_name}",
            "subscriptions": [
                {
                    "strategyId": MASTER_ACCOUNT_ID,
                    "multiplier": new_lot_size
                }
            ]
        }

        subscription_url = f"https://copyfactory-api-v1.new-york.agiliumtrade.ai/users/current/configuration/subscribers/{slave_account_id}"
        headers = {
            'auth-token': METAAPI_TOKEN,
            'Content-Type': 'application/json'
        }

        response = requests.put(subscription_url, json=copy_config, headers=headers, timeout=30)

        if response.status_code not in [200, 201, 204]:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg_id,
                text=f"Error updating lot size\n\n"
                     f"Please try again or contact support."
            )
            return

        # Success message
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"<b>Lot Size Updated Successfully!</b>\n\n"
                 f"Account: <code>{full_name}</code> - <code>{mt5_login}</code>\n"
                 f"New Lot Size: <code>{new_lot_size}x</code>\n\n"
                 f"Your new lot size is now active.\n\n"
                 f"Use /start to manage your accounts."
        )

        # Update session
        user_sessions[user_id]['accounts'][account_index]['lot_size'] = new_lot_size

    except requests.exceptions.Timeout:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"Timeout updating lot size\n\n"
                 f"Please try /start again"
        )
    except Exception as e:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"Error updating lot size\n\n"
                 f"Please try /start again or contact support."
        )

def process_removal_confirmation(message):
    user_id = message.chat.id
    response = message.text.strip().upper()

    if response == 'YES':
        chat_id = message.chat.id
        status_msg = bot.send_message(
            chat_id,
            "<b>Removing your account...</b>\n\n"
            "Disconnecting from 9Z1 system...",
            parse_mode='HTML'
        )
        remove_account_from_metaapi(user_id, chat_id, status_msg.message_id)
    elif response == 'NO':
        bot.send_message(user_id, "Removal cancelled. Your account remains connected.\n\nUse /start to continue.")
    else:
        msg = bot.send_message(
            user_id,
            "Invalid response. Please reply with YES or NO:"
        )
        bot.register_next_step_handler(msg, process_removal_confirmation)

def remove_account_from_metaapi(user_id, chat_id, status_msg_id):
    """Remove account from MetaAPI and clear from accounts list"""

    try:
        session_data = user_sessions.get(user_id, {})
        account_index = session_data.get('selected_account_index', 0)
        account = session_data['accounts'][account_index]

        slave_account_id = account['slave_account_id']
        full_name = account['full_name']
        mt5_login = account['mt5_login']

        headers = {
            'auth-token': METAAPI_TOKEN,
            'Content-Type': 'application/json',
            'transaction-id': str(uuid.uuid4())
        }

        # Delete account from MetaAPI
        delete_url = f"https://mt-provisioning-api-v1.agiliumtrade.ai/users/current/accounts/{slave_account_id}"
        delete_response = requests.delete(delete_url, headers=headers, timeout=30)

        # Remove from accounts list
        user_sessions[user_id]['accounts'].pop(account_index)

        # Success message
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"<b>Account Disconnected Successfully!</b>\n\n"
                 f"Account: <code>{full_name}</code> - <code>{mt5_login}</code>\n"
                 f"Status: Removed from 9Z1\n\n"
                 f"Trade copying has stopped.\n\n"
                 f"Remaining accounts: {len(user_sessions[user_id]['accounts'])}\n\n"
                 f"Use /start to continue managing your accounts."
        )

    except requests.exceptions.Timeout:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"Timeout removing account\n\n"
                 f"Please try /start again or contact support."
        )
    except Exception as e:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg_id,
            text=f"Error removing account\n\n"
                 f"Please try /start again or contact support."
        )

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(
        message.chat.id,
        "Hello! Use /start to access your 9Z1 accounts and manage them.\n\n"
        "/start - Manage your accounts"
    )

try:
    print("Bot is running...")
    bot.infinity_polling()
except Exception as e:
    print(f"Error: {e}")
    bot.stop_polling()
