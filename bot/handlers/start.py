from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.database.models import User
from bot.utils.consts import user_languages, session_local
from bot.utils.keyboards.start_keyboards import main_menu_keyboard, language_keyboard
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user

router = Router()


@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    session = session_local
    await state.clear()
    await state.set_state(None)

    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalars().first()

    if not user:
        user = User(telegram_id=message.from_user.id)
        session.add(user)
        await session.commit()

    if user.language:
        user_languages[user.telegram_id] = user.language
        await message.answer(phrase_by_user("hello_phrase", user.telegram_id),
                             reply_markup=main_menu_keyboard(language=user.language))

    else:
        await message.answer("Please choose your language / Пожалуйста, выберите язык:",
                             reply_markup=language_keyboard())


@router.message(lambda message: message.text in ['Русский', 'English'])
async def language_choice(message: types.Message):
    session = session_local
    user_id = message.from_user.id
    chosen_language = 'RU' if message.text == 'Русский' else 'ENG'

    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalars().first()

    if user:
        user.language = chosen_language
        await session.commit()

    user_languages[user.telegram_id] = user.language

    await message.answer(phrase_by_user("hello_phrase", user.telegram_id), reply_markup=main_menu_keyboard(chosen_language))

