from bot.database.db_operations import get_user_from_redis_or_db
from bot.utils.common.sessions import redis_client
from bot.utils.resources.bot_phrases.bot_phrase_strings import phrase_dict
from bot.utils.resources.exceptions.exceptions import PlaceholderMissingError


async def phrase_by_user(phrase_id: str, user_id: int, session, **kwargs):
    """
    Функция, которая возвращает необходимую строку из словаря phrase_dict по ключу phrase_id,
    на соответствующем языке пользователя (user_id).
    Если языка нет в Redis, он будет получен из базы данных и сохранён в Redis.
    """

    # Попытка получить язык пользователя из Redis
    user_language = await redis_client.hget(f"user:{user_id}", "language")

    if not user_language:  # Если язык не найден в Redis, пробуем в БД
        user_data = await get_user_from_redis_or_db(user_id, session)
        if user_data:
            user_language = user_data.language
            if user_language:
                # Сохраняем в Redis для будущих запросов
                await redis_client.hset(f"user:{user_id}", "language", user_language)

    if not user_language:  # Если язык все равно не найден
        user_language = "ENG"  # По умолчанию, если язык не найден

    phrase = phrase_dict.get(user_language, {}).get(phrase_id)

    if phrase and kwargs:
        try:
            phrase = phrase.format(**kwargs)
        except KeyError as e:
            raise PlaceholderMissingError(phrase_id, e.args[0])

    return phrase


def phrase_by_language(phrase_id: str, language: str, **kwargs):
    """
    Функция, которая возвращает необходимую строку из словаря phrase_dict по ключу phrase_id,
    на соответствующем языке (language)
    """

    phrase = phrase_dict.get(language, {}).get(phrase_id)

    if phrase and kwargs:
        try:
            phrase = phrase.format(**kwargs)
        except KeyError as e:
            raise PlaceholderMissingError(phrase_id, e.args[0])

    return phrase
