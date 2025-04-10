from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.utils.resources.buttons.button_strings_handler import button_text_by_user


async def main_menu_keyboard(user_id: int):
    """
    Создает и возвращает клавиатуру для главного меню бота.
    """

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=await button_text_by_user("help_button", user_id=user_id)),
                KeyboardButton(text=await button_text_by_user("start_calculate_button", user_id=user_id)),
                KeyboardButton(text=await button_text_by_user("start_history_button", user_id=user_id)),
                KeyboardButton(text=await button_text_by_user("donate", user_id=user_id)),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard


def language_keyboard():
    """
    Создает и возвращает клавиатуру для выбора языка.
    """

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Русский"),
                KeyboardButton(text="English"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard
