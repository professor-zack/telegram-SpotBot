from dotenv import load_dotenv
import os
from telegram import Update, MessageEntity
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from data import create_connection, update_spot_num, update_caught_num, fetch_spotboard, fetch_caughtboard

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_BOT_API_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message that explains how to use the bot."""
    start_msg = """
    Hello, welcome to SpotBot. SpotBot helps to facilitate and track spotted and caught numbers in a Telegram group.\n\n
To spot someone, send a picture of them and tag them in the picture's caption message, like "@alice".\n\n
/spotboard will display the ranked list of how many spots each group member has made.\n\n
/caughtboard will display the ranked list of how many times each group member has been caught."""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=start_msg)

async def spotboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the stats on number of spots each group member has made"""
    group_id = update.message.chat.id
    db_path = os.path.join('databases', f"{group_id}.db")
    if not os.path.exists(db_path):
        result_string = "No spots have been made in your group yet."
    else:
        result_string = fetch_spotboard(db_path)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result_string)

async def caughtboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the stats on number of times each group member has been caught"""
    group_id = update.message.chat.id
    db_path = os.path.join('databases', f"{group_id}.db")
    if not os.path.exists(db_path):
        result_string = "No spots have been made in your group yet."
    else:
        result_string = fetch_caughtboard(db_path)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result_string)

async def spot_detector(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detects and processes spots made"""
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

            group_id = update.message.chat.id
            sender = update.message.from_user
            sender_username = sender.username if sender.username else f"{sender.first_name} {sender.last_name if sender.last_name else ''}"
            
            db_path = os.path.join('databases', f"{group_id}.db")
            conn = create_connection(db_path)

            update_spot_num(conn, sender_username, len(mentioned_users))

            for caught_user in mentioned_users:
                update_caught_num(conn, caught_user)

            conn.close()

            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'{sender_username} has spotted {mentioned_users_string}')

def main():
    # Create the Application and pass it your bot's API token
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Register the /greet command handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("spotboard", spotboard))
    application.add_handler(CommandHandler("caughtboard", caughtboard))
    application.add_handler(MessageHandler(filters.PHOTO, spot_detector))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
