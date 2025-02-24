import asyncio
import datetime
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.common.config import API_TOKEN
from bot.data_processing.data_update import (
    fetch_crypto_data,
    update_agent_answers,
)
from bot.database.backups import create_backup
from bot.handlers import history, select_language, donate
from bot.utils.middlewares import RestoreStateMiddleware
from bot.utils.resources.exceptions.exceptions import (
    ExceptionError,
    ValueProcessingError,
    MissingKeyError,
    AttributeAccessError,
)
from bot.utils.common.sessions import session_local, SessionLocal, redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_redis_connection():
    """
    Проверяет подключение к Redis.
    """
    try:
        await redis_client.ping()
        logging.info("Подключение к Redis успешно!")
    except ConnectionError:
        logging.error("Не удалось подключиться к Redis!")
        raise Exception("Не удалось подключиться к Redis!")


async def parse_periodically(session: AsyncSession):
    """
    Запускает обновление данных каждые 6 часов и обновление ответов агентов в 3:00 ночи.
    """
    logging.info("Запущен процесс периодического обновления данных.")

    # Немедленное обновление данных при старте
    try:
        logging.info(
            "Первый запуск: немедленное обновление данных о криптовалютах."
        )
        await fetch_crypto_data(session)
        logging.info("Первичное обновление данных выполнено успешно.")
    except Exception as e:
        logging.error(f"Ошибка первичного обновления данных: {e}")

    while True:
        current_time = datetime.datetime.now(datetime.timezone.utc)

        # Вычисляем время следующего запуска обновления данных
        next_fetch_run = current_time + datetime.timedelta(
            hours=6 - (current_time.hour % 6)
        )
        next_fetch_run = next_fetch_run.replace(
            minute=0, second=0, microsecond=0
        )
        time_until_fetch = (next_fetch_run - current_time).total_seconds()

        # Вычисляем время следующего обновления ответов агентов (в 3:00 ночи)
        next_agent_run = current_time.replace(
            hour=3, minute=0, second=0, microsecond=0
        )
        if current_time >= next_agent_run:
            next_agent_run += datetime.timedelta(days=1)
        time_until_agent = (next_agent_run - current_time).total_seconds()

        # Определяем, что выполнять первым
        if time_until_fetch <= time_until_agent:
            logging.info(
                f"Следующее обновление данных через {time_until_fetch // 3600:.2f} часов."
            )
            await asyncio.sleep(max(time_until_fetch, 1))  # Избегаем sleep(0)
            try:
                logging.info("Запуск обновления данных о криптовалютах...")
                await fetch_crypto_data(session)
                logging.info("Обновление данных завершено.")
            except Exception as e:
                logging.error(f"Ошибка обновления данных: {e}")
        else:
            logging.info(
                f"Следующее обновление ответов агентов через {time_until_agent // 3600:.2f} часов."
            )
            await asyncio.sleep(max(time_until_agent, 1))  # Избегаем sleep(0)
            try:
                logging.info("Запуск обновления данных и ответов агентов...")
                await asyncio.gather(
                    fetch_crypto_data(session),
                    update_agent_answers(),
                    create_backup(),
                )
                logging.info("Все задачи выполнены успешно.")
            except Exception as e:
                logging.error(f"Ошибка при выполнении обновления: {e}")


async def main():
    """
    Запуск бота и его настройка.
    """

    try:
        await check_redis_connection()

        async with AiohttpSession() as aiohttp_session:
            storage = RedisStorage(redis_client)
            dp = Dispatcher(storage=storage)
            bot = Bot(token=API_TOKEN, session=aiohttp_session)

            logger.info("Настраиваются команды бота.")
            await bot.set_my_commands(
                [
                    BotCommand(
                        command="/start",
                        description="Запустить бота / Bot start",
                    ),
                    BotCommand(
                        command="/analysis",
                        description="Выбрать блок аналитики / Select an analytics block",
                    ),
                ]
            )

            from bot.handlers import start, help, calculate, analysis

            dp.include_router(start.start_router)
            dp.include_router(analysis.analysis_router)
            dp.include_router(help.help_router)
            dp.include_router(calculate.calculate_router)
            dp.include_router(history.history_router)
            dp.include_router(select_language.change_language_router)
            dp.include_router(donate.donate_router)

            dp.update.middleware(RestoreStateMiddleware(SessionLocal))

            # Логируем старт таски перед ее запуском
            logging.info("Запуск периодического обновления данных.")
            asyncio.create_task(parse_periodically(session_local))

            await dp.start_polling(bot)

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))

    finally:
        logger.info("Завершение работы бота.")


if __name__ == "__main__":
    asyncio.run(main())
