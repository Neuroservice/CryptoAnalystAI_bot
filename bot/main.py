import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand

from bot.data_processing.tasks import (
    parse_periodically,
    parse_categories_weekly,
    parse_tokens_weekly,
)
from bot.handlers import history, select_language, donate
from bot.utils.common.config import API_TOKEN
from bot.utils.common.sessions import session_local, SessionLocal, redis_client
from bot.utils.middlewares import RestoreStateMiddleware
from bot.utils.resources.exceptions.exceptions import (
    ExceptionError,
    ValueProcessingError,
    MissingKeyError,
    AttributeAccessError,
)
from bot.utils.validations import check_redis_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

            logging.info("Запуск периодического обновления данных.")
            asyncio.create_task(parse_periodically(session_local))
            asyncio.create_task(parse_categories_weekly())
            asyncio.create_task(parse_tokens_weekly())

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
