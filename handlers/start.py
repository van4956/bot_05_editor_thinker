import logging

# Инициализируем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)


import asyncio
from aiogram import F, Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import ChatMemberUpdatedFilter, KICKED, MEMBER
from aiogram.types import ChatMemberUpdated

from common import keyboard


# Инициализируем роутер уровня модуля
start_router = Router()

# Команда /start
@start_router.message(CommandStart())
async def start_cmd(message: Message, bot: Bot):
    user_name = message.from_user.username if message.from_user.username else 'None'
    user_id = message.from_user.id
    chat_id = bot.home_group[0]
    bot_username = bot.username
    await bot.send_message(chat_id=chat_id, text=f"✅ пользователь @{user_name} - запустил бота @{bot_username}")
    await message.answer(text=(f'Привет {user_name}.\n\n'
                                'Я персональный Telegram bot, model Т-5. '
                                'Если ты не в списке администраторов, то твои команды не будут работать.\n\n'
                                'Полный список команд - /help\n'
                                'Инструкция использования - /info'))

    await asyncio.sleep(2)
    # Отправляем сообщение пользователю если он в списке администраторов
    if user_id in bot.admin_list:
        await message.answer('Бот активирован!\n\nОжидаю текст, или войс.', reply_markup=keyboard.del_kb)
