import asyncio
import logging

from bot.database.backups import create_backup
from bot.data_processing.data_update import update_agent_answers


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
    """
    Задача обновления ответов модели. Выполняется раз в 12 часов
    """

    while True:
        try:
            await update_agent_answers()
        except Exception as e:
            logging.error(f"Ошибка при обновлении ответов агентов: {e}")

        await asyncio.sleep(60 * 60 * 12)
