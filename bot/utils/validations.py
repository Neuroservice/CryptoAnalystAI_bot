import re
import logging

from aiogram import types
from typing import Any, Optional, Callable
from aiogram.fsm.context import FSMContext

from bot.utils.common.sessions import redis_client
from bot.utils.resources.files_worker.google_doc import load_document_for_garbage_list
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user, phrase_by_language
from bot.utils.common.consts import (
    OVERALL_PROJECT_CATEGORY_PATTERN,
    PROJECT_DESCRIPTION_PATTERN,
    POSITIVE_PATTERN_RU,
    NEGATIVE_PATTERN_RU,
    POSITIVE_PATTERN_ENG,
    NEGATIVE_PATTERN_ENG,
    TOKENOMICS_PATTERN_ENG,
    TOKENOMICS_PATTERN_RU,
    COMPARISON_PATTERN_ENG,
    COMPARISON_PATTERN_RU,
    CALCULATIONS_PATTERN_ENG,
    CALCULATIONS_PATTERN_RU,
    METRICS_MAPPING,
    NO_DATA_TEXT,
    CATEGORY_MAP,
    MAX_MESSAGE_LENGTH,
    START_TITLE_FOR_STABLECOINS,
    END_TITLE_FOR_STABLECOINS,
    START_TITLE_FOR_SCAM_TOKENS,
    START_TITLE_FOR_FUNDAMENTAL,
    END_TITLE_FOR_FUNDAMENTAL,
)
from bot.utils.resources.exceptions.exceptions import (
    ExceptionError,
    ValueProcessingError,
    MissingKeyError,
    AttributeAccessError,
)


async def validate_user_input(user_coin_name: str, message: types.Message, state: FSMContext):
    """
    Проверяет введенный пользователем токен и выполняет соответствующие действия.
    """

    user_coin_name = user_coin_name.upper().replace(" ", "")
    stablecoins = load_document_for_garbage_list(START_TITLE_FOR_STABLECOINS, END_TITLE_FOR_STABLECOINS)
    scam_tokens = load_document_for_garbage_list(START_TITLE_FOR_SCAM_TOKENS)
    fundamental_tokens = load_document_for_garbage_list(START_TITLE_FOR_FUNDAMENTAL, END_TITLE_FOR_FUNDAMENTAL)

    # Проверка на команду выхода
    if user_coin_name.lower() == "/exit":
        await state.clear()
        return await phrase_by_user("calculations_end", message.from_user.id)

    # Проверка на стейблкоин
    if user_coin_name in stablecoins:
        return await phrase_by_user("stablecoins_answer", message.from_user.id)

    # Проверка на фундаментальный токен
    if user_coin_name in fundamental_tokens:
        return await phrase_by_user("fundamental_tokens_answer", message.from_user.id)

    # Проверка на скам-токен
    if user_coin_name in scam_tokens:
        return await phrase_by_user("scam_tokens_answer", message.from_user.id)

    return False


def extract_overall_category(category_answer: str) -> str:
    """
    Функция для извлечения общей категории проекта из строки ответа.
    Находит текст в кавычках после "Общая категория проекта:".
    """

    match = re.search(OVERALL_PROJECT_CATEGORY_PATTERN, category_answer)
    return match.group(1) if match else "Неизвестная категория"


def extract_description(topic: str, language: str) -> str:
    """
    Функция для извлечения описания проекта.
    """

    match = re.search(PROJECT_DESCRIPTION_PATTERN, topic, re.DOTALL)
    return match.group(1) if match else phrase_by_language("no_green_flags", language)


def extract_red_green_flags(answer: str, language: str) -> str:
    """
    Функция для извлечения ред и грин флагов на русском и английском языках.
    """

    positive_pattern = POSITIVE_PATTERN_ENG
    negative_pattern = NEGATIVE_PATTERN_ENG

    if language == "RU":
        positive_pattern = POSITIVE_PATTERN_RU
        negative_pattern = NEGATIVE_PATTERN_RU

    # Извлекаем положительные характеристики
    positive_match = re.search(positive_pattern, answer, re.S)
    positive_text = positive_match.group(1) if positive_match else phrase_by_language("no_green_flags", language)

    # Извлекаем отрицательные характеристики
    negative_match = re.search(negative_pattern, answer, re.S)
    negative_text = negative_match.group(1) if negative_match else phrase_by_language("no_red_flags", language)

    # Возвращаем объединенные результаты
    return f"{positive_text}\n{negative_text}"


def extract_calculations(answer: str, language: str):
    """
    Функция для извлечения описания проекта без заголовка.
    """

    if language == "ENG":
        pattern = TOKENOMICS_PATTERN_ENG
    else:
        pattern = TOKENOMICS_PATTERN_RU

    # Удаляем заголовок и пробел после него
    answer = re.sub(pattern, "", answer, count=1)

    # Ищем расчёты с учетом языка
    if language == "ENG":
        match = re.search(CALCULATIONS_PATTERN_ENG, answer, re.DOTALL)
    else:
        match = re.search(CALCULATIONS_PATTERN_RU, answer, re.DOTALL)

    if match:
        extracted_text = match.group(1)
        lines = extracted_text.split("\n")

        for i in range(1, len(lines)):
            if (language == "ENG" and lines[i].startswith("Calculation results for")) or (
                language != "ENG" and lines[i].startswith("Результаты расчета для")
            ):
                lines[i] = "\n" + lines[i]

        return "\n".join(lines)

    return phrase_by_language("no_data", language)


def extract_old_calculations(answer: str, language: str):
    """
    Функция для извлечения описания проекта без заголовка.
    """

    if language == "ENG":
        comparison_pattern = COMPARISON_PATTERN_RU
    else:
        comparison_pattern = COMPARISON_PATTERN_ENG

    # Удаляем заголовок и пробел после него
    answer = re.sub(comparison_pattern, "", answer, count=1)

    # Ищем расчёты с учетом языка
    match = re.search(CALCULATIONS_PATTERN_ENG, answer, re.DOTALL)
    if language == "RU":
        match = re.search(CALCULATIONS_PATTERN_RU, answer, re.DOTALL)

    if match:
        extracted_text = match.group(1)
        lines = extracted_text.split("\n")

        for i in range(1, len(lines)):
            if (language == "ENG" and lines[i].startswith("Calculation results for")) or (
                language != "ENG" and lines[i].startswith("Результаты расчета для")
            ):
                lines[i] = "\n" + lines[i]

        return "\n".join(lines)

    return answer


# Функция для форматирования метрик
def format_metric(metric_key: str, value: str, language: str, extra=""):
    """
    Форматирует строку для метрики.
    """

    if value and value != "N/A":
        return f"- {METRICS_MAPPING[metric_key][language]}{extra}: {value}"
    else:
        return f"- {METRICS_MAPPING[metric_key][language]}: {NO_DATA_TEXT[language]}"


def clean_fundraise_data(fundraise_str: str):
    """
    Преобразует текстовую информацию о фандрейзе в числовой формат.
    """

    try:
        clean_str = fundraise_str.replace("$", "").strip()
        parts = clean_str.split()
        amount = 1

        for part in parts:
            clean_part = part

            if clean_part[-1] in ["B", "M", "K"]:
                suffix = clean_part[-1]
                if suffix == "B":
                    amount = float(clean_part[:-1])
                    amount *= 1e9
                elif suffix == "M":
                    amount = float(clean_part[:-1])
                    amount *= 1e6
                elif suffix == "K":
                    amount = float(clean_part[:-1])
                    amount *= 1e3

            amount = float(amount)

        return amount
    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


def clean_twitter_subs(twitter_subs: str):
    """
    Преобразует текстовую информацию о подписчиках в числовой формат.
    """

    try:
        # Если входное значение уже является числом, возвращаем его
        if isinstance(twitter_subs, (int, float)):
            return float(twitter_subs)

        # Удаляем символы и обрабатываем строку
        clean_str = twitter_subs.strip()
        parts = clean_str.split()
        amount = 1

        for part in parts:
            clean_part = part

            if clean_part[-1] in ["B", "M", "K"]:
                suffix = clean_part[-1]
                if suffix == "B":
                    amount = float(clean_part[:-1]) * 1e9
                elif suffix == "M":
                    amount = float(clean_part[:-1]) * 1e6
                elif suffix == "K":
                    amount = float(clean_part[:-1]) * 1e3
            else:
                amount = float(clean_part)

        return amount

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


def extract_tokenomics(data: str):
    """
    Извлекает данные о распределении токенов из текста.
    """

    tokenomics_data = []
    clean_data = data.replace("\n", "").replace("\r", "").strip()
    entries = re.split(r"\)\s*", clean_data)

    for entry in entries:
        if entry:
            tokenomics_data.append(entry.strip() + ")")

    return tokenomics_data


def standardize_category(overall_category: str) -> str:
    """
    Преобразование общей категории в соответствующее английское название.
    """

    return CATEGORY_MAP.get(overall_category, "Unknown Category")


def process_metric(value: Any, default=0.0):
    """
    Проверяет значение на наличие 'N/A' или неподходящего типа,
    и возвращает преобразованное значение (float) или значение по умолчанию.

    :param value: Входное значение для проверки.
    :param default: Значение по умолчанию, если проверка не пройдена.
    :return: Преобразованное значение (float) или default.
    """
    if value == "N/A" or not isinstance(value, (int, float)):
        return default
    return float(value)


def split_long_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """
    Разбивает длинный текст на части, если он превышает заданный лимит длины.
    """
    parts = []
    while text:
        part = text[:max_length]
        parts.append(part)
        text = text[max_length:]
    return parts


def get_metric_value(
    obj: Any,
    attr_chain: Optional[str] = None,
    fallback: Any = "N/A",
    transform: Optional[Callable[[Any], Any]] = None,
):
    """
    Получение поля из базы данных по таблице
    """
    try:
        if obj is None:
            return fallback
        # Проходим по цепочке атрибутов
        value = obj
        if attr_chain:
            for attr in attr_chain.split("."):
                value = getattr(value, attr, None)
                if value is None:
                    return fallback
        # Применяем преобразование, если указано
        return transform(value) if transform else value
    except (TypeError, ValueError, ZeroDivisionError, AttributeError):
        return fallback


async def check_redis_connection():
    """
    Проверяет подключение к Redis.
    """
    try:
        await redis_client.ping()
        logging.info("Подключение к Redis успешно!")
    except ConnectionError:
        logging.error("Не удалось подключиться к Redis!")
        raise Exception("Не удалось подключиться к Redis!")


def is_float(value: str) -> bool:
    try:
        float(value.replace(",", "."))
        return True
    except ValueError:
        return False


def is_int(value: str) -> bool:
    return value.isdigit()


def normalize_float(value: str) -> float:
    return float(value.replace(",", "."))


def is_percentage(value: str) -> bool:
    return bool(re.match(r"^\d+(\.\d+)?%?$", value.strip().replace(",", ".")))


def is_valid_number_with_suffix(value: str) -> bool:
    """
    Проверяет, что строка:
    1) Может содержать цифры, точки, запятые.
    2) Опционально заканчивается на K, M или B (в любом регистре).
    3) Не содержит других букв/символов.

    Примеры валидных:
      "123" -> True
      "42.5" -> True
      "10,500" -> True
      "1.2M"  -> True
      "950k"  -> True
      "3,2B"  -> True (хотя 3,2 не совсем стандарт, но по условию допустим)
    Примеры невалидных:
      "abc", "12X", "??" -> False
    """
    s = value.strip()
    if not s:
        return False

    s_upper = s.upper()

    suffix = ""
    if s_upper[-1] in ("K", "M", "B"):
        suffix = s_upper[-1]
        s_upper = s_upper[:-1]
        if not s_upper:
            return False

    for ch in s_upper:
        if ch not in "0123456789.,":
            return False

    digits_found = any(ch.isdigit() for ch in s_upper)
    if not digits_found:
        return False

    return True


def is_valid_investors_format(text: str) -> bool:
    pattern = r"^[^()]+\(Tier: \d+\)(,\s*[^()]+\(Tier: \d+\))*$"
    return re.match(pattern, text.strip()) is not None


def is_valid_distribution_format(text: str) -> bool:
    pattern = r"^([\w &]+\(\d+%\))(,\s*[\w &]+\(\d+%\))*$"
    return re.match(pattern, text.strip()) is not None


def parse_general_number(text: str) -> float:
    """
    Парсит строку вида:
      - '930B' => 9.30e11
      - '450M' => 4.50e8
      - '63K'  => 6.30e4
      - '10,534,000' => 10534000
      - '4.2B' => 4.2e9
      - '450' (обычное число)
    Если строка невалидна, выкидывает ValueError.
    """
    # Убираем запятые и пробелы
    s = text.strip().replace(",", "")
    if not s:
        raise ValueError("Пустая строка")

    # Проверяем последний символ на K / M / B
    suffix = s[-1].upper()  # последний символ в верхнем регистре
    if suffix in ["K", "M", "B"]:
        numeric_part = s[:-1]  # без последнего символа
        val = float(numeric_part)
        if suffix == "K":
            return val * 1e3
        elif suffix == "M":
            return val * 1e6
        else:  # suffix == "B"
            return val * 1e9
    else:
        # Если никакой суффикс (или, например, число "1234.56"), просто парсим
        return float(s)


def is_general_number_or_dash(text: str) -> bool:
    """
    Проверяет, что text == '-' (нет данных)
    ИЛИ корректно парсится функцией parse_general_number.
    """
    text = text.strip()
    if text == "-":
        return True
    try:
        parse_general_number(text)
        return True
    except ValueError:
        return False


def parse_general_number_or_none(text: str) -> float | None:
    """
    Если text == '-', возвращаем None.
    Иначе парсим через parse_general_number.
    """
    text = text.strip()
    if text == "-":
        return None
    return parse_general_number(text)
