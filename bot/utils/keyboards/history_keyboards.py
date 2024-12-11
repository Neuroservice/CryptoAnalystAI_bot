from aiogram import types


def file_format_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="PDF"), types.KeyboardButton(text="Excel")],
        ],
        resize_keyboard=True
    )

    return keyboard
