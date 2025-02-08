import asyncio
import datetime
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand

from bot.utils.common.config import API_TOKEN
from bot.data_processing.data_update import fetch_crypto_data, update_agent_answers
from bot.database.backups import create_backup
from bot.handlers import history, select_language, donate
from bot.utils.middlewares import RestoreStateMiddleware
from bot.utils.resources.exceptions.exceptions import (
    ExceptionError,
    ValueProcessingError,
    MissingKeyError,
    AttributeAccessError
)
from bot.utils.common.sessions import session_local, SessionLocal, redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_redis_connection():
    """
    Проверяет подключение к Redis и выводит сообщение об успешном подключении.
    Если подключение не удалось, вызывает исключение.
    """

    try:
        await redis_client.ping()
        print("Подключение к Redis успешно!")
    except ConnectionError:
        print("Не удалось подключиться к Redis!")
        raise Exception("Не удалось подключиться к Redis!")


async def parse_periodically():
    """
    Процедура, которая запускается каждые 6 часов и вызывает необходимые функции для обновления ответов агентов,
    обновления данных по токенам, создания бэкапов БД.
    """

    while True:
        current_time = datetime.datetime.now(datetime.timezone.utc)
        # Расчет времени до следующего запуска fetch_task (каждые 6 часов)
        next_fetch_run = current_time + datetime.timedelta(hours=6 - (current_time.hour % 6))
        next_fetch_run = next_fetch_run.replace(minute=0, second=0, microsecond=0)
        time_until_fetch = (next_fetch_run - current_time).total_seconds()

        # Расчет времени до 3:00 ночи
        next_agent_run = current_time.replace(hour=3, minute=0, second=0, microsecond=0)
        if current_time >= next_agent_run:
            next_agent_run += datetime.timedelta(days=1)
        time_until_agent = (next_agent_run - current_time).total_seconds()

        # Определяем, что нужно запускать первым
        if time_until_fetch <= time_until_agent:
            await asyncio.sleep(time_until_fetch)
            try:
                async def fetch_task():
                    await fetch_crypto_data(session_local)

                # Выполняем fetch_task каждые 6 часов
                await fetch_task()

            except Exception as e:
                raise ExceptionError(str(e))

        else:
            await asyncio.sleep(time_until_agent)
            try:
                async def fetch_task():
                    await fetch_crypto_data(session_local)

                async def agent_update_task():
                    await update_agent_answers(session_local)

                async def backup_task():
                    await create_backup()

                # Выполняем все задачи в 3:00 ночи
                tasks = [fetch_task(), agent_update_task(), backup_task()]
                await asyncio.gather(*tasks)

            except Exception as e:
                raise ExceptionError(str(e))


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

            logger.info("Устанавливаются команды: %s", [
                BotCommand(command="/start", description="Запустить бота / Bot start"),
                BotCommand(command="/analysis", description="Выбрать блок аналитики / Select an analytics block")
            ])

            await bot.set_my_commands([
                BotCommand(command="/start", description="Запустить бота / Bot start"),
                BotCommand(command="/analysis", description="Выбрать блок аналитики / Select an analytics block")
            ])

            from bot.handlers import start, help, calculate, analysis
            dp.include_router(start.start_router)
            dp.include_router(analysis.analysis_router)
            dp.include_router(help.help_router)
            dp.include_router(calculate.calculate_router)
            dp.include_router(history.history_router)
            dp.include_router(select_language.change_language_router)
            dp.include_router(donate.donate_router)

            dp.update.middleware(RestoreStateMiddleware(SessionLocal))

            asyncio.create_task(parse_periodically())

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
