from bot.utils.common.sessions import redis_client
from bot.utils.resources.buttons.button_strings import button_strings_dict


async def button_text_by_user(button_text_id: str, user_id: int):
    """
    Функция, которая возвращает текст кнопки на основе языка пользователя.
    Извлекает язык пользователя из Redis и использует его для получения текста кнопки.
    """

    user_language = await redis_client.hget(f"user:{user_id}", "language")
    user_language = user_language or 'ENG'

    return button_strings_dict.get(user_language, {}).get(button_text_id)

