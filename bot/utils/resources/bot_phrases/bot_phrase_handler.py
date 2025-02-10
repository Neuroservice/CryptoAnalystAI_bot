from typing import Optional

from bot.database.db_operations import get_user_from_redis_or_db
from bot.utils.resources.bot_phrases.bot_phrase_strings import phrase_dict
from bot.utils.resources.exceptions.exceptions import PlaceholderMissingError


async def phrase_by_user(
        phrase_id: str,
        user_id: int,
        session,
        language: Optional[str] = None,
        **kwargs
) -> str:
    """
    Функция возвращает строку из словаря phrase_dict по ключу phrase_id на нужном языке.
    Если параметр language не передан, функция пытается получить язык пользователя через Redis (а при отсутствии – через БД).

    Если язык уже известен, его можно передать в параметре language, чтобы избежать лишних запросов.
    """

    if language is None:
        user_data = await get_user_from_redis_or_db(user_id, session)
        if user_data and hasattr(user_data, 'language'):
            language = user_data.language
        else:
            language = "ENG"

    phrase = phrase_dict.get(language, {}).get(phrase_id)

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
