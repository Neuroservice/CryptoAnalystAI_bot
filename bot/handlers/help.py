from aiogram import Router, types
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user

help_router = Router()


@help_router.message(lambda message: message.text == 'Помощь' or message.text == 'Help')
async def help_command(message: types.Message):
    await message.answer(phrase_by_user("help_phrase", message.from_user.id))
