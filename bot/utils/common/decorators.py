import logging

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession


def save_execute(f: Any):
    """
    Декоратор для обертки хендлеров и функций, которые могут вызывать исключения при работе с базой данных.
    Если исключение произойдет, транзакция будет откатана и логировано.
    """

    async def wrapper(session: AsyncSession, *args, **kwargs):
        try:
            return await f(session, *args, **kwargs)
        except Exception as e:
            if hasattr(session, 'rollback'):
                await session.rollback()
            logging.error(e)

    return wrapper
