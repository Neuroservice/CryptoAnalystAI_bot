from aiogram import Router, types
from sqlalchemy import select

from bot.database.models import User
from bot.utils.consts import WALLET_ADDRESS, user_languages, SessionLocal
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.validations import save_execute

donate_router = Router()


@donate_router.message(lambda message: message.text == 'Донат' or message.text == 'Donate')
async def donate_command(message: types.Message):
    await message.answer(
        phrase_by_user("donate", message.from_user.id) + f"<code>{WALLET_ADDRESS}</code>",
        parse_mode="HTML"
    )
