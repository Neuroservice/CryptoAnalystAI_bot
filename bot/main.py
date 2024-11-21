import asyncio
import datetime
import logging
import threading

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from bot.config import API_TOKEN, engine_url
from bot.database.db_setup import create_db
from bot.data_update import fetch_crypto_data, update_agent_answers
from bot.handlers import history, select_language

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
engine = create_async_engine(engine_url, echo=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


def parse_periodically():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def periodic_task():
        last_agent_update = datetime.datetime.utcnow() - datetime.timedelta(days=1)

        while True:
            try:
                async with SessionLocal() as session:
                    tasks = [fetch_crypto_data()]
                    current_time = datetime.datetime.utcnow()

                    if (current_time - last_agent_update).days >= 1:
                        tasks.append(update_agent_answers(session))
                        last_agent_update = current_time

                    await asyncio.gather(*tasks)
            except Exception as e:
                logging.error(f"Ошибка при выполнении задач: {e}", exc_info=True)

            await asyncio.sleep(3600)

    loop.run_until_complete(periodic_task())


async def main():
    try:
        await asyncio.to_thread(create_db)
        async with AiohttpSession() as aiohttp_session:
            bot = Bot(token=API_TOKEN, session=aiohttp_session)
            await bot.set_my_commands([BotCommand(command="/start", description="Запустить бота")])

            from bot.handlers import start, help, calculate
            dp.include_router(start.router)
            dp.include_router(help.router)
            dp.include_router(calculate.calculate_router)
            dp.include_router(history.history_router)
            dp.include_router(select_language.change_language_router)

            threading.Thread(target=parse_periodically, args=(), daemon=True).start()

            await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка в основном цикле: {e}")
    finally:
        logger.info("Завершение работы бота.")


if __name__ == "__main__":
    asyncio.run(main())
