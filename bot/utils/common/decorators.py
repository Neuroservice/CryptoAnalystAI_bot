import logging

from typing import Any

from bot.utils.common.sessions import session_local


def save_execute(f: Any):
    """
    Декоратор для оборачивания функций, работающих с базой данных.
    Если в процессе выполнения возникает исключение, производится rollback и логирование.
    Сессия берется из session_local, импортированной из bot.utils.common.sessions.
    Теперь при вызове функции не нужно явно передавать session.
    """

    async def wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except Exception as e:
            if hasattr(session_local, "rollback"):
                await session_local.rollback()
            logging.error(e)
            raise e

    return wrapper
