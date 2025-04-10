from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.utils.common.consts import ALLOWED_USERS
from bot.utils.resources.buttons.button_strings_handler import button_text_by_user


async def analysis_type_keyboard(user_id: int):
    """
    Функция создает клавиатуру для выбора вида анализа.
    """

    keyboard_buttons = [
        [KeyboardButton(text=await button_text_by_user("rebalancing_block", user_id))],
        [KeyboardButton(text=await button_text_by_user("analysis_block", user_id))],
        [KeyboardButton(text=await button_text_by_user("listing_price_block", user_id))],
    ]

    if user_id in ALLOWED_USERS:
        keyboard_buttons.append([KeyboardButton(text=await button_text_by_user("update_or_create_project", user_id))])

    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    return keyboard
