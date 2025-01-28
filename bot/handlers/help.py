from aiogram import Router, types

from bot.utils.common.sessions import session_local
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user

help_router = Router()


@help_router.message(lambda message: message.text == 'Помощь' or message.text == 'Help')
async def help_command(message: types.Message):
    """
    Хендлер для обработки пункта главного меню 'Помощь'.
    Пользователю выводиться базовое сообщение о том что может бот, какие функции в нем есть.
    """

    await message.answer(await phrase_by_user("help_phrase", message.from_user.id, session_local))
