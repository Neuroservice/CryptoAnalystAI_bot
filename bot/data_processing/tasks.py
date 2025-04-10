import asyncio
import logging
import traceback

from bot.data_processing.data_update import fetch_crypto_data, update_agent_answers
from bot.database.backups import create_backup


async def parse_data_and_answers():
    """
    Запускает обновление данных каждые 6 часов и обновление ответов агентов в 3:00 ночи.
    """
    try:
        logging.info("Запущен процесс периодического обновления данных.")

        asyncio.create_task(fetch_crypto_data())
        asyncio.create_task(periodically_update_answers())

        logging.info("All update tasks started successfully.")

        while True:
            await asyncio.sleep(3600)  # Стопимся на 1 час, чтобы не нагружать цикл

    except Exception as e:
        logging.error(f"Critical error in parse_periodically: {e}")
        logging.error(f"Exception type: {type(e).__name__}")
        logging.error("Traceback:")
        logging.error(traceback.format_exc())


async def backup_database():
    """Создаёт бэкап базы данных каждый день."""
    while True:
        try:
            await create_backup()
            logging.info(f"Бэкап создан")
        except Exception as e:
            logging.error(f"Ошибка при создании бэкапа: {e}")

        await asyncio.sleep(60 * 60 * 24)


async def periodically_update_answers():
    while True:
        await update_agent_answers()
        await asyncio.sleep(60 * 60 * 12)
