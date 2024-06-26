import re
from telethon import TelegramClient, events
import logging
from decouple import config
from db_handler.db_class import PostgresHandler
from aiogram import Bot, Dispatcher
from aiogram.types import ChatMemberRestricted, ChatMemberBanned, ChatPermissions
import time

processed_events = {}

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
        if user.username is None:
            logging.info(f"User {event.user_id} entered in the chat.")
            await event.respond(f"Приветстуем тебя, {user.id}!")
        else:
            logging.info(f"User {event.user_id} entered in the chat.")
            await event.respond(f"Приветстуем тебя, {user.username}!")
    elif event.user_left or event.user_kicked:
        event_id = (event.chat_id, event.user_id)
        now = time.time()
        if event_id in processed_events and (now - processed_events[event_id]) < 10:
            print("Дублирование")
            return
        processed_events[event_id] = now
        user = await event.get_user()
        if user.username is None:
            logging.info(f"User {event.user_id} left or was kicked from the chat.")
            await event.respond(f"Прощаемся с тобой, {user.id}!")
        else:
            logging.info(f"User {event.user_id} left or was kicked from the chat.")
            await event.respond(f"Прощаемся с тобой, {user.username}!")
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


@client.on(events.NewMessage(pattern=re.compile(r'^-sms$', re.IGNORECASE)))
async def sms_delete(event):
    user_id = event.message.to_dict()['from_id']['user_id']
    permissions = await client.get_permissions(event.chat_id, user_id)
    if permissions.is_admin:
        await client.delete_messages(event.chat_id, event.message.reply_to_msg_id)
        await client.delete_messages(event.chat_id, event.message.id)


# Обработчик команды mute при ответе на сообщение
@client.on(events.NewMessage(pattern=re.compile(r'^(?!.*@)\bmute\b', re.IGNORECASE)))
async def mute_user_reply(event):
    user_id = event.message.to_dict()['from_id']['user_id']
    permissions = await client.get_permissions(event.chat_id, user_id)

    if permissions.is_admin and event.message.is_reply:
        try:
            reply_message = await event.get_reply_message()
            user_replied_to_id = reply_message.from_id.user_id
            user_replied_to = await client.get_entity(user_replied_to_id)

            await bot.restrict_chat_member(
                event.chat_id,
                user_replied_to_id,
                ChatPermissions(can_send_messages=False)
            )
            await event.respond(f"{user_replied_to.username or user_replied_to_id} is muted")
        except Exception:
            await event.respond("Такого пользователя нет в чате")
    else:
        await event.respond("Выберите пользователя для мьюта")


# Обработчик команды unmute при ответе на сообщение
@client.on(events.NewMessage(pattern=re.compile(r'^(?!.*@)\bunmute\b', re.IGNORECASE)))
async def unmute_user_reply(event):
    user_id = event.message.to_dict()['from_id']['user_id']
    permissions = await client.get_permissions(event.chat_id, user_id)
    if permissions.is_admin and event.message.is_reply:
        try:
            reply_message = await event.get_reply_message()
            user_replied_to_id = reply_message.from_id.user_id
            user_replied_to = await client.get_entity(user_replied_to_id)

            await bot.restrict_chat_member(
                event.chat_id,
                user_replied_to_id,
                ChatPermissions(can_send_messages=True)
            )
            await event.respond(f"{user_replied_to.username or user_replied_to_id} is unmuted")
        except Exception:
            await event.respond("Такого пользователя нет в чате")
    else:
        await event.respond("Выберите пользователя для анмьюта")


@client.on(events.NewMessage(pattern=re.compile(r'^(?!.*@)\bban\b', re.IGNORECASE)))
async def sms_delete(event):
    user_id = event.message.to_dict()['from_id']['user_id']
    permissions = await client.get_permissions(event.chat_id, user_id)
    if permissions.is_admin and event.message.is_reply:
        try:
            reply_message = await event.get_reply_message()
            user_replied_to_id = reply_message.from_id.user_id
            user_replied_to = await client.get_entity(user_replied_to_id)

            await bot.ban_chat_member(event.chat_id, user_replied_to_id)
            await event.respond(user_replied_to.username + " is banned")
        except Exception:
            await event.respond("Такого пользователя нет в чате")
    else:
        await event.respond("Выберите пользователя для бана")


@client.on(events.NewMessage(pattern=re.compile(r'^(?!.*@)\bunban\b', re.IGNORECASE)))
async def sms_delete(event):
    user_id = event.message.to_dict()['from_id']['user_id']
    permissions = await client.get_permissions(event.chat_id, user_id)
    if permissions.is_admin and event.message.is_reply:
        try:
            reply_message = await event.get_reply_message()
            user_replied_to_id = reply_message.from_id.user_id
            user_replied_to = await client.get_entity(user_replied_to_id)

            await bot.unban_chat_member(event.chat_id, user_replied_to_id)
            await event.respond(user_replied_to.username + " is unbanned")
        except Exception:
            await event.respond("Такого пользователя нет в чате")
    else:
        await event.respond("Выберите пользователя для бана")


@client.on(events.NewMessage(pattern=re.compile(r'mute\s+@(\w+)', re.IGNORECASE)))
async def mute_user(event):
    user_id = event.message.to_dict()['from_id']['user_id']
    permissions = await client.get_permissions(event.chat_id, user_id)

    if permissions.is_admin:
        find_nick_message = re.search(r'mute\s+@(\w+)', event.message.text, re.IGNORECASE)
        if find_nick_message:
            nick_message = find_nick_message.group(1)
            if nick_message.isalnum():
                if nick_message.isdigit():
                    try:
                        await bot.restrict_chat_member(
                            event.chat_id,
                            nick_message,
                            ChatPermissions(can_send_messages=False)
                        )
                        await event.respond(f"{nick_message} is muted")
                    except Exception:
                        await event.respond("Видимо такого ника или id не существует")
                else:
                    try:
                        user_to_mute = await client.get_entity(nick_message)
                        await bot.restrict_chat_member(
                            event.chat_id,
                            user_to_mute.id,
                            ChatPermissions(can_send_messages=False)
                        )
                        await event.respond(f"{nick_message} is muted")
                    except Exception:
                        await event.respond("Видимо такого ника или id не существует")
            else:
                await event.respond("Nickname can contain only letters and digits")
        else:
            await event.respond("No nickname found in the text")
    else:
        await event.respond("You don't have permission to mute users")


# Пример функции unmute для снятия ограничения с пользователя
@client.on(events.NewMessage(pattern=re.compile(r'unmute\s+@(\w+)', re.IGNORECASE)))
async def unmute_user(event):
    user_id = event.message.to_dict()['from_id']['user_id']
    permissions = await client.get_permissions(event.chat_id, user_id)

    if permissions.is_admin:
        find_nick_message = re.search(r'unmute\s+@(\w+)', event.message.text, re.IGNORECASE)
        if find_nick_message:
            nick_message = find_nick_message.group(1)
            if nick_message.isalnum():
                if nick_message.isdigit():
                    try:
                        await bot.restrict_chat_member(
                            event.chat_id,
                            nick_message,
                            ChatPermissions(can_send_messages=True)
                        )
                        await event.respond(f"{nick_message} is unmuted")
                    except Exception:
                        await event.respond("Видимо такого ника или id не существует")
                else:
                    try:
                        user_to_unmute = await client.get_entity(nick_message)
                        await bot.restrict_chat_member(
                            event.chat_id,
                            user_to_unmute.id,
                            ChatPermissions(can_send_messages=True)
                        )
                        await event.respond(f"{nick_message} is unmuted")
                    except Exception:
                        await event.respond("Видимо такого ника или id не существует")
            else:
                await event.respond("Nickname can contain only letters and digits")
        else:
            await event.respond("No nickname found in the text")
    else:
        await event.respond("You don't have permission to unmute users")


@client.on(events.NewMessage(pattern=re.compile(r'ban\s+@(\w+)', re.IGNORECASE)))
async def sms_delete(event):
    user_id = event.message.to_dict()['from_id']['user_id']
    permissions = await client.get_permissions(event.chat_id, user_id)
    if permissions.is_admin:
        find_nick_message = re.search(r'ban\s+@(\w+)', event.message.text, re.IGNORECASE)
        if find_nick_message:
            nick_massage = find_nick_message.group(1)
            if nick_massage.isalnum():
                if nick_massage.isdigit():
                    try:
                        await bot.ban_chat_member(event.chat_id, nick_massage)
                        await event.respond(nick_massage + " is banned")
                    except Exception:
                        await event.respond("Видимо такого ника или id не существует")
                else:
                    try:
                        user_toban = await client.get_entity(nick_massage)
                        await bot.ban_chat_member(event.chat_id, user_toban.id)
                        await event.respond(nick_massage + " is banned")
                    except Exception:
                        await event.respond("Видимо такого ника или id не существует")
            else:
                await event.respond("Nickname can contain only latter's and digits")
        else:
            await event.respond("No nickname found in the text")


@client.on(events.NewMessage(pattern=re.compile(r'unban\s+@(\w+)', re.IGNORECASE)))
async def sms_delete(event):
    user_id = event.message.to_dict()['from_id']['user_id']
    permissions = await client.get_permissions(event.chat_id, user_id)
    if permissions.is_admin:
        find_nick_message = re.search(r'unban\s+@(\w+)', event.message.text, re.IGNORECASE)
        if find_nick_message:
            nick_massage = find_nick_message.group(1)
            if nick_massage.isalnum():
                if nick_massage.isdigit():
                    try:
                        await bot.unban_chat_member(event.chat_id, nick_massage)
                        await event.respond(nick_massage + " is unbanned")
                    except Exception:
                        await event.respond("Видимо такого ника или id не существует")
                else:
                    try:
                        user_toban = await client.get_entity(nick_massage)
                        await bot.unban_chat_member(event.chat_id, user_toban.id)
                        await event.respond(nick_massage + " is unbanned")
                    except Exception:
                        await event.respond("Видимо такого ника или id не существует")
            else:
                await event.respond("Nickname can contain only latter's and digits")
        else:
            await event.respond("No nickname found in the text")


client.start()
client.run_until_disconnected()
