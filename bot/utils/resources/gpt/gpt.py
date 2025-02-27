import logging
import re

import requests
from langchain_openai import ChatOpenAI

from bot.utils.common.config import GPT_SECRET_KEY_FASOLKAAI
from bot.utils.common.consts import DOCUMENT_URL, GPT_MODEL, TEMPERATURE
from bot.utils.resources.gpt.gpt_promts import (
    user_prompt_for_tier_agent,
    user_prompt_for_funds_agent,
    user_prompt_for_project_rating_agent,
    user_prompt_for_flags_agent,
    user_prompt_for_description_agent,
)
from bot.utils.resources.gpt.titles_for_promts import (
    start_title_for_tier_agent,
    end_title_for_tier_agent,
    start_title_for_flags_agent,
    start_title_for_funds_agent,
    end_title_for_funds_agent,
    end_title_for_flags_agent,
    end_title_for_project_rating_agent,
    start_title_for_project_rating_agent,
    end_title_for_description_agent,
    start_title_for_description_agent,
)


def load_document(start_title: str, end_title: str) -> str:
    """
    Загружает текст из документа Google и извлекает текст между указанными заголовками.
    """

    try:
        response = requests.get(DOCUMENT_URL)
        response.raise_for_status()

        # Извлечение текста документа
        full_text = response.text

        # Формирование регулярного выражения для извлечения текста между началом и концом
        pattern = rf"{re.escape(start_title)}(.*?)(?=\n{re.escape(end_title)})"
        match = re.search(pattern, full_text, re.DOTALL)

        extracted_text = match.group(1).strip() if match else "Текст не найден"

        return extracted_text

    except Exception as e:
        logging.error(f"Ошибка при загрузке документа: {e}")
        return "Ошибка загрузки текста"


def load_document_for_description_agent() -> str:
    """
    Загружает текст из документа Google и извлекает текст для промта агента определения категории проекта.
    """

    return load_document(
        start_title_for_description_agent, end_title_for_description_agent
    )


def load_document_for_tier_agent() -> str:
    """
    Загружает текст из документа Google и извлекает текст для промта агента определения тира проекта.
    """

    return load_document(start_title_for_tier_agent, end_title_for_tier_agent)


def load_document_for_funds_agent() -> str:
    """
    Загружает текст из документа Google и извлекает текст для промта агента определения профита инвесторов.
    """

    return load_document(
        start_title_for_funds_agent, end_title_for_funds_agent
    )


def load_document_for_project_rating_agent() -> str:
    """
    Загружает текст из документа Google и извлекает текст для промта агента определения оценки проекта.
    """

    return load_document(
        start_title_for_project_rating_agent,
        end_title_for_project_rating_agent,
    )


def load_document_for_flags_agent() -> str:
    """
    Загружает текст из документа Google и извлекает текст для промта агента определения ред/грин флагов проекта.
    """

    return load_document(
        start_title_for_flags_agent, end_title_for_flags_agent
    )


async def create_agent_response(system_content: str, user_prompt: str) -> str:
    """
    Создает ответ от агента на основе системного сообщения и пользовательского запроса.
    """

    llm = ChatOpenAI(
        api_key=GPT_SECRET_KEY_FASOLKAAI,
        model=GPT_MODEL,
        temperature=TEMPERATURE,
    )
    response = llm.invoke(
        [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]
    )

    return response.content


async def description_agent(topic: str, language: str):
    """
    Обработчик агента определения категории проекта.
    """

    system = load_document_for_description_agent()
    user_prompt = user_prompt_for_description_agent.format(
        language=language, topic=topic
    )

    return await create_agent_response(system, user_prompt)


async def tier_agent(topic: str):
    """
    Обработчик агента определения тира проекта.
    """

    system = load_document_for_tier_agent()
    user_prompt = user_prompt_for_tier_agent.format(topic=topic)
    return await create_agent_response(system, user_prompt)


async def funds_agent(topic: str):
    """
    Обработчик агента определения процента токенов которые относятся инвесторам.
    """

    system = load_document_for_funds_agent()
    user_prompt = user_prompt_for_funds_agent.format(topic=topic)
    return await create_agent_response(system, user_prompt)


async def project_rating_agent(topic: str):
    """
    Обработчик агента определения общего рейтинга проекта.
    """

    system = load_document_for_project_rating_agent()
    user_prompt = user_prompt_for_project_rating_agent.format(topic=topic)
    return await create_agent_response(system, user_prompt)


async def flags_agent(topic: str, language: str):
    """
    Обработчик агента определения ред/грин флагов проекта.
    """

    system = load_document_for_flags_agent()
    user_prompt = user_prompt_for_flags_agent.format(
        language=language, topic=topic
    )
    return await create_agent_response(system, user_prompt)


async def agent_handler(agent_type: str, topic: str, language=None):
    """
    Обработчик для вызова различных агентов в зависимости от типа агента.
    """

    agent_functions = {
        "description": lambda t: description_agent(t, language),
        "tier_agent": tier_agent,
        "funds_agent": funds_agent,
        "rating": project_rating_agent,
        "flags": lambda t: flags_agent(t, language),
    }

    if agent_type not in agent_functions:
        logging.error(f"Неизвестный тип агента: {agent_type}")
        return None

    try:
        return await agent_functions[agent_type](topic)
    except Exception as e:
        logging.error(f"Ошибка при вызове агента {agent_type}: {e}")
        return None
