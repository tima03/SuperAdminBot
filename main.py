from telethon import TelegramClient, events
import logging
from decouple import config
from db_handler.db_class import PostgresHandler
from aiogram import Bot, Dispatcher
from aiogram.types import ChatMemberRestricted, ChatMemberBanned

# Initialize the database handler
pg_db = PostgresHandler(config('PG_LINK'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Telegram client and bot
client = TelegramClient('phoneTest', config('API_ID'), config('API_HASH')).start(bot_token=config('API_TOKEN'))
bot = Bot(token=config('API_TOKEN'))
dp = Dispatcher()

# Temporary user details
temp_user_details = {
    'name': None,
    'is_admin': None,
    'is_muted': None,
    'is_banned': None
}


def check_user_in_db(user_id):
    global temp_user_details
    if pg_db.connect_by_link():
        print("Database connected")
    try:
        pg_db.cursor.execute("""SELECT * FROM users WHERE userid = %s;""", [user_id])
        record = pg_db.cursor.fetchone()
        if record is None:
            if pg_db.disconnect():
                print("Database disconnected")
            return False
        else:
            temp_user_details['name'] = record[1]
            temp_user_details['is_admin'] = record[2]
            temp_user_details['is_muted'] = record[3]
            temp_user_details['is_banned'] = record[4]
            if pg_db.disconnect():
                print("Database disconnected")
            return True
    except Exception:
        if pg_db.disconnect():
            print("[INFO] Error checking user ID in the database")
        return False


def update_user_in_db(user_id, user_name, user_is_admin, user_is_muted, user_is_banned):
    if pg_db.connect_by_link():
        print("Database connected")
    pg_db.conn.autocommit = True
    sql_update_query = """UPDATE users SET username = %s, userisadmin = %s, userismuted = %s, userisbanned = %s WHERE 
    userid = %s;"""
    update_tuple = (user_name, user_is_admin, user_is_muted, user_is_banned, user_id)
    try:
        pg_db.cursor.execute(sql_update_query, update_tuple)
        temp_user_details.update({'name': None, 'is_admin': None, 'is_muted': None, 'is_banned': None})
        if pg_db.disconnect():
            print("Database disconnected")
    except Exception:
        if pg_db.disconnect():
            print("[INFO] Error updating user data in the database")


def insert_new_user_in_db(user_id, user_name, user_is_admin, user_is_muted, user_is_banned):
    if pg_db.connect_by_link():
        print("Database connected")
    pg_db.conn.autocommit = True
    sql_insert_query = """INSERT INTO users (userid, username, userisadmin, userismuted, userisbanned) VALUES (%s, 
    %s, %s, %s, %s);"""
    insert_tuple = (user_id, user_name, user_is_admin, user_is_muted, user_is_banned)
    try:
        pg_db.cursor.execute(sql_insert_query, insert_tuple)
        if pg_db.disconnect():
            print("Database disconnected")
    except Exception:
        if pg_db.disconnect():
            print("[INFO] Error adding user to the database")


@client.on(events.ChatAction(chats=config('CHAT_NAME')))
async def handle_chat_action(event):
    if event.user_joined:
        user = await event.get_user()
        await event.respond(f"Приветствуем тебя, {user.username or user.id}!")
    if event.user_left:
        user = await event.get_user()
        await event.respond(f"Прощаемся с тобой, {user.username or user.id}!")
    if event.user_joined or event.user_left:
        users = await client.get_participants(config('CHAT_NAME'))
        for user in users:
            if user.username is None:
                user.username = str(user.id)
            permissions = await client.get_permissions(event.chat_id, user.id)
            member = await bot.get_chat_member(event.chat_id, user.id)
            is_admin = permissions.is_admin
            is_muted = isinstance(member, ChatMemberRestricted)
            is_banned = isinstance(member, ChatMemberBanned)
            if not check_user_in_db(user.id):
                insert_new_user_in_db(user.id, user.username, is_admin, is_muted, is_banned)
            else:
                if (temp_user_details['name'] != user.username or
                        temp_user_details['is_admin'] != is_admin or
                        temp_user_details['is_muted'] != is_muted or
                        temp_user_details['is_banned'] != is_banned):
                    update_user_in_db(user.id, user.username, is_admin, is_muted, is_banned)


@client.on(events.NewMessage(pattern='hello'))
async def handler(event):
    await event.reply('Hey!')


client.start()
client.run_until_disconnected()
