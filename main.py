import telebot
import os
from threading import Thread
from flask import Flask, request

# 1. Flask web server setup for webhook
app = Flask(__name__)

# This route handles all incoming updates from Telegram
@app.route('/' + os.environ.get('BOT_TOKEN'), methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

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
# 13. Set webhook for Render deployment
if name == 'main':
    bot.delete_webhook() # Remove any existing webhook
    print("Webhook deleted successfully.")

    # Set new webhook to Render's URL
    try:
        render_url = os.environ.get('RENDER_EXTERNAL_URL')
        if not render_url:
            raise ValueError("RENDER_EXTERNAL_URL environment variable is not set.")
        
        webhook_url = render_url + '/' + BOT_TOKEN
        bot.set_webhook(url=webhook_url)
        print(f"Webhook set successfully to {webhook_url}")
        print("Bot is running on the web server!")
        
    except Exception as e:
        print(f"Error setting webhook: {e}")
        print("The bot will not receive updates. Please check your environment variables.")
