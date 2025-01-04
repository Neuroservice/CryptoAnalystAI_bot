from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.database.models import User
from bot.utils.consts import user_languages, session_local


class RestoreStateMiddleware(BaseMiddleware):
    """Middleware для восстановления языка общения с пользователем."""

    def __init__(self, session_factory: async_sessionmaker):
        super().__init__()
        self.session_factory = session_factory

    async def __call__(self, handler, event: Update, data: dict):
        if not hasattr(event, 'message') or not isinstance(event.message, Message):
            return await handler(event, data)

        message = event.message

        async with session_local as session:
            result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
            user = result.scalars().first()

            if user and user.language and message.from_user.id not in user_languages:
                user_languages[user.telegram_id] = user.language

        return await handler(event, data)
