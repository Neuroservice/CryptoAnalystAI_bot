import logging
import re
import requests

from openai import OpenAI
from bs4 import BeautifulSoup

from bot.config import GPT_SECRET_KEY_FASOLKAAI


def load_document_for_category_agent() -> str:
    document_id = '1_NHFo4b4FmWNxZn6ycQsjm_KaWGdG-mHp6SGCjtPvgI'
    url = f'https://docs.google.com/document/d/{document_id}/export?format=txt'

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    full_text = soup.get_text()

    match = re.search(r"1\. Категории крипто проектов(.*?)2\. Тир проекта", full_text, re.DOTALL)
    chapter_text = match.group(1).strip() if match else "Раздел не найден"

    logging.info(f"TEXT {chapter_text}")

    return chapter_text


def load_document_for_tier_agent() -> str:
    document_id = '1_NHFo4b4FmWNxZn6ycQsjm_KaWGdG-mHp6SGCjtPvgI'
    url = f'https://docs.google.com/document/d/{document_id}/export?format=txt'

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    full_text = soup.get_text()

    match = re.search(r"2\. Тир проекта(.*?)3\. Анализ токеномики, сравнение с другими проектами", full_text, re.DOTALL)
    chapter_text = match.group(1).strip() if match else "Раздел не найден"

    logging.info(f"TEXT {chapter_text}")

    return chapter_text


def load_document_for_tokemonic_agent() -> str:
    document_id = '1_NHFo4b4FmWNxZn6ycQsjm_KaWGdG-mHp6SGCjtPvgI'
    url = f'https://docs.google.com/document/d/{document_id}/export?format=txt'

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    full_text = soup.get_text()

    match = re.search(
        r"3\. Анализ токеномики, сравнение с другими проектами(.*?)4\. Прибыль фондов \+ рост/падение \+ топ 100 кошельков \+ заблокированные токены \(TVL\)",
        full_text,
        re.DOTALL
    )
    chapter_text = match.group(1).strip() if match else "Раздел не найден"

    logging.info(f"TEXT {chapter_text}")

    return chapter_text


def load_document_for_funds_agent() -> str:
    document_id = '1_NHFo4b4FmWNxZn6ycQsjm_KaWGdG-mHp6SGCjtPvgI'
    url = f'https://docs.google.com/document/d/{document_id}/export?format=txt'

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    full_text = soup.get_text()

    match = re.search(
        r"4\. Прибыль фондов \+ рост/падение \+ топ 100 кошельков \+ заблокированные токены \(TVL\)(.*?)5\. Агент подсчета общего рейтинга",
        full_text,
        re.DOTALL
    )
    chapter_text = match.group(1).strip() if match else "Раздел не найден"

    logging.info(f"TEXT {chapter_text}")

    return chapter_text


def load_document_for_project_rating_agent() -> str:
    document_id = '1_NHFo4b4FmWNxZn6ycQsjm_KaWGdG-mHp6SGCjtPvgI'
    url = f'https://docs.google.com/document/d/{document_id}/export?format=txt'

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    full_text = soup.get_text()

    match = re.search(
        r"5\. Агент подсчета общего рейтинга(.*?)6\. Агент ред флаги и грин флаги",
        full_text,
        re.DOTALL
    )
    chapter_text = match.group(1).strip() if match else "Раздел не найден"

    logging.info(f"TEXT {chapter_text}")

    return chapter_text


def load_document_for_flags_agent() -> str:
    document_id = '1_NHFo4b4FmWNxZn6ycQsjm_KaWGdG-mHp6SGCjtPvgI'
    url = f'https://docs.google.com/document/d/{document_id}/export?format=txt'

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    full_text = soup.get_text()

    match = re.search(
        r"6\. Агент ред флаги и грин флаги(.*?)(?=Примечание, весы \(не обращай внимание\):)",
        full_text,
        re.DOTALL
    )
    chapter_text = match.group(1).strip() if match else "Раздел не найден"

    logging.info(f"TEXT {chapter_text}")

    return chapter_text


def category_agent(topic):
    system = load_document_for_category_agent()
    client = OpenAI(api_key=GPT_SECRET_KEY_FASOLKAAI)
    logging.info(f"topic {topic, system}")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Определи к какой категории относится данный проект.\nВот текстовое описание проекта: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0.1
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
        temperature=0.1
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
        {"role": "user", "content": f"Внимательно следуй инструкции которую тебе дали. Не придумывай ничего от себя. Сравни криптопроект с другими проектами в той же категории и рассчитай его оценку в баллах на основе возможного прироста токена по сравнению с этими проектами. Предоставь результаты в заданном в инструкции формате и ничего более.\nПеременные для вычислений: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0.1
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
        {"role": "user", "content": f"Внимательно следуй инструкции которую тебе дали. Не придумывай ничего от себя. Вычисли количество набранных баллов по каждому показателю и предоставь результаты в заданном в инструкции формате и ничего более.\nПеременные для вычислений: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0.1
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
        {"role": "user", "content": f"Внимательно следуй инструкции которую тебе дали. Не придумывай ничего от себя. Рассчитай общее количество баллов для криптопроекта на основе предоставленных переменных и предоставь результаты в заданном в инструкции формате и ничего более.\nПеременные для вычислений: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0.1
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
        {"role": "user", "content": f"Ответь на языке: {language}. Не упоминай о том, что тебя попросили ответить на конкретном языке. Переменные для анализа: {topic}"}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        temperature=0.1
    )
    answer = completion.choices[0].message.content
    logging.info(f"\n================================\nAnswer: {answer}\n")
    return answer
