# bot.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
import config
from database.db import init_db
from handlers import user_handlers, admin_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаём таблицы в БД (если ещё не созданы)
init_db()

# Инициализируем бота с режимом форматирования HTML
bot = Bot(token=config.TOKEN, parse_mode=ParseMode.HTML)

# Dispatcher
dp = Dispatcher()

# Подключаем роутеры (handler-ы)
dp.include_router(user_handlers.router)
dp.include_router(admin_handlers.router)


async def main() -> None:
    logger.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
