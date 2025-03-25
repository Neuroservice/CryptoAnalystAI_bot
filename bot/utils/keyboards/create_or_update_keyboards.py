from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.utils.resources.buttons.button_strings_handler import button_text_by_user


async def create_or_update_keyboard(user_id: int):
    """
    Функция создает клавиатуру для выбора вида работ с данными проекта:
    Создать новый проект или обновить существующий.
    """

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=await button_text_by_user("add_project", user_id))],
            [KeyboardButton(text=await button_text_by_user("update_project", user_id))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    return keyboard
