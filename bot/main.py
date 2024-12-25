import asyncio
import datetime
import logging

import redis.asyncio as redis
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from aiogram.fsm.storage.redis import RedisStorage

from bot.config import API_TOKEN, engine_url, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, REDIS_PORT, REDIS_HOST
from bot.data_update import fetch_crypto_data, update_agent_answers
from bot.database.backups import create_backup
from bot.database.db_setup import create_db
from bot.handlers import history, select_language, donate
from bot.utils.consts import STATE_FILE
from bot.utils.middlewares import RestoreStateMiddleware
from bot.utils.resources.files_worker.bot_states import restore_states, save_all_states


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
    last_agent_update = datetime.datetime.utcnow() - datetime.timedelta(days=1)

    while True:
        try:
            async def fetch_task():
                await fetch_crypto_data()

            async def agent_update_task():
                await update_agent_answers()

            async def backup_task():
                await create_backup()

            tasks = [fetch_task()]
            current_time = datetime.datetime.utcnow()

            if (current_time - last_agent_update).days >= 1:
                tasks.append(agent_update_task())
                # tasks.append(backup_task())
                last_agent_update = current_time

            # Выполнение всех задач
            await asyncio.gather(*tasks)

        except Exception as e:
            logging.error(f"Неизвестная ошибка при выполнении задач: {e}", exc_info=True)

        await asyncio.sleep(3600)


def start_parse_periodically():
    # Создаем новый цикл событий для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(parse_periodically())


async def main():
    try:
        await check_redis_connection()
        # await create_db()
        async with AiohttpSession() as aiohttp_session:
            # storage = MemoryStorage()
            storage = RedisStorage(redis_client)
            dp = Dispatcher(storage=storage)

            bot = Bot(token=API_TOKEN, session=aiohttp_session)
            await bot.set_my_commands([BotCommand(command="/start", description="Запустить бота")])

            from bot.handlers import start, help, calculate
            dp.include_router(start.router)
            dp.include_router(help.help_router)
            dp.include_router(calculate.calculate_router)
            dp.include_router(history.history_router)
            dp.include_router(select_language.change_language_router)
            dp.include_router(donate.donate_router)

            dp.update.middleware(RestoreStateMiddleware())

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
