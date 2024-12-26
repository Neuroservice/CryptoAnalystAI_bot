from aiogram import Router, types
from sqlalchemy import select

from bot.database.models import User
from bot.utils.consts import WALLET_ADDRESS, user_languages, SessionLocal
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.validations import save_execute

donate_router = Router()


@donate_router.message(lambda message: message.text == 'Донат' or message.text == 'Donate')
async def donate_command(session: SessionLocal(), message: types.Message):
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalars().first()

    if not user:
        user = User(telegram_id=message.from_user.id)
        session.add(user)
        await session.commit()

    if user.language:
        user_languages[message.from_user.id] = user.language

    await message.answer(
        phrase_by_user("donate", message.from_user.id) + f"<code>{WALLET_ADDRESS}</code>",
        parse_mode="HTML"
    )
