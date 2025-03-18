from aiogram import Router, types

from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.common.consts import (
    WALLET_ADDRESS,
    DONATE_TEXT_RU,
    DONATE_TEXT_ENG,
)

donate_router = Router()


@donate_router.message(lambda message: message.text == DONATE_TEXT_RU or message.text == DONATE_TEXT_ENG)
async def donate_command(message: types.Message):
    """
    Хендлер для обработки пункта главного меню 'Донат'.
    Выводит пользователю сообщение с кошельком для доната.
    """

    await message.answer(
        await phrase_by_user("donate", message.from_user.id) + f"<code>{WALLET_ADDRESS}</code>",
        parse_mode="HTML",
    )
