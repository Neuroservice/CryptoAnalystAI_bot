from aiogram import Router, types
from sqlalchemy import select

from bot.database.models import User
from bot.utils.consts import SessionLocal, user_languages
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user

help_router = Router()


@help_router.message(lambda message: message.text == 'Помощь' or message.text == 'Help')
async def help_command(message: types.Message):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalars().first()

        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.commit()

        if user.language:
            user_languages[message.from_user.id] = user.language

        await message.answer(phrase_by_user("help_phrase", message.from_user.id))
