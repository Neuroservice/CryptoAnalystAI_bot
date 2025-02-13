from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.utils.keyboards.start_keyboards import (
    main_menu_keyboard,
    language_keyboard,
)
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.database.db_operations import get_user_from_redis_or_db
from bot.utils.common.sessions import session_local, redis_client

start_router = Router()


@start_router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    """
    Хендлер для команды /start. Получает пользователя из Redis, БД или создаёт нового.
    """
    await state.clear()
    user_id = message.from_user.id

    # Получаем пользователя из Redis или базы данных
    user = await get_user_from_redis_or_db(user_id=user_id)

    if user:
        language = user.get("language", "ENG")

        if language:
            await message.answer(
                await phrase_by_user(
                    "hello_phrase", user_id, session_local, language
                ),
                reply_markup=await main_menu_keyboard(user_id=user_id),
            )
        else:
            await message.answer(
                "Please choose your language / Пожалуйста, выберите язык:",
                reply_markup=language_keyboard(),
            )
    else:
        await message.answer(
            "Ошибка при работе с базой данных. Попробуйте позже."
        )


@start_router.message(lambda message: message.text in ["Русский", "English"])
async def language_choice(message: types.Message):
    """
    Хендлер для выбора языка. Сохраняет язык в Redis и базе данных.
    """
    user_id = message.from_user.id
    chosen_language = "RU" if message.text == "Русский" else "ENG"

    # Получаем пользователя из Redis или базы данных
    user = await get_user_from_redis_or_db(user_id=user_id)

    if user:
        # Обновляем Redis
        await redis_client.hset(f"user:{user_id}", "language", chosen_language)

        # Обновляем язык в базе данных
        user.language = chosen_language
        async with session_local() as session:
            await session.commit()

        await message.answer(
            await phrase_by_user("hello_phrase", user_id, session_local),
            reply_markup=await main_menu_keyboard(user_id=user_id),
        )
    else:
        await message.answer(
            "Ошибка при работе с базой данных. Попробуйте позже."
        )
