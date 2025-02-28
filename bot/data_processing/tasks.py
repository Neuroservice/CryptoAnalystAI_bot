import asyncio
import datetime
import logging

from bot.data_processing.data_update import (
    fetch_crypto_data,
    update_agent_answers,
)
from bot.database.backups import create_backup
from bot.database.db_operations import get_or_create, update_or_create_token
from bot.database.models import Category
from bot.utils.common.consts import (
    START_TITLE_FOR_GARBAGE_CATEGORIES,
    END_TITLE_FOR_GARBAGE_CATEGORIES,
    START_TITLE_FOR_STABLECOINS,
    END_TITLE_FOR_STABLECOINS,
    START_TITLE_FOR_SCAM_TOKENS,
    START_TITLE_FOR_FUNDAMENTAL,
    END_TITLE_FOR_FUNDAMENTAL,
)
from bot.utils.project_data import fetch_categories, fetch_top_tokens
from bot.utils.resources.files_worker.google_doc import (
    load_document_for_garbage_list,
)


async def parse_periodically(session):
    """
    Запускает обновление данных каждые 6 часов и обновление ответов агентов в 3:00 ночи.
    """
    logging.info("Запущен процесс периодического обновления данных.")

    # Немедленное обновление данных при старте
    try:
        logging.info(
            "Первый запуск: немедленное обновление данных о криптовалютах."
        )
        await fetch_crypto_data(session)
        logging.info("Первичное обновление данных выполнено успешно.")
    except Exception as e:
        logging.error(f"Ошибка первичного обновления данных: {e}")

    while True:
        current_time = datetime.datetime.now(datetime.timezone.utc)

        # Вычисляем время следующего запуска обновления данных
        next_fetch_run = current_time + datetime.timedelta(
            hours=6 - (current_time.hour % 6)
        )
        next_fetch_run = next_fetch_run.replace(
            minute=0, second=0, microsecond=0
        )
        time_until_fetch = (next_fetch_run - current_time).total_seconds()

        # Вычисляем время следующего обновления ответов агентов (в 3:00 ночи)
        next_agent_run = current_time.replace(
            hour=3, minute=0, second=0, microsecond=0
        )
        if current_time >= next_agent_run:
            next_agent_run += datetime.timedelta(days=1)
        time_until_agent = (next_agent_run - current_time).total_seconds()

        # Определяем, что выполнять первым
        if time_until_fetch <= time_until_agent:
            logging.info(
                f"Следующее обновление данных через {time_until_fetch // 3600:.2f} часов."
            )
            await asyncio.sleep(max(time_until_fetch, 1))  # Избегаем sleep(0)
            try:
                logging.info("Запуск обновления данных о криптовалютах...")
                await fetch_crypto_data(session)
                logging.info("Обновление данных завершено.")
            except Exception as e:
                logging.error(f"Ошибка обновления данных: {e}")
        else:
            logging.info(
                f"Следующее обновление ответов агентов через {time_until_agent // 3600:.2f} часов."
            )
            await asyncio.sleep(max(time_until_agent, 1))  # Избегаем sleep(0)
            try:
                logging.info("Запуск обновления данных и ответов агентов...")
                await asyncio.gather(
                    fetch_crypto_data(session),
                    update_agent_answers(),
                )
                logging.info("Все задачи выполнены успешно.")
            except Exception as e:
                logging.error(f"Ошибка при выполнении обновления: {e}")


async def parse_categories_weekly():
    """
    Еженедельно парсит категории криптовалют и сохраняет только не-мусорные категории.
    """
    while True:
        logging.info("Запуск еженедельного обновления категорий...")
        try:
            all_categories = await fetch_categories()
            garbage_categories = load_document_for_garbage_list(
                START_TITLE_FOR_GARBAGE_CATEGORIES,
                END_TITLE_FOR_GARBAGE_CATEGORIES,
            )

            valid_categories = [
                category
                for category in all_categories
                if category not in garbage_categories
            ]

            for category in valid_categories:
                await get_or_create(Category, category_name=category)

            logging.info("Обновление категорий завершено.")
        except Exception as e:
            logging.error(f"Ошибка при обновлении категорий: {e}")

        # Ожидание 7 дней
        await asyncio.sleep(7 * 24 * 60 * 60)


async def parse_tokens_weekly():
    """
    Еженедельно парсит топ-1000 токенов CoinMarketCap, исключая стейблкоины и скам-токены.
    Обновляет поле cmc_rank, если токен с данным символом уже существует в базе,
    иначе создаёт новую запись.
    """
    while True:
        logging.info("Запуск еженедельного обновления списка токенов...")
        try:
            all_tokens = await fetch_top_tokens(limit=1300)

            stablecoins = set(
                load_document_for_garbage_list(
                    START_TITLE_FOR_STABLECOINS, END_TITLE_FOR_STABLECOINS
                )
            )
            fundamental = set(
                load_document_for_garbage_list(
                    START_TITLE_FOR_FUNDAMENTAL, END_TITLE_FOR_FUNDAMENTAL
                )
            )
            scam_tokens = set(
                load_document_for_garbage_list(START_TITLE_FOR_SCAM_TOKENS)
            )

            # Исключаем мусорные токены
            filtered_tokens = [
                token
                for token in all_tokens
                if token["symbol"] not in stablecoins
                and token["symbol"] not in fundamental
                and token["symbol"] not in scam_tokens
            ]
            # Проверяем, хватает ли 1000 токенов
            if len(filtered_tokens) < 1000:
                remaining_tokens = [
                    token
                    for token in all_tokens
                    if token not in filtered_tokens
                ][: 1000 - len(filtered_tokens)]
                filtered_tokens.extend(remaining_tokens)

            # Оставляем ровно 1000 токенов
            top_1000_tokens = filtered_tokens[:1000]

            for token in top_1000_tokens:
                await update_or_create_token(token_data=token)

            logging.info(
                "Обновление списка токенов завершено. В базе 1000 отфильтрованных токенов."
            )
        except Exception as e:
            logging.error(f"Ошибка при обновлении списка токенов: {e}")

        # Ожидание 7 дней
        await asyncio.sleep(7 * 24 * 60 * 60)


async def backup_database():
    """Создаёт бэкап базы данных каждый день."""
    while True:
        try:
            await create_backup()
            logging.info(f"Бэкап создан")
        except Exception as e:
            logging.error(f"Ошибка при создании бэкапа: {e}")

        await asyncio.sleep(60 * 60 * 24)
