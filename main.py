from telethon import TelegramClient, events
import logging
from decouple import config
from db_handler.db_class import PostgresHandler
from aiogram import Bot, Dispatcher
from aiogram.types import ChatMemberRestricted, ChatMemberBanned

pg_db = PostgresHandler(config('PG_LINK'))
# scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
# admins = [int(admin_id) for admin_id in config('ADMINS').split(',')]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = TelegramClient('phoneTest', config('API_ID'), config('API_HASH')).start(bot_token=config('API_TOKEN'))


bot = Bot(token=config('API_TOKEN'))
dp = Dispatcher()

def CheckIfUserIdInDB(user_ID):
    global temp_user_name
    global temp_user_isadmin
    global temp_user_ismuted
    global temp_user_isbanned
    if pg_db.connect_by_link(): print("БД подключена")
    try:
        pg_db.cursor.execute("""SELECT * FROM users WHERE userid = %s;""", [user_ID])
        record = pg_db.cursor.fetchone()
        if record is None:
            if pg_db.disconnect(): print("БД отключена")
            return False
        else:
            temp_user_name = record[1]
            temp_user_isadmin = record[2]
            temp_user_ismuted = record[3]
            temp_user_isbanned = record[4]
            if pg_db.disconnect(): print("БД отключена")
            return True
    except Exception as _ex:
        if pg_db.disconnect(): print("[INFO] Ошибка проверки ID пользователя в базе данных")
        return False


def UpdateUserInDatabase(user_ID, user_NAME, user_ISADMIN, user_ISMUTED, user_ISBANNED):
    if pg_db.connect_by_link(): print("БД подключена")
    pg_db.conn.autocommit = True
    sql_insert_query = """UPDATE users SET username = %s, userisadmin = %s,userismuted = %s, userisbanned = %s WHERE 
    userid = %s;"""
    insert_tuple = (user_NAME, user_ISADMIN, user_ISMUTED, user_ISBANNED, user_ID)
    try:
        pg_db.cursor.execute(sql_insert_query, insert_tuple)
        temp_user_name = None
        temp_user_isadmin = None
        temp_user_ismuted = None
        temp_user_isbanned = None
        if pg_db.disconnect(): print("Бд отключена")
    except Exception as _ex:
        if pg_db.disconnect(): print("[INFO] Ошибка обновления данных пользователя в бд")


def InsertNewUserInDB(user_ID, user_NAME, user_ISADMIN, user_ISMUTED, user_ISBANNED):
    if pg_db.connect_by_link(): print("БД подключена")
    pg_db.conn.autocommit = True
    sql_insert_query = """INSERT INTO users (userid, username, userisadmin, userismuted, userisbanned) VALUES (%s, 
    %s, %s, %s, %s);"""
    insert_tuple = (user_ID, user_NAME, user_ISADMIN, user_ISMUTED, user_ISBANNED)
    try:
        pg_db.cursor.execute(sql_insert_query, insert_tuple)
        if pg_db.disconnect(): print("БД отключена")
    except Exception as _ex:
        if pg_db.disconnect(): print("[INFO] Ошибка добавления пользователя в базу данных")


@client.on(events.ChatAction(chats=('trapfestchat')))
async def normal_handler(event):
    if (event.user_joined | event.user_left):
        users = await client.get_participants('trapfestchat')
        for user in users:
            if user.username == None:
                user.username = str(user.id)
            permissions = await client.get_permissions(event.chat_id, user.id)
            member = await bot.get_chat_member(event.chat_id, user.id)
            is_admin = permissions.is_admin
            is_muted = isinstance(member, ChatMemberRestricted)
            is_banned = isinstance(member, ChatMemberBanned)
            if not CheckIfUserIdInDB(user.id):
               InsertNewUserInDB(user.id, user.username, permissions.is_admin, is_muted, is_banned)
            else:
                if temp_user_name != user.username or temp_user_isadmin != is_admin or temp_user_ismuted != is_muted or\
                        temp_user_isbanned != is_banned:
                    UpdateUserInDatabase(user.id, user.username, is_admin, is_muted, is_banned)


client.start()
client.run_until_disconnected()
