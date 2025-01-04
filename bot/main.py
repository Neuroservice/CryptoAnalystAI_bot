import asyncio
import datetime
import logging

import redis.asyncio as redis
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from bot.config import API_TOKEN, engine_url, DB_PASSWORD, REDIS_PORT, REDIS_HOST
from bot.data_update import fetch_crypto_data, update_agent_answers
from bot.database.backups import create_backup
from bot.handlers import history, select_language, donate
from bot.utils.consts import session_local
from bot.utils.middlewares import RestoreStateMiddleware
from bot.utils.validations import save_execute

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
engine = create_async_engine(engine_url, echo=False, pool_timeout=60, connect_args={"timeout": 60})
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=DB_PASSWORD, db=0, decode_responses=True)


async def check_redis_connection():
    try:
        await redis_client.ping()
        print("Подключение к Redis успешно!")
    except redis.exceptions.ConnectionError:
        print("Не удалось подключиться к Redis!")
        raise Exception("Не удалось подключиться к Redis!")


async def parse_periodically():
    last_agent_update = None  # Храним время последнего выполнения задач в 3:00

    while True:
        current_time = datetime.datetime.utcnow()

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
                    await fetch_crypto_data()

                # Выполняем fetch_task каждые 6 часов
                await fetch_task()

            except Exception as e:
                print(f"Ошибка при выполнении fetch_task: {e}")

        else:
            await asyncio.sleep(time_until_agent)
            try:
                async def fetch_task():
                    await fetch_crypto_data()

                async def agent_update_task():
                    await update_agent_answers(session_local)

                async def backup_task():
                    await create_backup()

                # Выполняем все задачи в 3:00 ночи
                tasks = [fetch_task(), agent_update_task(), backup_task()]
                await asyncio.gather(*tasks)

                # Обновляем время последнего выполнения задач в 3:00
                last_agent_update = next_agent_run

            except Exception as e:
                print(f"Ошибка при выполнении задач в 3:00: {e}")


async def main():
    try:
        await check_redis_connection()
        # await create_db()
        # storage = MemoryStorage()

        async with AiohttpSession() as aiohttp_session:
            storage = RedisStorage(redis_client)
            dp = Dispatcher(storage=storage)

            bot = Bot(token=API_TOKEN, session=aiohttp_session)

            logger.info("Устанавливаются команды: %s", [
                BotCommand(command="/start", description="Запустить бота"),
                BotCommand(command="/analysis", description="Выбрать блок аналитики")
            ])

            await bot.set_my_commands([
                BotCommand(command="/start", description="Запустить бота"),
                BotCommand(command="/analysis", description="Выбрать блок аналитики")
            ])

            from bot.handlers import start, help, calculate, analysis
            dp.include_router(start.router)
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
        logging.error(f"Ошибка доступа к атрибуту: {attr_error}", exc_info=True)
        return {"error": f"Ошибка при попытке получить доступ к атрибуту: {attr_error}"}
    except KeyError as key_error:
        logging.error(f"Ошибка при доступе к ключу словаря: {key_error}", exc_info=True)
        return {"error": f"Ошибка при извлечении данных из словаря, отсутствует ключ: {key_error}"}
    except TypeError as type_error:
        logging.error(f"Ошибка типов данных: {type_error}", exc_info=True)
        return {"error": f"Неверный тип данных: {type_error}"}
    except Exception as e:
        logging.error(f"Общая ошибка при выполнении операции: {e}", exc_info=True)
        return {"error": f"Неизвестная ошибка: {e}"}
    finally:
        logger.info("Завершение работы бота.")


if __name__ == "__main__":
    asyncio.run(main())
