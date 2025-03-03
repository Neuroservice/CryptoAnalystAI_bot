import asyncio
import datetime
import logging

from bot.data_processing.data_update import fetch_crypto_data, update_agent_answers
from bot.database.backups import create_backup


async def parse_periodically(session):
    """
    Запускает обновление данных каждые 6 часов и обновление ответов агентов в 3:00 ночи.
    """
    logging.info("Запущен процесс периодического обновления данных.")

    # Немедленное обновление данных при старте
    try:
        logging.info("Первый запуск: немедленное обновление данных о криптовалютах.")
        await fetch_crypto_data(session)
        logging.info("Первичное обновление данных выполнено успешно.")
    except Exception as e:
        logging.error(f"Ошибка первичного обновления данных: {e}")

    while True:
        current_time = datetime.datetime.now(datetime.timezone.utc)

        # Вычисляем время следующего запуска обновления данных
        next_fetch_run = current_time + datetime.timedelta(hours=6 - (current_time.hour % 6))
        next_fetch_run = next_fetch_run.replace(minute=0, second=0, microsecond=0)
        time_until_fetch = (next_fetch_run - current_time).total_seconds()

        # Вычисляем время следующего обновления ответов агентов (в 3:00 ночи)
        next_agent_run = current_time.replace(hour=3, minute=0, second=0, microsecond=0)
        if current_time >= next_agent_run:
            next_agent_run += datetime.timedelta(days=1)
        time_until_agent = (next_agent_run - current_time).total_seconds()

        # Определяем, что выполнять первым
        if time_until_fetch <= time_until_agent:
            logging.info(f"Следующее обновление данных через {time_until_fetch // 3600:.2f} часов.")
            await asyncio.sleep(max(time_until_fetch, 1))  # Избегаем sleep(0)
            try:
                logging.info("Запуск обновления данных о криптовалютах...")
                await fetch_crypto_data(session)
                logging.info("Обновление данных завершено.")
            except Exception as e:
                logging.error(f"Ошибка обновления данных: {e}")
        else:
            logging.info(f"Следующее обновление ответов агентов через {time_until_agent // 3600:.2f} часов.")
            await asyncio.sleep(max(time_until_agent, 1))  # Избегаем sleep(0)
            try:
                logging.info("Запуск обновления данных и ответов агентов...")
                await asyncio.gather(
                    fetch_crypto_data(session),
                    update_agent_answers(),
                )
                logging.info("Все задачи выполнены успешно.")
            except Exception as e:
                logging.error(f"Ошибка при выполнении обновления: {e}")


async def backup_database():
    """Создаёт бэкап базы данных каждый день."""
    while True:
        try:
            await create_backup()
            logging.info(f"Бэкап создан")
        except Exception as e:
            logging.error(f"Ошибка при создании бэкапа: {e}")

        await asyncio.sleep(60 * 60 * 24)
