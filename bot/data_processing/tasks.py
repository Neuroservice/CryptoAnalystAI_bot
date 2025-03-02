import asyncio
import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from bot.data_processing.data_update import (
    fetch_crypto_data,
    update_agent_answers,
)
from bot.database.backups import create_backup
from bot.database.db_operations import get_or_create, update_or_create_token, update_or_create, get_one
from bot.database.models import (
    Category,
    ManipulativeMetrics,
    InvestingMetrics,
    MarketMetrics,
    TopAndBottom,
    BasicMetrics,
    Tokenomics,
    Project,
    NetworkMetrics,
    SocialMetrics,
    FundsProfit,
)
from bot.utils.common.consts import (
    START_TITLE_FOR_GARBAGE_CATEGORIES,
    END_TITLE_FOR_GARBAGE_CATEGORIES,
    START_TITLE_FOR_STABLECOINS,
    END_TITLE_FOR_STABLECOINS,
    START_TITLE_FOR_SCAM_TOKENS,
    START_TITLE_FOR_FUNDAMENTAL,
    END_TITLE_FOR_FUNDAMENTAL,
    EXPECTED_KEYS,
    TICKERS,
    PROJECT_TYPES,
)
from bot.utils.common.params import get_cryptocompare_params, get_cryptocompare_params_with_full_name, get_header_params
from bot.utils.project_data import (
    fetch_categories,
    fetch_top_tokens,
    fetch_cryptocompare_data,
    fetch_coingecko_data,
    fetch_coinmarketcap_data,
    get_lower_name,
    get_twitter_link_by_symbol,
    get_top_projects_by_capitalization,
    fetch_tvl_data,
    fetch_top_100_wallets,
    fetch_twitter_data,
    get_percentage_data,
    fetch_fundraise_data,
)
from bot.utils.resources.exceptions.exceptions import ExceptionError
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
        logging.info("Первый запуск: немедленное обновление данных о криптовалютах.")
        await fetch_crypto_data(session)
        logging.info("Первичное обновление данных выполнено успешно.")
    except Exception as e:
        logging.error(f"Ошибка первичного обновления данных: {e}")

    while True:
        current_time = datetime.datetime.now(datetime.timezone.utc)

        # Вычисляем время следующего запуска обновления данных
        next_fetch_run = current_time + datetime.timedelta(hours=6 - (current_time.hour % 6))
        next_fetch_run = next_fetch_run.replace(minute=0, second=0, microsecond=0)
        time_until_fetch = (next_fetch_run - current_time).total_seconds()

        # Вычисляем время следующего обновления ответов агентов (в 3:00 ночи)
        next_agent_run = current_time.replace(hour=3, minute=0, second=0, microsecond=0)
        if current_time >= next_agent_run:
            next_agent_run += datetime.timedelta(days=1)
        time_until_agent = (next_agent_run - current_time).total_seconds()

        # Определяем, что выполнять первым
        if time_until_fetch <= time_until_agent:
            logging.info(f"Следующее обновление данных через {time_until_fetch // 3600:.2f} часов.")
            await asyncio.sleep(max(time_until_fetch, 1))  # Избегаем sleep(0)
            try:
                logging.info("Запуск обновления данных о криптовалютах...")
                await fetch_crypto_data(session)
                logging.info("Обновление данных завершено.")
            except Exception as e:
                logging.error(f"Ошибка обновления данных: {e}")
        else:
            logging.info(f"Следующее обновление ответов агентов через {time_until_agent // 3600:.2f} часов.")
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

            valid_categories = [category for category in all_categories if category not in garbage_categories]

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

            stablecoins = set(load_document_for_garbage_list(START_TITLE_FOR_STABLECOINS, END_TITLE_FOR_STABLECOINS))
            fundamental = set(load_document_for_garbage_list(START_TITLE_FOR_FUNDAMENTAL, END_TITLE_FOR_FUNDAMENTAL))
            scam_tokens = set(load_document_for_garbage_list(START_TITLE_FOR_SCAM_TOKENS))

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
                remaining_tokens = [token for token in all_tokens if token not in filtered_tokens][
                    : 1000 - len(filtered_tokens)
                ]
                filtered_tokens.extend(remaining_tokens)

            # Оставляем ровно 1000 токенов
            top_1000_tokens = filtered_tokens[:1000]

            for token in top_1000_tokens:
                await update_or_create_token(token_data=token)

            logging.info("Обновление списка токенов завершено. В базе 1000 отфильтрованных токенов.")
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


async def update_static_data(async_session: AsyncSession):
    """
    Обновление данных, которые меняются редко (раз в 3 месяца).
    """
    try:
        for project_type in PROJECT_TYPES:
            symbols = await get_top_projects_by_capitalization(project_type=project_type, tickers=TICKERS)

            if not symbols:
                logging.info(f"No projects found for type: {project_type}")
                continue

            for symbol in symbols:
                try:
                    project = await get_one(Project, coin_name=symbol)
                    if not project:
                        logging.error(f"Project not found for {symbol}")
                        continue

                    (
                        twitter_name,
                        description,
                        lower_name,
                        categories,
                    ) = await get_twitter_link_by_symbol(symbol)
                    if not lower_name:
                        lower_name = await get_lower_name(symbol)
                    header_params = get_header_params(symbol)

                    fundraising_data, investors = await fetch_fundraise_data(lower_name)
                    tokenomics_percentage_data = await get_percentage_data(twitter_name, symbol)
                    output_string = "\n".join(tokenomics_percentage_data) if tokenomics_percentage_data else "-"

                    coin_data = await fetch_coinmarketcap_data(user_coin_name=symbol, **header_params)
                    if not coin_data:
                        coin_data = await fetch_coingecko_data(symbol)

                    if not coin_data or not isinstance(coin_data, dict):
                        logging.error(f"Invalid data returned for {symbol}: {coin_data}")
                        continue
                    else:
                        total_supply = coin_data["total_supply"]

                    # Обновление Fundraising
                    await update_or_create(
                        InvestingMetrics,
                        project_id=project.id,
                        defaults={"fundraise": fundraising_data, "fund_level": investors},
                    )

                    # Обновление распределения токенов
                    await update_or_create(
                        FundsProfit,
                        project_id=project.id,
                        defaults={"distribution": output_string},
                    )

                    # Обновление Total Supply
                    await update_or_create(
                        Tokenomics,
                        project_id=project.id,
                        defaults={"total_supply": total_supply},
                    )

                except Exception as error:
                    logging.error(f"Error processing static data for {symbol}: {error}")
                    await async_session.rollback()
                    raise ExceptionError(f"Error processing {symbol}: {str(error)}") from error

        return {"status": "Static data updated successfully"}
    except Exception as e:
        logging.error(f"Critical error in update_static_data: {e}")
        return {"status": "Error", "message": str(e)}


async def update_weekly_data(async_session: AsyncSession):
    """
    Обновление данных, которые меняются редко (раз в неделю).
    """
    try:
        tokens_task = asyncio.create_task(parse_tokens_weekly())
        categories_task = asyncio.create_task(parse_categories_weekly())

        for project_type in PROJECT_TYPES:
            symbols = await get_top_projects_by_capitalization(project_type=project_type, tickers=TICKERS)

            if not symbols:
                logging.info(f"No projects found for type: {project_type}")
                continue

            for symbol in symbols:
                try:
                    project = await get_one(Project, coin_name=symbol)
                    if not project:
                        logging.error(f"Project not found for {symbol}")
                        continue

                    basic_metrics = await get_one(BasicMetrics, project_id=project.id)

                    (
                        twitter_name,
                        description,
                        lower_name,
                        categories,
                    ) = await get_twitter_link_by_symbol(symbol)
                    if not lower_name:
                        lower_name = await get_lower_name(symbol)

                    twitter, twitterscore = fetch_twitter_data(twitter_name)
                    top_100_wallets = await fetch_top_100_wallets(symbol.lower())
                    tvl = await fetch_tvl_data(symbol.lower())

                    cryptocompare_params = get_cryptocompare_params(symbol)
                    cryptocompare_params_with_full_coin_name = get_cryptocompare_params_with_full_name(
                        lower_name.upper()
                    )

                    if basic_metrics.market_price:
                        result = await fetch_cryptocompare_data(
                            cryptocompare_params,
                            cryptocompare_params_with_full_coin_name,
                            basic_metrics.market_price,
                            "top_and_bottom",
                        )

                        fail_high, growth_low, max_price, min_price = result

                        if growth_low and min_price:
                            await update_or_create(
                                TopAndBottom,
                                project_id=project.id,
                                defaults={"min_price": min_price},
                            )
                            await update_or_create(
                                MarketMetrics,
                                project_id=project.id,
                                defaults={"growth_low": growth_low},
                            )

                    await update_or_create(
                        SocialMetrics,
                        project_id=project.id,
                        defaults={
                            "twitter": twitter,
                            "twitterscore": twitterscore,
                        },
                    )

                    await update_or_create(
                        ManipulativeMetrics,
                        project_id=project.id,
                        defaults={"top_100_wallet": top_100_wallets},
                    )

                    await update_or_create(
                        NetworkMetrics,
                        project_id=project.id,
                        defaults={"tvl": tvl},
                    )

                except Exception as error:
                    logging.error(f"Error processing weekly data for {symbol}: {error}")
                    await async_session.rollback()
                    raise ExceptionError(f"Error processing {symbol}: {str(error)}") from error

        await asyncio.gather(tokens_task, categories_task)

        return {"status": "Weekly data updated successfully"}
    except Exception as e:
        logging.error(f"Critical error in update_weekly_data: {e}")
        return {"status": "Error", "message": str(e)}


async def update_dynamic_data(async_session: AsyncSession):
    """
    Обновление данных, которые часто меняются (ежедневно).
    """
    try:
        for project_type in PROJECT_TYPES:
            symbols = await get_top_projects_by_capitalization(project_type=project_type, tickers=TICKERS)

            if not symbols:
                logging.info(f"No projects found for type: {project_type}")
                continue

            for symbol in symbols:
                try:
                    project = await get_one(Project, coin_name=symbol)
                    if not project:
                        logging.error(f"Project not found for {symbol}")
                        continue

                    (
                        twitter_name,
                        description,
                        lower_name,
                        categories,
                    ) = await get_twitter_link_by_symbol(symbol)
                    if not lower_name:
                        lower_name = await get_lower_name(symbol)

                    cryptocompare_params = get_cryptocompare_params(symbol)
                    cryptocompare_params_with_full_coin_name = get_cryptocompare_params_with_full_name(
                        lower_name.upper()
                    )

                    header_params = get_header_params(symbol)

                    # Получение данных с CoinMarketCap
                    data = await fetch_coinmarketcap_data(user_coin_name=symbol, **header_params)
                    if not data:
                        data = await fetch_coingecko_data(symbol)

                    if not data or not isinstance(data, dict):
                        logging.error(f"Invalid data returned for {symbol}: {data}")
                        continue

                    if not all(key in data for key in EXPECTED_KEYS):
                        logging.warning(f"Missing required keys in data for {symbol}: {data}")
                        continue

                    # Данные из API
                    capitalization = data.get("capitalization")
                    fdv = data.get("coin_fdv")
                    price = data.get("price")

                    result = await fetch_cryptocompare_data(
                        cryptocompare_params,
                        cryptocompare_params_with_full_coin_name,
                        price,
                        "top_and_bottom",
                    )

                    if result is None:
                        result = (None, None, None, None)

                    fail_high, growth_low, max_price, min_price = result

                    await update_or_create(
                        Tokenomics,
                        project_id=project.id,
                        defaults={"capitalization": capitalization, "fdv": fdv},
                    )

                    await update_or_create(
                        BasicMetrics,
                        project_id=project.id,
                        defaults={"market_price": round(float(price), 4)},
                    )

                    if max_price and fail_high:
                        await update_or_create(
                            TopAndBottom,
                            project_id=project.id,
                            defaults={"upper_threshold": max_price},
                        )
                        await update_or_create(
                            MarketMetrics,
                            project_id=project.id,
                            defaults={"fail_high": fail_high},
                        )

                    investing_metrics = await get_one(InvestingMetrics, project_id=project.id)
                    if investing_metrics and fdv and investing_metrics.fundraise:
                        await update_or_create(
                            ManipulativeMetrics,
                            project_id=project.id,
                            defaults={"fdv_fundraise": fdv / investing_metrics.fundraise},
                        )

                except Exception as error:
                    logging.error(f"Error processing dynamic data for {symbol}: {error}")
                    await async_session.rollback()
                    raise ExceptionError(f"Error processing {symbol}: {str(error)}") from error

        return {"status": "Dynamic data updated successfully"}
    except Exception as e:
        logging.error(f"Critical error in update_dynamic_data: {e}")
        return {"status": "Error", "message": str(e)}
