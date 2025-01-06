import re
import logging

from sqlalchemy.ext.asyncio.session import AsyncSession

from bot.utils.consts import stablecoins, fundamental_tokens
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user


def save_execute(f):
    async def wrapper(session, *args, **kwargs):
        try:
            return await f(session, *args, **kwargs)
        except Exception as e:
            if hasattr(session, 'rollback'):
                await session.rollback()
            logging.error(e)

    return wrapper


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


def extract_description(topic: str) -> str:
    """
    Функция для извлечения описания проекта.
    """

    match = re.search(r'Описание проекта:\s*"([^"]+)"', topic)
    return match.group(1) if match else "Нет описания"


def extract_red_green_flags(answer: str, language: str) -> str:
    """
    Функция для извлечения ред и грин флагов на русском и английском языках.
    """
    if language == "RU":
        # Регулярное выражение для извлечения положительных характеристик
        positive_pattern = r'(Положительные характеристики:.*?)(?=\s*Отрицательные характеристики|$)'
        # Регулярное выражение для извлечения отрицательных характеристик до "Данные для анализа"
        negative_pattern = r'(Отрицательные характеристики:.*?)(?=\s*Данные для анализа|$)'
        positive_label = "Отрицательные характеристики:"
        negative_label = "Данные для анализа"
    else:  # Предполагается, что язык - английский
        # Регулярное выражение для извлечения положительных характеристик
        positive_pattern = r'(Positive Characteristics:.*?)(?=\s*Negative Characteristics|$)'
        # Регулярное выражение для извлечения отрицательных характеристик до "Data to analyze"
        negative_pattern = r'(Negative Characteristics:.*?)(?=\s*Data to analyze|$)'
        positive_label = "Negative Characteristics:"
        negative_label = "Data to analyze"

    # Извлекаем положительные характеристики
    positive_match = re.search(positive_pattern, answer, re.S)
    positive_text = positive_match.group(1) if positive_match else "Нет 'грин' флагов" if language == "RU" else "No 'green' flags"

    # Извлекаем отрицательные характеристики
    negative_match = re.search(negative_pattern, answer, re.S)
    negative_text = negative_match.group(1) if negative_match else "Нет 'ред' флагов" if language == "RU" else "No 'red' flags"

    # Возвращаем объединенные результаты
    return f"{positive_text}\n\n{negative_text}"


def extract_calculations(answer, language):
    """
    Функция для извлечения описания проекта без заголовка.
    """
    print(f"language {language} answer !!!!!! {answer}")

    if language == "ENG":
        pattern = r'Data for tokenomic analysis:\s*'
    else:
        pattern = r'Данные для анализа токеномики:\s*'

    # Удаляем заголовок и пробел после него
    answer = re.sub(pattern, '', answer, count=1)

    # Ищем расчёты с учетом языка
    if language == "ENG":
        match = re.search(r'(Calculation results for.*?)$', answer, re.DOTALL)
    else:
        match = re.search(r'(Результаты расчета для.*?)$', answer, re.DOTALL)

    if match:
        extracted_text = match.group(1)
        lines = extracted_text.split('\n')

        for i in range(1, len(lines)):
            if (language == "ENG" and lines[i].startswith('Calculation results for')) or \
               (language != "ENG" and lines[i].startswith('Результаты расчета для')):
                lines[i] = '\n' + lines[i]

        return '\n'.join(lines)

    return "Нет данных" if language == "RU" else "No data"


def is_async_session(session):
    return isinstance(session, AsyncSession)


def if_exist_instance(instance, field):
    return instance and len(instance) > 1 and isinstance(instance[1], list) and len(
        instance[1]) > 0 and field is not None
