import json
import logging

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.database.models import User
from bot.utils.consts import user_languages, SessionLocal, STATE_FILE
from bot.utils.keyboards.start_keyboards import main_menu_keyboard, language_keyboard
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.validations import save_execute

router = Router()


@router.message(CommandStart())
@save_execute
async def start_command(session: SessionLocal(), message: types.Message, state: FSMContext):
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
@save_execute
async def language_choice(session: SessionLocal(), message: types.Message):
    user_id = message.from_user.id
    chosen_language = 'RU' if message.text == 'Русский' else 'ENG'

    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalars().first()

    if user:
        user.language = chosen_language
        await session.commit()

    user_languages[user.telegram_id] = user.language

    await message.answer(phrase_by_user("hello_phrase", user.telegram_id), reply_markup=main_menu_keyboard(chosen_language))


async def handle_first_message(message: types.Message, storage: FSMContext):
    try:
        user_id = message.from_user.id
        user_key = f"user:{user_id}"

        # Загрузка данных из JSON
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            all_states = json.load(file)

        # Идентификация пользователя и получение состояния
        user_data = all_states.get(user_key, {})
        user_state = user_data.get("state").replace(":", ".")
        user_language = user_data.get("language")

        # Установка состояния из JSON, если оно указано
        if user_state:
            await storage.set_state(state=user_state)
            await message.answer(f"Ваше состояние восстановлено: {user_state} (язык: {user_language})")
        else:
            await message.answer(f"У вас нет активного состояния. (язык: {user_language})")
    except FileNotFoundError:
        await message.answer("Файл с состояниями не найден.")
    except Exception as e:
        logging.error(f"Ошибка при обработке состояния: {e}")
