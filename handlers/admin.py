import logging

# Инициализируем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext


from filters.is_admin import IsAdminListFilter
from filters.chat_type import ChatTypeFilter
from common import keyboard



admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private", "group", "supergroup","channel"]), IsAdminListFilter(is_admin=True))


# команда /help
@admin_router.message(Command("help"))
async def cmd_help(message: Message, bot: Bot):
    if message.from_user.id in bot.admin_list:
        await message.answer(text=('Доступные команды:\n\n'
                                    '/start - перезапустить бота\n'
                                    '/data - состояние FSMContext\n'
                                    '/get_id - id диалога\n'
                                    '/ping - количество апдейтов\n'
                                    '/info - инструкция'),
                            reply_markup=keyboard.del_kb
                            )


# хендлер, покажет содержимое data пользователя
@admin_router.message(Command("data"))
async def data_cmd(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(str(data))

# Here is some example !ping command ...
@admin_router.message(Command(commands=["ping"]),)
async def cmd_ping_bot(message: Message, counter):
    await message.answer(f"ping-{counter}")


# Этот хендлер показывает ID чата в котором запущена команда
@admin_router.message(Command("get_id"))
async def get_chat_id_cmd(message: Message):
    await message.answer(f"ID: <code>{message.chat.id}</code>")

# хендлер /info
@admin_router.message(Command("info"))
async def cmd_info(message: Message):
    # photo = FSInputFile("common/images/image_info.jpg")
    await message.answer(text=('Инструкция по использованию:\n\n'
                                '1) Бот всегда в режиме ожидания\n'
                                '2) Боту можно отправить текстовое сообщение, либо войс\n'
                                '3) После бот выведет кнопки с доступными командами\n\n'
                                'Кнопки:\n\n'
                                '↗️ Добавить\n<i>Бот перейдет в режим ожидания дополнительного текста, либо войса</i>\n\n'
                                '⏺️ Объединить\n<i>Бот объединит все полученные тексты, и выведет результат</i>\n\n'
                                '🔄 Переформулировать 🔄\n<i>Бот переформулирует последний полученый текст, и выведет результат</i>\n\n'
                                'ℹ️ Поправить текст ℹ️\n<i>Бот исправит грамматику последнего полученного текста</i>\n\n'
                                '❌ Отменить\n<i>Бот очистит память, перейдет в состояние ожидания</i>\n\n'
                                '✅ Отправить\n<i>Бот отправить текст в группу с временной меткой в конце</i>'))
