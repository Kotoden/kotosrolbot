# bot.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
import config
from database.db import init_db
from handlers import user_handlers, admin_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаём БД (таблицы) при старте
init_db()

# Просто передаём токен (без BotDefaults)
bot = Bot(token=config.TOKEN)
dp = Dispatcher()

# Подключаем роутеры с хендлерами
dp.include_router(user_handlers.router)
dp.include_router(admin_handlers.router)

async def main() -> None:
    logger.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
