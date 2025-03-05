import re
import requests

from bot.utils.common.consts import (
    DOCUMENT_GARBAGE_LIST_URL,
    PATTERN_FOR_GARBAGE_LIST_WITHOUT_END_TITLE,
    PATTERN_FOR_GARBAGE_LIST_WITH_END_TITLE,
)


def load_document_for_garbage_list(start_title: str = None, end_title: str = None):
    """
    Загружает список мусорных категорий, стейблкоинов и т.д., в зависимости от передающихся заголовков.
    """

    try:
        # Получение содержимого документа в текстовом формате
        response = requests.get(DOCUMENT_GARBAGE_LIST_URL)
        response.raise_for_status()

        # Извлечение текста документа
        full_text = response.text

        # Формирование регулярного выражения для извлечения текста между заголовками
        pattern = PATTERN_FOR_GARBAGE_LIST_WITHOUT_END_TITLE.format(start_title=re.escape(start_title))
        if end_title:
            pattern = PATTERN_FOR_GARBAGE_LIST_WITH_END_TITLE.format(
                start_title=re.escape(start_title),
                end_title=re.escape(end_title),
            )

        match = re.search(pattern, full_text, re.DOTALL)

        if not match:
            print("Не удалось найти текст между заголовками.")
            return []

        extracted_text = match.group(1).strip()

        # Формирование списка категорий (по строкам)
        categories = [line.strip() for line in extracted_text.split("\n") if line.strip()]
        return categories

    except requests.RequestException as e:
        print(f"Ошибка при загрузке документа: {e}")
        return []
    except Exception as e:
        print(f"Ошибка обработки документа: {e}")
        return []
