import logging
import re

import requests
# from openai import OpenAI
from langchain_openai import ChatOpenAI

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
    return load_document("1. Категории крипто проектов и краткое описание", "1. Категории крипто проектов")


def load_document_for_tier_agent() -> str:
    return load_document("2. Тир проекта", "3. Анализ токеномики, сравнение с другими проектами")


def load_document_for_tokemonic_agent() -> str:
    return load_document("3. Анализ токеномики, сравнение с другими проектами",
                         "4. Прибыль фондов + рост/падение + топ 100 кошельков + заблокированные токены (TVL)")


def load_document_for_funds_agent() -> str:
    return load_document("4.1 от 23.12.2024 Определение процента токенов фондов",
                         "5. Агент подсчета общего рейтинга")


def load_document_for_project_rating_agent() -> str:
    return load_document("5. Агент подсчета общего рейтинга", "6. Агент ред флаги и грин флаги")


def load_document_for_flags_agent() -> str:
    return load_document("7. Новый промт агента ред флаги и грин флаги",
                         "Примечание, весы (не обращай внимание):")


def create_agent_response(system_content: str, user_prompt: str) -> str:
    """Создает ответ от агента на основе системного сообщения и пользовательского запроса."""
    llm = ChatOpenAI(api_key=GPT_SECRET_KEY_FASOLKAAI, model="gpt-4o-mini-2024-07-18", temperature=0)
    response = llm.invoke([{"role": "system", "content": system_content},
                           {"role": "user", "content": user_prompt}])
    return response.content


def category_agent(topic, language):
    system = load_document_for_category_agent()
    user_prompt = f"Определи к какой категории относится данный проект. Текстовое описание предоставь на языке пользователя: {language}\nВот текстовое описание проекта: {topic}"
    return create_agent_response(system, user_prompt)


def tier_agent(topic):
    system = load_document_for_tier_agent()
    user_prompt = f"Определи к какому Тиру относится проект.\nВот критерии для оценки: {topic}"
    return create_agent_response(system, user_prompt)


def tokemonic_agent(topic):
    system = load_document_for_tokemonic_agent()
    user_prompt = (f"Сравни криптопроект с другими проектами в той же категории и рассчитай его оценку "
                   f"в баллах на основе возможного прироста токена по сравнению с этими проектами.\n"
                   f"Переменные для вычислений: {topic}")
    return create_agent_response(system, user_prompt)


def funds_agent(topic):
    system = load_document_for_funds_agent()
    user_prompt = (f"Вычисли процент, который получают 'инвесторы'"
                   f"и предоставь результаты в заданном в инструкции формате.\n"
                   f"Распределение токенов для анализа: {topic}")
    return create_agent_response(system, user_prompt)


def project_rating_agent(topic):
    system = load_document_for_project_rating_agent()
    user_prompt = (f"Рассчитай общее количество баллов для криптопроекта на основе предоставленных переменных "
                   f"и предоставь результаты в заданном в инструкции формате.\n"
                   f"Переменные для вычислений: {topic}")
    return create_agent_response(system, user_prompt)


def flags_agent(topic, language):
    system = load_document_for_flags_agent()
    user_prompt = (f"Ответь на языке: {language}. Не упоминай о том, что тебя попросили ответить на конкретном языке.\n"
                   f"Переменные для анализа: {topic}")
    return create_agent_response(system, user_prompt)


def agent_handler(agent_type, topic, language=None):
    """Обработчик для вызова различных агентов в зависимости от типа агента."""
    agent_functions = {
        "category": lambda t: category_agent(t, language),
        "tier_agent": tier_agent,
        "tokemonic_agent": tokemonic_agent,
        "funds_agent": funds_agent,
        "rating": project_rating_agent,
        "flags": lambda t: flags_agent(t, language),
    }

    if agent_type not in agent_functions:
        logging.error(f"Неизвестный тип агента: {agent_type}")
        return None

    try:
        return agent_functions[agent_type](topic)
    except Exception as e:
        logging.error(f"Ошибка при вызове агента {agent_type}: {e}")
        return None
