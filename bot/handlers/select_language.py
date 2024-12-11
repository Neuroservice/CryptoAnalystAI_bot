from aiogram import Router
from aiogram import types
from aiogram.filters import Command
from sqlalchemy.future import select

from bot.database.models import User
from bot.handlers.start import user_languages
from bot.utils.consts import SessionLocal
from bot.utils.keyboards.start_keyboards import main_menu_keyboard
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user

change_language_router = Router()


@change_language_router.message(Command("language"))
async def change_language(message: types.Message):
    user_id = message.from_user.id

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalars().first()

        if user:
            new_language = 'ENG' if user.language == 'RU' else 'RU'
            user.language = new_language
            user_languages.clear()
            user_languages[user_id] = new_language
            session.add(user)
        await session.commit()

        new_keyboard = main_menu_keyboard(new_language)

        # Отправляем сообщение с новой клавиатурой
        await message.answer(phrase_by_user("language_changed", user.telegram_id), reply_markup=new_keyboard)
