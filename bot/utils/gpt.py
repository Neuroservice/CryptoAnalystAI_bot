import logging
import re

import requests
from openai import OpenAI

from bot.config import GPT_SECRET_KEY_FASOLKAAI


def load_document(start_title: str, end_title: str) -> str:
    """Загружает текст из документа Google и извлекает текст между указанными заголовками."""
    document_id = '1_NHFo4b4FmWNxZn6ycQsjm_KaWGdG-mHp6SGCjtPvgI'
    url = f'https://docs.google.com/document/d/{document_id}/export?format=txt'

    try:
        response = requests.get(url)
        response.raise_for_status()

        # Извлечение текста документа
        full_text = response.text

        # Формирование регулярного выражения для извлечения текста между началом и концом
        pattern = rf"{re.escape(start_title)}(.*?)(?=\n{re.escape(end_title)})"
        match = re.search(pattern, full_text, re.DOTALL)

        extracted_text = match.group(1).strip() if match else "Текст не найден"

        logging.info(f"Extracted text: {extracted_text}")
        return extracted_text

    except Exception as e:
        logging.error(f"Ошибка при загрузке документа: {e}")
        return "Ошибка загрузки текста"


def load_document_for_category_agent() -> str:
    return load_document("1. Категории крипто проектов", "2. Тир проекта")


def load_document_for_tier_agent() -> str:
    return load_document("2. Тир проекта", "3. Анализ токеномики, сравнение с другими проектами")


def load_document_for_tokemonic_agent() -> str:
    return load_document("3. Анализ токеномики, сравнение с другими проектами",
                         "4. Прибыль фондов + рост/падение + топ 100 кошельков + заблокированные токены (TVL)")


def load_document_for_funds_agent() -> str:
    return load_document("4. Прибыль фондов + рост/падение + топ 100 кошельков + заблокированные токены (TVL)",
                         "5. Агент подсчета общего рейтинга")


def load_document_for_project_rating_agent() -> str:
    return load_document("5. Агент подсчета общего рейтинга", "6. Агент ред флаги и грин флаги")


def load_document_for_flags_agent() -> str:
    return load_document("6. Агент ред флаги и грин флаги",
                         "Примечание, весы (не обращай внимание):")


def category_agent(topic):
    system = load_document_for_category_agent()
    client = OpenAI(api_key=GPT_SECRET_KEY_FASOLKAAI)
    logging.info(f"topic {topic, system}")
    messages = [
        {"role": "system", "content": system},
        {"role": "user",
         "content": f"Определи к какой категории относится данный проект.\nВот текстовое описание проекта: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0
    )
    answer = completion.choices[0].message.content
    logging.info(f"\n================================\nAnswer: {answer}\n")
    return answer


def tier_agent(topic):
    system = load_document_for_tier_agent()
    client = OpenAI(api_key=GPT_SECRET_KEY_FASOLKAAI)
    logging.info(f"topic {topic, system}")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Определи к какому Тиру относится проект.\nВот критерии для оценки: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0
    )
    answer = completion.choices[0].message.content
    logging.info(f"\n================================\nAnswer: {answer}\n")
    return answer


def tokemonic_agent(topic):
    system = load_document_for_tokemonic_agent()
    client = OpenAI(api_key=GPT_SECRET_KEY_FASOLKAAI)
    logging.info(f"topic {topic, system}")
    messages = [
        {"role": "system", "content": system},
        {"role": "user",
         "content": f"Внимательно следуй инструкции которую тебе дали. Не придумывай ничего от себя. Сравни криптопроект с другими проектами в той же категории и рассчитай его оценку в баллах на основе возможного прироста токена по сравнению с этими проектами. Предоставь результаты в заданном в инструкции формате и ничего более.\nПеременные для вычислений: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0
    )
    answer = completion.choices[0].message.content
    logging.info(f"\n================================\nAnswer: {answer}\n")
    return answer


def funds_agent(topic):
    system = load_document_for_funds_agent()
    client = OpenAI(api_key=GPT_SECRET_KEY_FASOLKAAI)
    logging.info(f"topic {topic, system}")
    messages = [
        {"role": "system", "content": system},
        {"role": "user",
         "content": f"Внимательно следуй инструкции которую тебе дали. Не придумывай ничего от себя. Вычисли количество набранных баллов по каждому показателю и предоставь результаты в заданном в инструкции формате и ничего более.\nПеременные для вычислений: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0
    )
    answer = completion.choices[0].message.content
    logging.info(f"\n================================\nAnswer: {answer}\n")
    return answer


def project_rating_agent(topic):
    system = load_document_for_project_rating_agent()
    client = OpenAI(api_key=GPT_SECRET_KEY_FASOLKAAI)
    logging.info(f"topic {topic, system}")
    messages = [
        {"role": "system", "content": system},
        {"role": "user",
         "content": f"Внимательно следуй инструкции которую тебе дали. Не придумывай ничего от себя. Рассчитай общее количество баллов для криптопроекта на основе предоставленных переменных и предоставь результаты в заданном в инструкции формате и ничего более.\nПеременные для вычислений: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0
    )
    answer = completion.choices[0].message.content
    logging.info(f"\n================================\nAnswer: {answer}\n")
    return answer


def flags_agent(topic, language):
    system = load_document_for_flags_agent()
    client = OpenAI(api_key=GPT_SECRET_KEY_FASOLKAAI)
    logging.info(f"topic {language, topic, system}")
    messages = [
        {"role": "system", "content": system},
        {"role": "user",
         "content": f"Ответь на языке: {language}. Не упоминай о том, что тебя попросили ответить на конкретном языке. Переменные для анализа: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0
    )
    answer = completion.choices[0].message.content
    logging.info(f"\n================================\nAnswer: {answer}\n")
    return answer


def agent_handler(agent_type, topic, language=None):
    """
    Обработчик для вызова различных агентов в зависимости от типа агента.
    """

    # Словарь с функциями для различных агентов
    agent_functions = {
        "category": category_agent,
        "tier_agent": tier_agent,
        "tokemonic_agent": tokemonic_agent,
        "funds_agent": funds_agent,
        "rating": project_rating_agent,
        "flags": lambda topic: flags_agent(topic, language)
    }

    # Проверка, существует ли такой агент
    if agent_type not in agent_functions:
        logging.error(f"Неизвестный тип агента: {agent_type}")
        return None

    # Вызов нужной функции для агента
    try:
        return agent_functions[agent_type](topic)
    except Exception as e:
        logging.error(f"Ошибка при вызове агента {agent_type}: {e}")
        return None
