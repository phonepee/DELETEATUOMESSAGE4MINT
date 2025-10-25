import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
BOT_TOKEN = os.environ.get('8495322697:AAETNIrnJxKGvsgEc8EY1j3a5N_DMLTrrdw')

# Store messages to be deleted
messages_to_delete = []

class AutoDeleteBot:
    def __init__(self):
        self.application = None
        self.scheduler = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        user = update.effective_user
        await update.message.reply_html(
            rf"Hi {user.mention_html()}!",
            reply_markup=None
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        help_text = """
🤖 Auto Delete Bot Help:

This bot automatically deletes all messages in the group after 10 seconds.

Commands:
/start - Start the bot
/help - Show this help message
/delete_now - Manually trigger deletion of old messages (Admin only)

How to use:
1. Add this bot to your group
2. Make the bot an admin with "Delete messages" permission
3. The bot will automatically delete messages after 10 seconds

Note: The bot needs admin privileges to delete messages.
        """
        await update.message.reply_text(help_text)
    
    async def delete_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually trigger deletion of old messages."""
        # Check if user is admin
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status in ['administrator', 'creator']:
                await self.delete_old_messages(chat_id, context)
                await update.message.reply_text("🗑️ Manually triggered deletion of old messages.")
            else:
                await update.message.reply_text("❌ You need to be an admin to use this command.")
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            await update.message.reply_text("❌ Error checking permissions.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Store message for future deletion."""
        message = update.message
        
        # Only process group messages
        if message.chat.type in ['group', 'supergroup']:
            chat_id = message.chat.id
            message_id = message.message_id
            
            # Schedule deletion after 10 seconds
            deletion_time = datetime.now() + timedelta(seconds=10)
            
            # Store message info
            messages_to_delete.append({
                'chat_id': chat_id,
                'message_id': message_id,
                'deletion_time': deletion_time
            })
            
            logger.info(f"Message {message_id} in chat {chat_id} scheduled for deletion at {deletion_time}")
    
    async def delete_scheduled_messages(self):
        """Delete messages that are due for deletion."""
        current_time = datetime.now()
        messages_to_keep = []
        
        for message_info in messages_to_delete:
            if current_time >= message_info['deletion_time']:
                try:
                    await self.application.bot.delete_message(
                        chat_id=message_info['chat_id'],
                        message_id=message_info['message_id']
                    )
                    logger.info(f"Deleted message {message_info['message_id']} from chat {message_info['chat_id']}")
                except Exception as e:
                    logger.error(f"Error deleting message {message_info['message_id']}: {e}")
            else:
                messages_to_keep.append(message_info)
        
        # Update the list
        messages_to_delete.clear()
        messages_to_delete.extend(messages_to_keep)
    
    async def delete_old_messages(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Delete all scheduled messages for a specific chat."""
        global messages_to_delete
        
        messages_to_keep = []
        deleted_count = 0
        
        for message_info in messages_to_delete:
            if message_info['chat_id'] == chat_id:
                try:
                    await context.bot.delete_message(
                        chat_id=message_info['chat_id'],
                        message_id=message_info['message_id']
                    )
                    deleted_count += 1
                    logger.info(f"Manually deleted message {message_info['message_id']}")
                except Exception as e:
                    logger.error(f"Error manually deleting message {message_info['message_id']}: {e}")
                    messages_to_keep.append(message_info)
            else:
                messages_to_keep.append(message_info)
        
        # Update the list
        messages_to_delete.clear()
        messages_to_delete.extend(messages_to_keep)
        
        logger.info(f"Manually deleted {deleted_count} messages from chat {chat_id}")
    
    def setup_scheduler(self):
        """Setup the scheduler for periodic message deletion."""
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self.delete_scheduled_messages,
            'interval',
            seconds=5,  # Check every 5 seconds
            id='delete_messages'
        )
        self.scheduler.start()
    
    def run(self):
        """Start the bot."""
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN environment variable not set!")
            return
        
        # Create the Application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("delete_now", self.delete_now))
        self.application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, self.handle_message))
        
        # Setup scheduler
        self.setup_scheduler()
        
        # Start the Bot
        logger.info("Bot is starting...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    bot = AutoDeleteBot()
    bot.run()

if __name__ == '__main__':
    main()
