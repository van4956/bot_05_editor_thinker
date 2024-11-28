import logging

# Настраиваем базовую конфигурацию логирования
logging.basicConfig(level=logging.INFO, format='  -  [%(asctime)s] #%(levelname)-5s -  %(name)s:%(lineno)d  -  %(message)s')
logger = logging.getLogger(__name__)

import asyncio
import psutil # этот модуль позволяет получать информацию о системе, такую как использование памяти и CPU

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.strategy import FSMStrategy
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config_data.config import Config, load_config
from handlers import admin, start, editor
from common.comands import private
from middlewares import counter


# Загружаем конфиг в переменную config
config: Config = load_config()

# Инициализируем объект хранилища
storage = MemoryStorage()  # данные хранятся в оперативной памяти, при перезапуске всё стирается (для тестов и разработки)

logger.info('Инициализируем бот и диспетчер')
bot = Bot(token=config.tg_bot.token,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML,
                                       link_preview=None,
                                       link_preview_is_disabled=None,
                                       link_preview_prefer_large_media=None,
                                       link_preview_prefer_small_media=None,
                                       link_preview_show_above_text=None))
bot.owner = config.tg_bot.owner
bot.admin_list = config.tg_bot.admin_list
bot.home_group = config.tg_bot.home_group
bot.work_group = config.tg_bot.work_group


dp = Dispatcher(fsm_strategy=FSMStrategy.USER_IN_CHAT, storage=storage)


# Помещаем нужные объекты в workflow_data диспетчера
chanel_dict = config.tg_bot.channels
dp.workflow_data.update({'chanel_dict': chanel_dict})

# Подключаем мидлвари
dp.update.outer_middleware(counter.CounterMiddleware())  # простой счетчик

# Подключаем роутеры
dp.include_router(start.start_router)
dp.include_router(admin.admin_router)
dp.include_router(editor.editor_router)



# Типы апдейтов которые будем отлавливать ботом
ALLOWED_UPDATES = dp.resolve_used_update_types()  # Отбираем только используемые события по роутерам

# Функция сработает при запуске бота
async def on_startup():
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    bot.username = bot_username
    await bot.send_message(chat_id = bot.home_group[0], text = f"🤖  @{bot_username}  -  запущен!")

# Функция сработает при остановке работы бота
async def on_shutdown():
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    await bot.send_message(chat_id = bot.home_group[0], text = f"☠️  @{bot_username}  -  деактивирован!")

# Функция мониторинга
async def monitor_resources():
    """Мониторит использование ресурсов и логирует при превышении лимитов"""
    try:
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # Конвертация в МБ

        if memory_usage > config.memory_limit:
            logger.warning("Высокое потребление памяти: %.2fMB (лимит: %sMB)", memory_usage, config.memory_limit)

        # Логируем использование CPU
        cpu_percent = process.cpu_percent(interval=1)
        if cpu_percent > 80:
            logger.warning("Высокая загрузка CPU: %s%%", cpu_percent)

    except Exception as e:
        logger.error("Ошибка мониторинга ресурсов: %s", e)

# Главная функция конфигурирования и запуска бота
async def main() -> None:

    # Регистрируем функцию, которая будет вызвана автоматически при запуске/остановке бота
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Пропускаем накопившиеся апдейты - удаляем вебхуки (то что бот получил пока спал)
    await bot.delete_webhook(drop_pending_updates=True)

    # Удаляем ранее установленные команды для бота во всех личных чатах
    await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())

    # Добавляем свои команды
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())


    # Запускаем polling
    try:
        await dp.start_polling(bot,
                               allowed_updates=ALLOWED_UPDATES,)
                            #    skip_updates=False)  # Если бот будет обрабатывать платежи, НЕ пропускаем обновления!

        while True:
            await monitor_resources()
            await asyncio.sleep(300)  # Проверка каждые 5 минут

    except Exception as e:
        logger.error("Критическая ошибка в main: %s", e)
        await bot.send_message(chat_id=bot.home_group[0],
                                text=f"⚠️ Критическая ошибка бота @<b>{bot.username}</b>: {e}")

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
