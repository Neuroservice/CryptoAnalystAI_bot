import logging

from aiogram import Router, types
from aiogram.filters import Command

from bot.database.models import User
from bot.utils.common.sessions import redis_client
from bot.utils.keyboards.start_keyboards import main_menu_keyboard
from bot.utils.resources.exceptions.exceptions import ExceptionError
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.database.db_operations import (
    get_user_from_redis_or_db,
    update_or_create,
    create,
    get_one,
)

change_language_router = Router()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@change_language_router.message(Command("language"))
async def change_language(message: types.Message):
    """
    Хендлер для обработки команды '/language'.
    Изменяет язык пользователя 'противоположный' (был RU, станет ENG) и загружает клавиатуру пунктов меню на
    новом языке.
    """

    user_id = message.from_user.id

    try:
        user_data = await get_user_from_redis_or_db(user_id)
        new_language = "ENG" if user_data.get("language") == "RU" else "RU"

        user = await get_one(User, telegram_id=user_id)

        if user:
            await update_or_create(User, id=user.id, defaults={"language": new_language})
        else:
            await create(User, telegram_id=user_id, language=new_language)

        await redis_client.hset(f"user:{user_id}", "language", new_language)

        new_keyboard = await main_menu_keyboard(user_id)

        await message.answer(
            await phrase_by_user(
                "language_changed",
                user_id,
                language=new_language,
            ),
            reply_markup=new_keyboard,
        )

    except Exception as e:
        logging.error(f"Ошибка при смене языка: {e}")
        raise ExceptionError(str(e))
