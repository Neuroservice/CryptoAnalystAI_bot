from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.utils.resources.buttons.button_strings_handler import button_text_by_language


def main_menu_keyboard(language):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=button_text_by_language("help_button", language=language)),
                KeyboardButton(text=button_text_by_language("start_calculate_button", language=language)),
                KeyboardButton(text=button_text_by_language("start_history_button", language=language)),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard


def language_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text='Русский'),
                KeyboardButton(text='English'),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
