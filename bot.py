from dotenv import load_dotenv
import os
from telegram import Update, MessageEntity, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from data import create_connection, update_spot_num, update_caught_num, fetch_spotboard, fetch_caughtboard
import logging

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_BOT_API_TOKEN')

CONFIRMATION = range(1)

log_file_path = 'logs.txt'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file_path, mode='a'),
        logging.StreamHandler()
    ]
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message that explains how to use the bot."""
    try:
        chat = update.effective_chat
        if chat.type not in ['group', 'supergroup']:
            return
        sender = update.effective_user
        sender_username = sender.username if sender.username else f"{sender.first_name} {sender.last_name if sender.last_name else ''}"
        start_msg = """
        Hello, welcome to SpotBot. SpotBot helps to facilitate spotting in a Telegram group.\n
    To spot someone, send a picture of them and tag them in the picture's caption like "(image) @alice".\n
    /spotboard will display the ranked list of how many spots each group member has made.\n
    /caughtboard will display the ranked list of how many times each group member has been caught.\n
    /reset will reset all the spot data in the group. This command can only be executed by an admin or owner of the group."""
        await context.bot.send_message(chat_id=chat.id, text=start_msg)
        logger.info(f"start command called in group {chat.id}, by user {sender_username}")
    except Exception as e:
        logger.error(f"Error in start command handler: {e}")

async def spotboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the stats on number of spots each group member has made"""
    try:
        #group_id = update.message.chat.id
        chat = update.effective_chat
        if chat.type not in ['group', 'supergroup']:
            return
        group_id = chat.id
        sender = update.effective_user
        sender_username = sender.username if sender.username else f"{sender.first_name} {sender.last_name if sender.last_name else ''}"
        db_path = os.path.join('databases', f"{group_id}.db")
        if not os.path.exists(db_path):
            result_string = "No spots have been made in your group yet."
        else:
            result_string = fetch_spotboard(db_path)
            result_string = "Spotboard:\n\n"+result_string
        await context.bot.send_message(chat_id=chat.id, text=result_string)
        logger.info(f"spotboard command called in group {chat.id}, by user {sender_username}")
    except Exception as e:
        logger.error(f"Error in spotboard command handler: {e}")

async def caughtboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the stats on number of times each group member has been caught"""
    try:
        chat = update.effective_chat
        if chat.type not in ['group', 'supergroup']:
            return
        #group_id = update.message.chat.id
        group_id = chat.id
        sender = update.effective_user
        sender_username = sender.username if sender.username else f"{sender.first_name} {sender.last_name if sender.last_name else ''}"
        db_path = os.path.join('databases', f"{group_id}.db")
        if not os.path.exists(db_path):
            result_string = "No spots have been made in your group yet."
        else:
            result_string = fetch_caughtboard(db_path)
            result_string = "Caughtboard:\n\n"+result_string
        await context.bot.send_message(chat_id=chat.id, text=result_string)
        logger.info(f"caughtboard command called in group {chat.id}, by user {sender_username}")
    except Exception as e:
        logger.error(f"Error in caughtboard command handler: {e}")

async def spot_detector(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detects and processes spots made"""
    try:
        chat = update.effective_chat
        if chat.type not in ['group', 'supergroup']:
            return
        if update.message.photo:
            message_entities = update.message.caption_entities or []
            mentioned_users = []
            tagged_user_present_status = False
            for entity in message_entities:
                if entity.type==MessageEntity.MENTION:
                    tagged_user = update.message.caption[entity.offset:entity.offset + entity.length]
                    mentioned_users.append(tagged_user[1:])
                    tagged_user_present_status = True
                    
            if tagged_user_present_status:
                mentioned_users_string = ', '.join(mentioned_users)

                #group_id = update.message.chat.id
                group_id = chat.id
                #sender = update.message.from_user
                sender = update.effective_user
                sender_username = sender.username if sender.username else f"{sender.first_name} {sender.last_name if sender.last_name else ''}"
                
                db_path = os.path.join('databases', f"{group_id}.db")
                conn = create_connection(db_path)

                update_spot_num(conn, sender_username, len(mentioned_users))

                for caught_user in mentioned_users:
                    update_caught_num(conn, caught_user)

                conn.close()

                await context.bot.send_message(chat_id=chat.id, text=f'{sender_username} has spotted {mentioned_users_string}')
                logger.info(f"spot made in group {chat.id}, by user {sender_username}, of {mentioned_users_string}")
    except Exception as e:
        logger.error(f"Error in spot detector function {e}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /reset command, asking for confirmation."""
    try:
        chat = update.effective_chat
        if chat.type not in ['group', 'supergroup']:
            return
        user = update.effective_user
        chat_id = update.effective_chat.id

        db_path = os.path.join('databases', f"{chat_id}.db")
        if not os.path.exists(db_path):
            await context.bot.send_message(chat_id=chat_id, text="No spots have been made in your group yet.")
        else:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)

            if chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                keyboard = [
                    [InlineKeyboardButton("Yes", callback_data='yes')],
                    [InlineKeyboardButton("No", callback_data='no')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id=chat_id, text="Are you sure you want to reset?", reply_markup=reply_markup)
                return CONFIRMATION
            else:
                await context.bot.send_message(chat_id=chat_id, text="You must be a group admin to use this command.")
                return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in reset command handler: {e}")
        return ConversationHandler.END

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the confirmation response."""
    try:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat_id
        await query.edit_message_reply_markup(reply_markup=None)
        if query.data == 'yes':
            db_path = os.path.join('databases', f"{chat_id}.db")
            os.remove(db_path)
            await context.bot.send_message(chat_id=chat_id, text="The group's spotted data has been reset.")
            sender = update.effective_user
            sender_username = sender.username if sender.username else f"{sender.first_name} {sender.last_name if sender.last_name else ''}"
            logger.info(f"reset command executed in group {chat_id}, by user {sender_username}")
        else:
            await context.bot.send_message(chat_id=chat_id, text="Reset cancelled.")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in confirm function after reset command: {e}")
        return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(API_TOKEN).build()

    reset_handler = CommandHandler("reset", reset)
    confirmation_handler = CallbackQueryHandler(confirm, pattern='^(yes|no)$')

    conv_handler = ConversationHandler(
        entry_points=[reset_handler],
        states={
            CONFIRMATION: [confirmation_handler]
        },
        fallbacks=[]
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("spotboard", spotboard))
    application.add_handler(CommandHandler("caughtboard", caughtboard))
    application.add_handler(MessageHandler(filters.PHOTO, spot_detector))

    application.run_polling()

if __name__ == '__main__':
    main()
