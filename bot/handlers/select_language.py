import logging

from aiogram import Router, types
from aiogram.filters import Command

from bot.database.db_operations import get_user_from_redis_or_db
from bot.utils.keyboards.start_keyboards import main_menu_keyboard
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.resources.exceptions.exceptions import ExceptionError
from bot.utils.common.sessions import session_local, redis_client

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
        user = await get_user_from_redis_or_db(user_id, session_local)

        # Меняем язык на противоположный
        print(user, user.language)
        new_language = 'ENG' if user.language == 'RU' else 'RU'
        user.language = new_language

        await session_local.merge(user)
        await session_local.commit()

        # Обновляем язык в Redis
        await redis_client.hset(f"user:{user_id}", "language", new_language)

        # Обновляем клавиатуру с новым языком
        new_keyboard = await main_menu_keyboard(user_id)

        # Отправляем сообщение с новой клавиатурой
        await message.answer(await phrase_by_user("language_changed", user.telegram_id, session_local),
                             reply_markup=new_keyboard)

    except Exception as e:
        raise ExceptionError(str(e))
