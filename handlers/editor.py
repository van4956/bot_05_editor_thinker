import logging

# Инициализируем логгер модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Загружен модуль: %s", __name__)

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter, or_f
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from openai import OpenAI
from filters.is_admin import IsAdminListFilter
from filters.chat_type import ChatTypeFilter
from common import keyboard
from config_data.config import load_config


editor_router = Router()
editor_router.message.filter(ChatTypeFilter(["private"]), IsAdminListFilter(is_admin=True))

# Определяем класс состояния Editor
class Editor(StatesGroup):
    """Класс состояний для Editor"""
    editor_wait_command = State()
    editor_wait_text = State()
    editor_wait_channel = State()
# Получаем API ключ для работы с OpenAI
API_GPT = load_config().tg_bot.api_gpt

# Инициализируем клиент OpenAI
client = OpenAI(api_key=API_GPT)


# Функция очистки старых файлов
async def cleanup_temp_files():
    """Удаляет временные файлы старше 1 часа"""
    try:
        voice_dir = Path("temp_voice")
        if not voice_dir.exists():
            return

        current_time = datetime.now()
        for file in voice_dir.glob("*.ogg"):
            file_time = datetime.fromtimestamp(file.stat().st_mtime)
            if current_time - file_time > timedelta(hours=1):
                file.unlink(missing_ok=True)
                logger.info("Удален старый временный файл: %s", file)
    except Exception as e:
        logger.error("Ошибка при очистке временных файлов: %s", e)


# Функция исправления грамматики и пунктуации текста через GPT
async def fix_text_style(text: str) -> str:
    """Функция исправления грамматики и пунктуации текста через GPT"""
    try:
        system_prompt = """Ты опытный редактор текста. Твоя задача:
                            1. Исправить грамматические и пунктуационные ошибки
                            2. Обеспечить правильное написание заглавных букв (начало предложений, имена собственные)
                            3. Расставить корректные знаки препинания
                            4. НЕ менять порядок слов и смысл текста
                            5. НЕ добавлять новую информацию
                            6. НЕ писать ни чего от себя
                            7. Сохранить исходный стиль автора"""

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Исправь этот текст:\n\n{text}"}]
            )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("GPT вернул пустой ответ")
        return content

    except Exception as e:
        logger.error("Ошибка при обработке текста в GPT: %s", str(e))
        return f"Ошибка обработки текста: {str(e)}"


# Функция переформулирования текста через GPT
async def rephrase_text(text: str) -> str:
    """Переформулирует текст, делая его более лаконичным и литературным."""
    try:
        system_prompt = """Ты опытный литературный редактор. Твоя задача:
                            1. Переформулировать текст, сделав его более лаконичным и литературным
                            2. Улучшить стиль изложения, сохраняя естественность речи
                            3. Исправить грамматические и пунктуационные ошибки
                            4. Сохранить основной смысл, идею и посыл текста
                            5. НЕ добавлять новую информацию или факты
                            6. НЕ менять эмоциональный окрас текста
                            7. НЕ писать ни чего от себя"""

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Переформулируй этот текст:\n\n{text}"}
            ]
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("GPT вернул пустой ответ")
        return content

    except Exception as e:
        logger.error("Ошибка при обработке текста в GPT: %s", str(e))
        return f"Ошибка обработки текста: {str(e)}"


@editor_router.message(Editor.editor_wait_command, F.text)
async def editor_wait_command(message: Message, state: FSMContext, bot: Bot, chanel_dict: dict):
    # Очищаем старые временные файлы
    await cleanup_temp_files()

    if message.text == "↗️ Добавить":
        await message.answer("Ожидаю текст, или войс.", reply_markup=keyboard.del_kb)
        await state.set_state(Editor.editor_wait_text)

    elif message.text == "⏺️ Объединить":
        data = await state.get_data()
        list_text = data.get('text',[])
        text = '\n'.join(list_text)
        await state.update_data(text=[text])
        await message.answer(f"⏺️ Объединенный текст:\n\n<code>{text}</code>", reply_markup=keyboard.work_keyboard())
        await state.set_state(Editor.editor_wait_command)
        await asyncio.sleep(1)
        await message.answer("Ожидаю команду ⬇️")

    elif message.text == "🔄 Переформулировать 🔄":
        try:
            # Получаем текущий текст
            data = await state.get_data()
            list_text = data.get('text', [])
            text = list_text[-1]

            # Отправляем сообщение о начале обработки
            processing_msg = await message.answer("⌛️ Переформулирую текст...")

            # Переформулируем текст
            rephrased_text = await rephrase_text(text)

            # Обновляем данные
            list_text[-1] = rephrased_text
            await state.update_data(text=list_text)

            # Удаляем сообщение о обработке
            await processing_msg.delete()

            # Отправляем переформулированный текст
            await message.answer(f"🔄 Переформулированный текст:\n\n<code>{rephrased_text}</code>",
                                 reply_markup=keyboard.work_keyboard())
            await asyncio.sleep(1)
            await message.answer("Ожидаю команду ⬇️")

        except Exception as e:
            await message.answer(f"Ошибка при обработке текста: {str(e)}",
                                 reply_markup=keyboard.work_keyboard())

    elif message.text == "ℹ️ Поправить текст ℹ️":
        try:
            # Получаем текущий текст
            data = await state.get_data()
            list_text = data.get('text', [])
            text = list_text[-1]

            # Отправляем сообщение о начале обработки
            processing_msg = await message.answer("⌛️ Обрабатываю текст...")

            # Исправляем текст
            fixed_text = await fix_text_style(text)

            # Обновляем данные
            list_text[-1] = fixed_text
            await state.update_data(text=list_text)

            # Удаляем сообщение о обработке
            await processing_msg.delete()

            # Отправляем исправленный текст
            await message.answer(f"ℹ️ Исправленный текст:\n\n<code>{fixed_text}</code>",
                                 reply_markup=keyboard.work_keyboard())
            await asyncio.sleep(1)
            await message.answer("Ожидаю команду ⬇️")

        except Exception as e:
            await message.answer(f"Ошибка при обработке текста: {str(e)}",
                                 reply_markup=keyboard.work_keyboard())

    elif message.text == "❌ Отменить":
        await message.answer("❌ Действия отменены", reply_markup=keyboard.del_kb)
        await state.clear()
        await asyncio.sleep(2)
        await message.answer("Ожидаю текст, или войс.")

    elif message.text == "✅ Отправить":
        inline_channels_keyboard = InlineKeyboardBuilder()
        await message.answer('Выберите канал для отправки', reply_markup=keyboard.del_kb)
        await asyncio.sleep(1)
        for text, data in chanel_dict.items():
            btn = "btn_" + data
            inline_channels_keyboard.add(InlineKeyboardButton(text=text, callback_data=btn))
        inline_channels_keyboard.add(InlineKeyboardButton(text="❌ Отменить", callback_data="btn_cancel"))
        await message.answer('Доступные каналы:', reply_markup=inline_channels_keyboard.adjust(1,1,1,1).as_markup())
        await state.set_state(Editor.editor_wait_channel)

    else:
        await message.answer("Неизвестная команда.\nНажми на кнопку ⬇️", reply_markup=keyboard.work_keyboard())


@editor_router.callback_query(Editor.editor_wait_channel, F.data.startswith("btn_"))
async def editor_wait_channel(callback: CallbackQuery, state: FSMContext, bot: Bot, chanel_dict: dict):
    channel_data = callback.data.split('_')[1]
    channel_name = [k for k, v in chanel_dict.items() if v == channel_data]
    if channel_data == "cancel":
        await callback.message.delete()
        await callback.message.answer("❌ Отправка отменена", reply_markup=keyboard.del_kb)
        data = await state.get_data()
        text = data.get('text',[])
        await callback.message.answer(f"✍️ Ты написал:\n\n<code>{text}</code>")
        await state.set_state(Editor.editor_wait_command)
        await asyncio.sleep(1)
        await callback.message.answer("Ожидаю команду ⬇️", reply_markup=keyboard.work_keyboard())
    else:
        channel_id = int(channel_data)
        data = await state.get_data()
        current_time = datetime.now().strftime("%d.%m.%Y")
        list_text = data.get('text',[])
        text = current_time + '\n\n' + '\n'.join(list_text)
        try:
            # Проверяем существование чата
            chat = await bot.get_chat(chat_id=channel_id)
            print(f"Chat found: {chat.title} (ID: {chat.id})")

            # Проверяем права бота
            bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
            print(f"Bot rights: {bot_member.status}")

            # Пробуем отправить сообщение
            message = await bot.send_message(chat_id=channel_id, text=text)
            print(f"Message sent successfully: {message.message_id}")

        except Exception as e:
            print(f"Error details: {type(e).__name__}: {str(e)}")
            await callback.message.answer(f"❌ Ошибка отправки:\n\n<code>{str(e)}</code>", reply_markup=keyboard.del_kb)


        await callback.message.delete()
        await callback.message.answer(f"✅ Текст отправлен в <b>{channel_name[0]}</b>", reply_markup=keyboard.del_kb)
        await state.clear()
        await asyncio.sleep(1)
        await callback.message.answer("Ожидаю текст, или войс.", reply_markup=keyboard.del_kb)
        await state.set_state(Editor.editor_wait_text)


# Обработка неизвестных команд
@editor_router.message(Editor.editor_wait_command)
async def not_command(message: Message):
    await message.answer("Ожидаю получить команду.\nНажми на кнопку ⬇️", reply_markup=keyboard.work_keyboard())

# Обработка текста и голосовых сообщений
@editor_router.message(~StateFilter(Editor.editor_wait_command), or_f(F.text, F.voice))
async def editor_wait_text(message: Message, state: FSMContext, bot: Bot):
    if message.text:
        data = await state.get_data()
        list_text = data.get('text',[])
        list_text.append(message.text)
        await state.update_data(text=list_text)
        await message.answer(f"✍️ Ты написал:\n\n<code>{message.text}</code>",
                         reply_markup=keyboard.work_keyboard())
        await state.set_state(Editor.editor_wait_command)
        await asyncio.sleep(1)
        await message.answer("Ожидаю команду ⬇️")

    elif message.voice:
        # Сообщаем пользователю о начале обработки
        processing_msg = await message.answer("⌛️ Обрабатываю голосовое сообщение...")
        try:
            # Получаем файл голосового сообщения
            voice = await bot.get_file(message.voice.file_id)

            if not voice.file_path:
                raise ValueError("Не удалось получить путь к файлу голосового сообщения")

            # Создаем временную директорию, если её нет
            voice_dir = Path("temp_voice")
            voice_dir.mkdir(exist_ok=True)

            # Формируем путь для файла
            voice_path = voice_dir / f"{message.voice.file_id}.ogg"

            # Скачиваем файл
            await bot.download_file(voice.file_path, voice_path)
            logger.info("Скачан файл голосового сообщения: %s", voice_path)

            # Инициализируем клиент OpenAI
            # client = OpenAI(api_key=API_GPT)

            # Транскрибируем аудио
            with open(voice_path, "rb") as audio_file:
                transcript = await asyncio.to_thread(client.audio.transcriptions.create,
                                                                    model="whisper-1",
                                                                    file=audio_file,
                                                                    language="ru"
                                                                    )

            transcribed_text = transcript.text

            # Обновляем данные в FSM
            data = await state.get_data()
            list_text = data.get('text', [])
            list_text.append(transcribed_text)
            await state.update_data(text=list_text)

            # Отправляем результат пользователю
            await processing_msg.delete()
            await message.answer(f"🔍 Распознанный текст:\n\n<code>{transcribed_text}</code>",
                                reply_markup=keyboard.work_keyboard())
            await state.set_state(Editor.editor_wait_command)
            await asyncio.sleep(1)
            await message.answer("Ожидаю команду ⬇️")

        except Exception as e:
            await processing_msg.delete()
            await message.answer(f"Ошибка при обработке голосового сообщения: {e}",
                                 reply_markup=keyboard.work_keyboard())
            await state.set_state(Editor.editor_wait_command)
            logger.error("Ошибка при обработке голосового сообщения: %s", str(e))

        finally:
            # Удаляем временный файл
            if 'voice_path' in locals():
                try:
                    voice_path.unlink()
                except Exception as e:
                    logger.error("Ошибка при удалении временного файла: %s", str(e))


# Обработка неизвестных форматов сообщений
@editor_router.message(~StateFilter(Editor.editor_wait_command))
async def not_text_not_voice(message: Message):
    await message.answer("Ожидаю текст, или войс.\nНапиши что-нибудь в поле ввода, или создай войс.\nДругие форматы сообщений не обрабатываются.",
                         reply_markup=keyboard.del_kb)
