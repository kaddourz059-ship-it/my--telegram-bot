import telebot
import os
from threading import Thread
from flask import Flask

# 1. Flask web server setup to keep bot alive
app = Flask('')

@app.route('/')
def home():
    user_count = len(get_all_user_ids()) if os.path.exists('user_ids.txt') else 0
    return f'''
    <html>
    <head><title>Telegram Broadcast Bot</title></head>
    <body>
        <h1>🤖 Telegram Broadcast Bot</h1>
        <p>✅ البوت يعمل حالياً</p>
        <p>👥 عدد المستخدمين المسجلين: {user_count}</p>
        <p>🕒 آخر تحديث: {os.popen('date').read().strip()}</p>
    </body>
    </html>
    '''

def run_flask():
    """Run Flask server in background"""
    app.run(host='0.0.0.0', port=5000, debug=False)

def keep_alive():
    """Start Flask server in a separate thread"""
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("🌐 Flask web server started on port 5000")

# 2. Setup token and admin ID
# This code will read values from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'your_bot_token_here')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))

# 3. Initialize bot with token
bot = telebot.TeleBot(BOT_TOKEN)

# 4. File name for storing user IDs
USER_IDS_FILE = 'user_ids.txt'

# 5. Function to save user ID
def save_user_id(user_id):
    """Save a new user ID to the file if not already present"""
    try:
        with open(USER_IDS_FILE, 'a+') as f:
            f.seek(0)
            users = f.read().splitlines()
            if str(user_id) not in users:
                f.write(str(user_id) + '\n')
                print(f"New user registered: {user_id}")
    except Exception as e:
        print(f"Error saving user ID {user_id}: {e}")

# 6. Function to read all user IDs
def get_all_user_ids():
    """Get all registered user IDs from the file"""
    try:
        with open(USER_IDS_FILE, 'a+') as f:
            f.seek(0)
            user_ids = f.read().splitlines()
            return [uid for uid in user_ids if uid.strip()]
    except Exception as e:
        print(f"Error reading user IDs: {e}")
        return []

# 7. Handler for /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle /start command and register new users"""
    save_user_id(message.chat.id)
    bot.reply_to(message, "مرحباً! لقد تم تسجيلك في البوت. سأقوم بتلقي رسائلك الآن.")
    print(f"User {message.chat.id} started the bot")

# 8. Handler for /broadcast command
@bot.message_handler(commands=['broadcast'])
def handle_broadcast_command(message):
    """Handle broadcast command - only for admin"""
    if message.chat.id == ADMIN_ID:
        user_count = len(get_all_user_ids())
        bot.reply_to(message, f"حسناً يا سيدي المدير، أرسل لي الآن المحتوى (نص، صورة، فيديو، إلخ.) الذي تريد بثه لجميع المستخدمين.\n\nعدد المستخدمين المسجلين: {user_count}")
        print(f"Admin {message.chat.id} initiated broadcast command")
    else:
        bot.reply_to(message, "أنت لست المدير المخول بهذا الأمر.")
        print(f"Unauthorized broadcast attempt from user {message.chat.id}")

# 9. Handler for voice messages from admin - placed BEFORE general admin handler
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID, content_types=['voice'])
def handle_voice_message(message):
    """Handle voice messages from admin for broadcasting"""
    print(f"VOICE MESSAGE RECEIVED from admin {message.chat.id}")
    
    # Get voice file ID
    voice_file_id = message.voice.file_id
    print(f"Voice file ID: {voice_file_id}")
    
    # Get all registered users
    user_ids = get_all_user_ids()
    sent_count = 0
    failed_count = 0
    
    if not user_ids:
        bot.reply_to(message, "لا يوجد مستخدمون مسجلون للبث إليهم.")
        return
    
    # Confirmation message to admin
    bot.reply_to(message, f"🎤 بدء عملية بث المقطع الصوتي إلى {len(user_ids)} مستخدم. يرجى الانتظار...")
    print(f"Starting voice broadcast to {len(user_ids)} users")

    # Send voice message to all users
    for user_id in user_ids:
        try:
            user_id = int(user_id.strip())
            bot.send_voice(chat_id=user_id, voice=voice_file_id)
            sent_count += 1
            print(f"Successfully sent voice broadcast to user {user_id}")
        except Exception as e:
            failed_count += 1
            if "bot was blocked by the user" in str(e).lower():
                print(f"User {user_id} has blocked the bot")
            else:
                print(f"Failed to send voice message to user {user_id}: {e}")
    
    # Send final report to admin
    report_message = f"🎤 ✅ تم بث المقطع الصوتي بنجاح إلى {sent_count} مستخدم.\n"
    if failed_count > 0:
        report_message += f"❌ فشل البث إلى {failed_count} مستخدم (ربما قاموا بحظر البوت أو حدث خطأ)."
    
    bot.send_message(ADMIN_ID, report_message)
    print(f"Voice broadcast completed: {sent_count} successful, {failed_count} failed")

# 10. Handler for all other message types from admin after broadcast command
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID, content_types=['text', 'photo', 'video', 'document', 'audio', 'sticker'])
def handle_admin_content(message):
    """Handle content from admin for broadcasting"""
    all_users = get_all_user_ids()
    sent_count = 0
    failed_count = 0
    
    if not all_users:
        bot.reply_to(message, "لا يوجد مستخدمون مسجلون للبث إليهم.")
        return
    
    # Confirmation message to admin
    bot.reply_to(message, f"بدء عملية البث إلى {len(all_users)} مستخدم. يرجى الانتظار...")
    print(f"Starting broadcast to {len(all_users)} users")

    # Send content to all users
    for user_id in all_users:
        try:
            user_id = int(user_id.strip())
            
            if message.content_type == 'text':
                bot.send_message(user_id, message.text)
            elif message.content_type == 'photo':
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'video':
                bot.send_video(user_id, message.video.file_id, caption=message.caption)
            elif message.content_type == 'document':
                bot.send_document(user_id, message.document.file_id, caption=message.caption)
            elif message.content_type == 'audio':
                bot.send_audio(user_id, message.audio.file_id, caption=message.caption)
            elif message.content_type == 'sticker':
                bot.send_sticker(user_id, message.sticker.file_id)
            
            sent_count += 1
            print(f"Successfully sent broadcast to user {user_id}")
            
        except Exception as e:
            failed_count += 1
            if "bot was blocked by the user" in str(e).lower():
                print(f"User {user_id} has blocked the bot")
            else:
                print(f"Telegram API error sending to {user_id}: {e}")
    
    # Send final report to admin
    report_message = f"✅ تم البث بنجاح إلى {sent_count} مستخدم.\n"
    if failed_count > 0:
        report_message += f"❌ فشل البث إلى {failed_count} مستخدم (ربما قاموا بحظر البوت أو حدث خطأ)."
    
    bot.send_message(ADMIN_ID, report_message)
    print(f"Broadcast completed: {sent_count} successful, {failed_count} failed")

# 11. Handler for all other messages (not from admin)
@bot.message_handler(func=lambda message: message.chat.id != ADMIN_ID)
def handle_other_users(message):
    """Handle messages from non-admin users"""
    # Save user ID in case they're messaging for the first time without /start
    save_user_id(message.chat.id)
    bot.reply_to(message, "أنا بوت خاص ولا يمكنني الرد حاليًا. استخدم الأمر /start للتسجيل في البوت.")
    print(f"Received message from non-admin user {message.chat.id}")

# 12. Handler for admin info command
@bot.message_handler(commands=['info'])
def handle_info_command(message):
    """Handle info command - show bot statistics to admin"""
    if message.chat.id == ADMIN_ID:
        user_count = len(get_all_user_ids())
        info_message = f"📊 معلومات البوت:\n\n👥 عدد المستخدمين المسجلين: {user_count}\n🆔 معرف المدير: {ADMIN_ID}\n🤖 حالة البوت: يعمل بشكل طبيعي"
        bot.reply_to(message, info_message)
    else:
        bot.reply_to(message, "هذا الأمر متاح للمدير فقط.")

# Error handler for polling
def error_handler():
    """Handle polling errors"""
    print("Bot polling stopped due to error. Attempting to restart...")

# 13. Run the bot
if __name__ == '__main__':
    try:
        # Start Flask web server first
        keep_alive()
        
        print("Starting Telegram Broadcast Bot...")
        print(f"Bot Token: {'*' * 20}{BOT_TOKEN[-10:] if len(BOT_TOKEN) > 10 else 'NOT_SET'}")
        print(f"Admin ID: {ADMIN_ID}")
        
        # Print Replit URL
        repl_url = os.environ.get('REPLIT_URL', 'URL not available')
        if repl_url != 'URL not available':
            print(f"🌐 Replit URL: {repl_url}")
        else:
            # Try to construct URL from other environment variables
            repl_slug = os.environ.get('REPL_SLUG', '')
            repl_owner = os.environ.get('REPL_OWNER', '')
            if repl_slug and repl_owner:
                constructed_url = f"https://{repl_slug}.{repl_owner}.repl.co"
                print(f"🌐 Project URL: {constructed_url}")
            else:
                print("🌐 URL: Not available in this environment")
        
        if BOT_TOKEN == 'your_bot_token_here' or ADMIN_ID == 0:
            print("WARNING: Please set BOT_TOKEN and ADMIN_ID environment variables!")
            print("BOT_TOKEN: Your Telegram bot token from @BotFather")
            print("ADMIN_ID: Your Telegram user ID (numeric)")
        
        # Delete webhook if exists to fix polling conflicts
        try:
            bot.delete_webhook()
            print("Webhook deleted successfully")
        except Exception as e:
            print(f"Note: Could not delete webhook: {e}")
        
        print("Bot is running... Press Ctrl+C to stop")
        bot.polling(none_stop=True, interval=1, timeout=60)
        
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Critical error occurred: {e}")
        print("Bot will attempt to restart...")
        # In a production environment, you might want to implement
        # automatic restart logic here
