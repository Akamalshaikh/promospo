import os
import logging
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
WAITING_FOR_JOIN, MAIN_MENU = range(2)
DATA_FILE = 'user_data.json'
CHANNELS_FILE = 'channels.json'
SPOTIFY_CHANNEL_LINK = "https://t.me/+g-xrzWHWZcUzODA1"
ADMIN_ID = int(os.getenv("ADMIN_ID", "6994528708"))

# Emojis
FIRE_EMOJI = "🔥"
ROCKET_EMOJI = "🚀"
CHECK_EMOJI = "✅"
DIAMOND_EMOJI = "💎"
MONEY_EMOJI = "💰"
GIFT_EMOJI = "🎁"
STAR_EMOJI = "⭐"
POINT_EMOJI = "🔍"
CHART_EMOJI = "📊"
LINK_EMOJI = "🔗"
USER_EMOJI = "👤"
FOLDER_EMOJI = "📁"
BROADCAST_EMOJI = "📣"

# Initialize data storage
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {'users': {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r') as f:
            return json.load(f)
    return {'channels': [], 'folders': {}}

def save_channels(channels_data):
    with open(CHANNELS_FILE, 'w') as f:
        json.dump(channels_data, f, indent=4)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    data = load_data()
    
    # Initialize user data if not exists
    if user_id not in data['users']:
        data['users'][user_id] = {
            'username': user.username if user.username else f"user_{user_id}",
            'points': 0,
            'referrals': [],
            'has_withdrawn': False,
            'referred_by': None,
        }
        save_data(data)
        
    # Check if this user was referred by someone
    if context.args and context.args[0] != user_id:
        referrer_id = context.args[0]
        if referrer_id in data['users'] and user_id not in data['users'][referrer_id]['referrals']:
            # Update referral information
            data['users'][referrer_id]['referrals'].append(user_id)
            data['users'][user_id]['referred_by'] = referrer_id
            save_data(data)
            
            # Notify the referrer
            try:
                await context.bot.send_message(
                    chat_id=int(referrer_id),
                    text=f"{STAR_EMOJI} Great news! A new user has joined using your referral link!"
                )
                
                # Check if this referral completes the requirement (3 referrals)
                if len(data['users'][referrer_id]['referrals']) >= 3 and not data['users'][referrer_id]['has_withdrawn']:
                    await context.bot.send_message(
                        chat_id=int(referrer_id),
                        text=f"{GIFT_EMOJI} Congratulations! You've referred 3 friends successfully! You can now withdraw your reward."
                    )
            except Exception as e:
                logger.error(f"Failed to notify referrer: {e}")
    
    welcome_text = (
        f"{FIRE_EMOJI} *Welcome to Spotify Premium Bot* {FIRE_EMOJI}\n\n"
        f"Get FREE Spotify Premium by completing simple tasks!\n\n"
        f"{ROCKET_EMOJI} First, join all our required channels to continue."
    )
    
    # Create inline keyboard with join buttons for channels
    channels_data = load_channels()
    keyboard = []
    
    # Add channel buttons
    for channel in channels_data['channels']:
        keyboard.append([
            InlineKeyboardButton(f"{LINK_EMOJI} {channel['name']}", url=channel['link'])
        ])
    
    # Add folder buttons
    for folder_name, folder_channels in channels_data['folders'].items():
        keyboard.append([
            InlineKeyboardButton(f"{FOLDER_EMOJI} {folder_name}", url=folder_channels['link'])
        ])
    
    # Add "I've Joined" button
    keyboard.append([InlineKeyboardButton(f"{CHECK_EMOJI} I've Joined All Channels", callback_data="check_join")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    return WAITING_FOR_JOIN

async def check_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    channels_data = load_channels()
    not_joined = []
    
    # Check if user has joined all channels
    for channel in channels_data['channels']:
        channel_id = channel['id']
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_joined.append(channel['name'])
        except Exception as e:
            logger.error(f"Error checking membership for channel {channel_id}: {e}")
            not_joined.append(channel['name'])
    
    # If user hasn't joined all channels
    if not_joined:
        channels_text = "\n".join([f"- {channel}" for channel in not_joined])
        await query.message.reply_text(
            f"{POINT_EMOJI} You haven't joined all required channels yet!\n\n"
            f"Please join these channels:\n{channels_text}\n\n"
            f"Then click the 'I've Joined All Channels' button again."
        )
        return WAITING_FOR_JOIN
    
    # User has joined all channels, show instructions
    instruction_text = (
        f"{STAR_EMOJI} *How to Get Spotify Premium* {STAR_EMOJI}\n\n"
        f"{CHECK_EMOJI} You've successfully joined all required channels!\n\n"
        f"{DIAMOND_EMOJI} *Here's how to get your Spotify Premium:*\n\n"
        f"1️⃣ Refer 3 friends to this bot using your referral link\n"
        f"2️⃣ Once you have 3 referrals, click on 'Withdraw Reward'\n"
        f"3️⃣ You'll get access to our exclusive Spotify Premium method\n\n"
        f"{FIRE_EMOJI} Get started by clicking 'Refer Friends' below!"
    )
    
    # Create main menu keyboard
    keyboard = [
        [KeyboardButton(f"{CHART_EMOJI} My Points"), KeyboardButton(f"{LINK_EMOJI} Refer Friends")],
        [KeyboardButton(f"{MONEY_EMOJI} Withdraw Reward")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await query.message.reply_text(instruction_text, reply_markup=reply_markup, parse_mode='Markdown')
    return MAIN_MENU

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    user_id = str(update.effective_user.id)
    data = load_data()
    
    # Check if user exists in data
    if user_id not in data['users']:
        await update.message.reply_text(
            f"Please start the bot first by clicking /start"
        )
        return MAIN_MENU
    
    user_data = data['users'][user_id]
    
    # Handle "My Points" button
    if message_text == f"{CHART_EMOJI} My Points":
        referral_count = len(user_data['referrals'])
        remaining = max(0, 3 - referral_count)
        
        await update.message.reply_text(
            f"{CHART_EMOJI} *Your Referral Status* {CHART_EMOJI}\n\n"
            f"{USER_EMOJI} You have referred: {referral_count} users\n"
            f"{POINT_EMOJI} Remaining referrals needed: {remaining}\n\n"
            f"{STAR_EMOJI} Refer 3 friends to get Spotify Premium!"
        , parse_mode='Markdown')
    
    # Handle "Refer Friends" button
    elif message_text == f"{LINK_EMOJI} Refer Friends":
        bot = await context.bot.get_me()
        referral_link = f"https://t.me/{bot.username}?start={user_id}"
        
        await update.message.reply_text(
            f"{LINK_EMOJI} *Your Referral Link* {LINK_EMOJI}\n\n"
            f"`{referral_link}`\n\n"
            f"{ROCKET_EMOJI} Share this link with your friends!\n"
            f"{GIFT_EMOJI} When 3 friends join using your link, you'll get access to the Spotify Premium method!"
        , parse_mode='Markdown')
    
    # Handle "Withdraw Reward" button
    elif message_text == f"{MONEY_EMOJI} Withdraw Reward":
        referral_count = len(user_data['referrals'])
        
        if referral_count >= 3:
            if not user_data['has_withdrawn']:
                # Update user data to mark as withdrawn
                data['users'][user_id]['has_withdrawn'] = True
                save_data(data)
                
                await update.message.reply_text(
                    f"{GIFT_EMOJI} *Congratulations!* {GIFT_EMOJI}\n\n"
                    f"{CHECK_EMOJI} You've successfully completed the requirements!\n\n"
                    f"{DIAMOND_EMOJI} Access our exclusive Spotify Premium method here:\n"
                    f"{LINK_EMOJI} {SPOTIFY_CHANNEL_LINK}\n\n"
                    f"{STAR_EMOJI} Enjoy your Spotify Premium!"
                , parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    f"{CHECK_EMOJI} You've already withdrawn your reward!\n\n"
                    f"{LINK_EMOJI} Access our exclusive Spotify Premium method here:\n"
                    f"{SPOTIFY_CHANNEL_LINK}"
                )
        else:
            remaining = 3 - referral_count
            await update.message.reply_text(
                f"{POINT_EMOJI} You need to refer {remaining} more friends before you can withdraw your reward!\n\n"
                f"{LINK_EMOJI} Use the 'Refer Friends' button to get your referral link."
            )
    
    return MAIN_MENU

# Admin commands
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        data = load_data()
        if str(user_id) not in data.get('admins', []):
            await update.message.reply_text("You don't have permission to use admin commands.")
            return
    
    admin_keyboard = [
        [InlineKeyboardButton("Add Channel", callback_data="admin_add_channel"),
         InlineKeyboardButton("Delete Channel", callback_data="admin_delete_channel")],
        [InlineKeyboardButton("Add Folder", callback_data="admin_add_folder"),
         InlineKeyboardButton("Delete Folder", callback_data="admin_delete_folder")],
        [InlineKeyboardButton("Add Admin", callback_data="admin_add_admin"),
         InlineKeyboardButton("Broadcast", callback_data="admin_broadcast")]
    ]
    
    reply_markup = InlineKeyboardMarkup(admin_keyboard)
    await update.message.reply_text(
        f"{STAR_EMOJI} *Admin Panel* {STAR_EMOJI}\n\n"
        f"Select an action from below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Verify admin
    if user_id != ADMIN_ID:
        data = load_data()
        if str(user_id) not in data.get('admins', []):
            await query.message.reply_text("You don't have permission to use admin commands.")
            return
    
    action = query.data.split('_', 2)[1]
    
    if action == "add":
        subcmd = query.data.split('_', 2)[2]
        if subcmd == "channel":
            await query.message.reply_text(
                "Please enter the channel details in this format:\n"
                "name|link|channel_id\n\n"
                "Example: My Channel|https://t.me/mychannel|-1001234567890"
            )
            context.user_data['admin_action'] = 'add_channel'
        elif subcmd == "folder":
            await query.message.reply_text(
                "Please enter the folder details in this format:\n"
                "folder_name|folder_link\n\n"
                "Example: My Folder|https://t.me/addlist/abcde"
            )
            context.user_data['admin_action'] = 'add_folder'
        elif subcmd == "admin":
            await query.message.reply_text(
                "Please enter the user ID of the new admin:"
            )
            context.user_data['admin_action'] = 'add_admin'
    elif action == "delete":
        subcmd = query.data.split('_', 2)[2]
        if subcmd == "channel":
            channels_data = load_channels()
            if not channels_data['channels']:
                await query.message.reply_text("No channels found.")
                return
            
            channel_keyboard = []
            for i, channel in enumerate(channels_data['channels']):
                channel_keyboard.append([
                    InlineKeyboardButton(
                        channel['name'], 
                        callback_data=f"del_channel_{i}"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(channel_keyboard)
            await query.message.reply_text(
                "Select a channel to delete:",
                reply_markup=reply_markup
            )
        elif subcmd == "folder":
            channels_data = load_channels()
            if not channels_data['folders']:
                await query.message.reply_text("No folders found.")
                return
            
            folder_keyboard = []
            for folder_name in channels_data['folders']:
                folder_keyboard.append([
                    InlineKeyboardButton(
                        folder_name, 
                        callback_data=f"del_folder_{folder_name}"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(folder_keyboard)
            await query.message.reply_text(
                "Select a folder to delete:",
                reply_markup=reply_markup
            )
    elif action == "broadcast":
        await query.message.reply_text(
            "Please enter the message you want to broadcast to all users:"
        )
        context.user_data['admin_action'] = 'broadcast'

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'admin_action' not in context.user_data:
        return
    
    user_id = update.effective_user.id
    # Verify admin
    if user_id != ADMIN_ID:
        data = load_data()
        if str(user_id) not in data.get('admins', []):
            await update.message.reply_text("You don't have permission to use admin commands.")
            return
    
    action = context.user_data['admin_action']
    text = update.message.text
    
    if action == 'add_channel':
        try:
            name, link, channel_id = text.strip().split('|')
            
            channels_data = load_channels()
            channels_data['channels'].append({
                'name': name.strip(),
                'link': link.strip(),
                'id': channel_id.strip()
            })
            save_channels(channels_data)
            
            await update.message.reply_text(f"Channel '{name}' added successfully!")
        except ValueError:
            await update.message.reply_text(
                "Invalid format. Please use: name|link|channel_id"
            )
    
    elif action == 'add_folder':
        try:
            folder_name, folder_link = text.strip().split('|')
            
            channels_data = load_channels()
            channels_data['folders'][folder_name.strip()] = {
                'link': folder_link.strip()
            }
            save_channels(channels_data)
            
            await update.message.reply_text(f"Folder '{folder_name}' added successfully!")
        except ValueError:
            await update.message.reply_text(
                "Invalid format. Please use: folder_name|folder_link"
            )
    
    elif action == 'add_admin':
        try:
            new_admin_id = text.strip()
            
            data = load_data()
            if 'admins' not in data:
                data['admins'] = []
            
            if new_admin_id not in data['admins']:
                data['admins'].append(new_admin_id)
                save_data(data)
                await update.message.reply_text(f"Admin added successfully with ID: {new_admin_id}")
            else:
                await update.message.reply_text(f"This ID is already an admin.")
        except Exception as e:
            await update.message.reply_text(f"Error adding admin: {str(e)}")
    
    elif action == 'broadcast':
        data = load_data()
        broadcast_message = text
        success_count = 0
        fail_count = 0
        
        await update.message.reply_text("Broadcasting message to all users...")
        
        for user_id in data['users']:
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=f"{BROADCAST_EMOJI} *ANNOUNCEMENT* {BROADCAST_EMOJI}\n\n{broadcast_message}",
                    parse_mode='Markdown'
                )
                success_count += 1
            except Exception:
                fail_count += 1
        
        await update.message.reply_text(
            f"Broadcast completed!\n"
            f"✅ Successfully sent: {success_count}\n"
            f"❌ Failed: {fail_count}"
        )
    
    # Clear admin action
    context.user_data.pop('admin_action', None)

async def handle_channel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    # Verify admin
    if user_id != ADMIN_ID:
        data = load_data()
        if str(user_id) not in data.get('admins', []):
            await query.message.reply_text("You don't have permission to use admin commands.")
            return
    
    # Extract channel index
    _, entity_type, entity_id = query.data.split('_', 2)
    channels_data = load_channels()
    
    if entity_type == 'channel':
        index = int(entity_id)
        channel_name = channels_data['channels'][index]['name']
        del channels_data['channels'][index]
        save_channels(channels_data)
        await query.message.reply_text(f"Channel '{channel_name}' has been deleted.")
    
    elif entity_type == 'folder':
        folder_name = entity_id
        del channels_data['folders'][folder_name]
        save_channels(channels_data)
        await query.message.reply_text(f"Folder '{folder_name}' has been deleted.")

def main():
    # Set up application with the bot token
    token = os.getenv("BOT_TOKEN", "7440431620:AAHBjql-Cu73vsKC33ruNgy5TrVbrmCvHro")
    application = Application.builder().token(token).build()
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_JOIN: [
                CallbackQueryHandler(check_user_joined, pattern="^check_join$"),
            ],
            MAIN_MENU: [
                MessageHandler(
                    filters.Regex(f"^({CHART_EMOJI} My Points|{LINK_EMOJI} Refer Friends|{MONEY_EMOJI} Withdraw Reward)$"), 
                    handle_menu_selection
                ),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(handle_channel_delete, pattern="^del_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))
    
    # Start the Bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    # Create data files if they don't exist
    if not os.path.exists(DATA_FILE):
        save_data({'users': {}})
    
    if not os.path.exists(CHANNELS_FILE):
        save_channels({'channels': [], 'folders': {}})
        
    main()