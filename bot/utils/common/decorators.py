import logging

from typing import Any

from bot.utils.common.sessions import SessionLocal


def save_execute(f: Any):
    """
    Декоратор для оборачивания функций, работающих с базой данных.
    Автоматически управляет сессией и передаёт её в функцию.
    """

    async def wrapper(*args, **kwargs):
        async with SessionLocal() as session:
            try:
                result = await f(session, *args, **kwargs)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logging.error(f"Ошибка в {f.__name__}: {e}")
                raise e

    return wrapper
