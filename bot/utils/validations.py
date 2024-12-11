import re

from sqlalchemy.ext.asyncio.session import AsyncSession

from bot.utils.consts import stablecoins, fundamental_tokens
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user


async def validate_user_input(user_coin_name, message, state):
    """
    Проверяет введенный пользователем токен и выполняет соответствующие действия.
    """

    user_coin_name = user_coin_name.upper().replace(" ", "")

    # Проверка на команду выхода
    if user_coin_name.lower() == "/exit":
        await message.answer(phrase_by_user("calculations_end", message.from_user.id))
        await state.clear()
        return True

    # Проверка на стейблкоин
    if user_coin_name in stablecoins:
        await message.answer(phrase_by_user("stablecoins_answer", message.from_user.id))
        return True

    # Проверка на фундаментальный токен
    if user_coin_name in fundamental_tokens:
        await message.answer(phrase_by_user("fundamental_tokens_answer", message.from_user.id))
        return True

    return False


def format_number(value):
    """Функция для округления числа до 2 знаков после запятой и преобразования в строку."""
    if value is None:
        return "-"
    try:
        return "{:.2f}".format(round(value, 6))
    except (TypeError, ValueError):
        return "-"


def extract_overall_category(category_answer: str) -> str:
    """
    Функция для извлечения общей категории проекта из строки ответа.
    Находит текст в кавычках после "Общая категория проекта:".
    """

    match = re.search(r'Общая категория проекта:\s*"([^"]+)"', category_answer)
    return match.group(1) if match else "Неизвестная категория"


def is_async_session(session):
    return isinstance(session, AsyncSession)


def if_exist_instance(instance, field):
    return instance and len(instance) > 1 and isinstance(instance[1], list) and len(
        instance[1]) > 0 and field is not None
