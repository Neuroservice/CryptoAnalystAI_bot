from aiogram import Router
from aiogram import types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from bot.database.models import User
from bot.handlers.start import user_languages
from bot.utils.consts import translations

change_language_router = Router()
DATABASE_URL = "sqlite+aiosqlite:///./crypto_analysis.db"  # Локалка
# DATABASE_URL = "sqlite+aiosqlite:///bot/crypto_analysis.db" # Прод

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(
    class_=AsyncSession,
    bind=engine,
    expire_on_commit=False
)


@change_language_router.message(Command("language"))
async def change_language(message: types.Message):
    user_id = message.from_user.id

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalars().first()

        if user:
            new_language = 'ENG' if user.language == 'RU' else 'RU'
            user.language = new_language
            user_languages.clear()
            user_languages[user_id] = new_language
            await session.commit()

            await message.answer(translations[new_language]["language_changed"])
        else:
            current_language = user_languages.get(user_id, "ENG")
            await message.answer(translations[current_language]["user_not_found"])
