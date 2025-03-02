from aiogram.types import Message, Update
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from bot.database.db_operations import get_one
from bot.database.models import User
from bot.utils.common.sessions import session_local, redis_client


class RestoreStateMiddleware(BaseMiddleware):
    """
    Middleware для восстановления языка общения с пользователем.
    """

    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory

    async def __call__(self, handler, event: Update, data: dict):
        if not hasattr(event, "message") or not isinstance(event.message, Message):
            return await handler(event, data)

        message = event.message
        user_id = message.from_user.id

        # Получаем пользователя из базы данных
        user = await get_one(model=User, telegram_id=user_id)

        if user and user.language:
            # Сохраняем язык пользователя в Redis
            await redis_client.hset(f"user:{user_id}", "language", user.language)

        # Получаем язык из Redis (если есть)
        user_language = await redis_client.hget(f"user:{user_id}", "language")

        # Если языка нет, можно по умолчанию установить 'ENG'
        if not user_language:
            user_language = "ENG"
            # Устанавливаем язык в Redis, если его не было
            await redis_client.hset(f"user:{user_id}", "language", user_language)

        # Сохраняем язык в data для дальнейшего использования
        data["language"] = user_language

        return await handler(event, data)
