from typing import Any

from bot.utils.common.sessions import SessionLocal


def save_execute(f: Any):
    """
    Декоратор для управления сессией БД.
    Создает новую сессию, передает её в функцию и автоматически выполняет commit/rollback.
    """

    async def wrapper(*args, **kwargs):
        # Создаем новую сессию для каждого вызова функции
        async with SessionLocal() as session:
            # Используем транзакционный контекст, чтобы автоматически выполнить commit/rollback
            async with session.begin():
                result = await f(session, *args, **kwargs)
                return result

    return wrapper
