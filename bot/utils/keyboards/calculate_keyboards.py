from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.utils.resources.buttons.button_strings_handler import button_text_by_user


def analysis_type_keyboard(user_id):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text_by_user("rebalancing_block", user_id))],
            [KeyboardButton(text=button_text_by_user("analysis_block", user_id))],
            [KeyboardButton(text=button_text_by_user("listing_price_block", user_id))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    return keyboard
