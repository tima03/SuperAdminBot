<h1 align="center">
  Привет, я <a href="https://github.com/tima03/" target="_blank">Валерия Шлыкова (Elka)</a>
  <img src="https://github.com/blackcater/blackcater/raw/main/images/Hi.gif" height="32"/>
</h1>
<h3 align="center">Студент компьютерных наук, блогер и стример из России 🇷🇺</h3>

<h1 align="center">SuperAdminBot</h1>

<p align="center">
  <em>Первоклассный open-source Telegram бот для управления чатами, созданный с использованием API Telethon и Aiogram.</em>
</p>

<p>
  SuperAdminBot предоставляет возможность:
  <ul>
    <li>Блокировать пользователей (Ban)</li>
    <li>Мьютить пользователей (Mute)</li>
    <li>Использовать: идентификатор пользователя (User Id), имя пользователя (UserName), информацию о банах и мьютах (is_banned, is_muted) в режиме реального времени</li>
    <li>Сохранять автоматически всю информацию в базу данных PostgreSQL, обеспечивая удобное и надежное управление данными</li>
  </ul>
</p>

<h2>Установка и настройка</h2>
<p><strong>Для установки зависимостей выполните:</strong></p>
<pre><code>pip install -r requirements.txt</code></pre>

<p><strong>Создайте файл с именем .env и настройте все необходимые API:</strong></p>
<pre><code>
PG_LINK=postgresql://username:password*@host:port/database #PostgreSQL link to your Database
API_ID=0000000000 #Telegram apps API_ID that you can get at https://my.telegram.org/auth?to=apps
API_HASH='39432jksdsdskjd333mnmn300' #Telegram apps API_HASH that you can get at https://my.telegram.org/auth?to=apps
API_TOKEN='000000000:ANsdnsdnNSDNdnnsdnsndSNDn' #Your bot token that you can get at @BotFather
</code></pre>

<h2>Основные функции и импорты:</h2>
<p>Вот фрагмент кода из <code>main.py</code>, показывающий основные функции и импорты бота:</p>
<pre><code>
from telethon import TelegramClient, events
import logging
from decouple import config
from db_handler.db_class import PostgresHandler
from aiogram import Bot, Dispatcher
from aiogram.types import ChatMemberRestricted, ChatMemberBanned

# Инициализация хендлера для базы данных по ссылке из .env
pg_db = PostgresHandler(config('PG_LINK'))

# Инициализация клиента Telegram apps api (Telethon) и бота telegram api (aiogram) 
client = TelegramClient('bot', api_id, api_hash)
bot = Bot(token=bot_token)
dp = Dispatcher(bot)

# Пример использования Telethon для получения информации о пользователях
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond('Привет! Я SuperAdminBot. Как я могу помочь вам сегодня?')
    raise events.StopPropagation

# Обработка действий в чате
@client.on(events.ChatAction(chats='your_chat'))
async def handle_chat_action(event):
    if event.user_joined or event.user_left:
        users = await client.get_participants('your_chat')
        for user in users:
            if user.username is None:
                user.username = str(user.id)
            permissions = await client.get_permissions(event.chat_id, user.id)
            member = await bot.get_chat_member(event.chat_id, user.id)
            is_admin = permissions.is_admin
            is_muted = isinstance(member, ChatMemberRestricted)
            is_banned = isinstance(member, ChatMemberBanned)
            # Ваш код для обработки информации о пользователе
</code></pre>

<h2>Поддержка</h2>
<p align="center">
  <a href="https://github.com/tima03/SuperAdminBot" target="_blank">
    <img src="https://img.shields.io/github/stars/tima03/SuperAdminBot?style=social" alt="GitHub stars"/>
  </a>
  <a href="https://github.com/tima03/SuperAdminBot/fork" target="_blank">
    <img src="https://img.shields.io/github/forks/tima03/SuperAdminBot?style=social" alt="GitHub forks"/>
  </a>
</p>

<h2>Свяжитесь со мной</h2>
<p align="center">
  <a href="https://t.me/elka_micro" target="_blank">
    <img src="https://img.icons8.com/color/48/000000/telegram-app.png" alt="Telegram"/>
  </a>
  <a href="https://vk.com/elkatsgirl" target="_blank">
    <img src="https://img.icons8.com/color/48/000000/vk-com.png" alt="VK"/>
  </a>
  <a href="https://www.instagram.com/elka_ts" target="_blank">
    <img src="https://img.icons8.com/color/48/000000/instagram-new.png" alt="Instagram"/>
  </a>
</p>
