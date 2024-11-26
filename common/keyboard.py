import logging

# Инициализируем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, KeyboardButtonPollType
from aiogram.utils.keyboard import ReplyKeyboardBuilder


# Удаление клавиатуры
del_kb = ReplyKeyboardRemove()


# Функция создания клавиатуры
def get_keyboard(
    *btns: str,
    placeholder: str | None = None,
    request_contact: int | None = None,
    request_location: int | None = None,
    sizes: tuple = (2,),
):
    '''
    Параметры request_contact и request_location должны быть индексами аргументов btns для нужных вам кнопок.
    Пример:
    get_keyboard(
            "Меню",
            "О магазине",
            "Варианты оплаты",
            "Варианты доставки",
            "Отправить номер телефона"
            placeholder="Что вас интересует?",
            request_contact=4,
            sizes=(2, 2, 1)
        )
    '''
    keyboard = ReplyKeyboardBuilder()

    for index, text in enumerate(btns, start=0):
        if request_contact and request_contact == index: keyboard.add(KeyboardButton(text=text, request_contact=True))
        elif request_location and request_location == index: keyboard.add(KeyboardButton(text=text, request_location=True))
        else: keyboard.add(KeyboardButton(text=text))

    return keyboard.adjust(*sizes).as_markup(resize_keyboard=True, # сделать кнопки поменьше
                                             input_field_placeholder=placeholder) # в поле ввода выводим текст placeholder


# Функция рабочей клавиатуры
def work_keyboard():
    return get_keyboard("↗️ Добавить", "⏺️ Объединить",
                        "🔄 Переформулировать 🔄",
                        "ℹ️ Поправить текст ℹ️",
                        "❌ Отменить", "✅ Отправить",
                        sizes=(2,1,1,2,1),
                        placeholder='⬇️')