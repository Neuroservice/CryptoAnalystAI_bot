import asyncio
import logging

from bot.database.db_operations import get_one, update_or_create, get_or_create, update_or_create_token, get_all
from bot.database.models import (
    Project,
    InvestingMetrics,
    FundsProfit,
    Tokenomics,
    BasicMetrics,
    TopAndBottom,
    MarketMetrics,
    SocialMetrics,
    ManipulativeMetrics,
    NetworkMetrics,
    Category,
)
from bot.utils.common.consts import (
    EXPECTED_KEYS,
    TICKERS,
    PROJECT_TYPES,
    START_TITLE_FOR_GARBAGE_CATEGORIES,
    END_TITLE_FOR_GARBAGE_CATEGORIES,
    START_TITLE_FOR_STABLECOINS,
    START_TITLE_FOR_FUNDAMENTAL,
    START_TITLE_FOR_SCAM_TOKENS,
    END_TITLE_FOR_STABLECOINS,
    END_TITLE_FOR_FUNDAMENTAL,
)
from bot.utils.common.params import get_header_params, get_cryptocompare_params_with_full_name, get_cryptocompare_params
from bot.utils.project_data import (
    get_twitter_link_by_symbol,
    get_lower_name,
    fetch_fundraise_data,
    get_percentage_data,
    fetch_coinmarketcap_data,
    fetch_coingecko_data,
    fetch_twitter_data,
    fetch_top_100_wallets,
    fetch_tvl_data,
    fetch_cryptocompare_data,
    get_top_projects_by_capitalization,
    fetch_categories,
    fetch_top_tokens,
)
from bot.utils.resources.files_worker.google_doc import load_document_for_garbage_list


async def update_static_data():
    """
    Обновление данных, которые меняются редко (раз в 3 месяца).
    """
    try:
        projects = await get_all(Project)

        # Загружаем списки мусорных токенов
        stablecoins = set(load_document_for_garbage_list(START_TITLE_FOR_STABLECOINS, END_TITLE_FOR_STABLECOINS))
        fundamental = set(load_document_for_garbage_list(START_TITLE_FOR_FUNDAMENTAL, END_TITLE_FOR_FUNDAMENTAL))
        scam_tokens = set(load_document_for_garbage_list(START_TITLE_FOR_SCAM_TOKENS))

        # Фильтруем токены
        valid_projects = [
            project
            for project in projects
            if project.coin_name not in stablecoins
            and project.coin_name not in fundamental
            and project.coin_name not in scam_tokens
        ]

        # Ограничиваем список до 1000 проектов
        top_1000_projects = valid_projects[:1000]

        for project in top_1000_projects:
            success = await fetch_static_data(project.coin_name)
            if not success:
                logging.error(f"Skipping {project.coin_name} due to static data fetch error")

        return True
    except Exception as e:
        logging.error(f"Critical error in update_static_data: {e}")
        return False


async def update_weekly_data():
    """
    Обновление данных, которые меняются раз в неделю.
    """
    try:
        tokens_task = asyncio.create_task(parse_tokens_weekly())
        categories_task = asyncio.create_task(parse_categories_weekly())

        projects = await get_all(Project)

        # Загружаем списки мусорных токенов
        stablecoins = set(load_document_for_garbage_list(START_TITLE_FOR_STABLECOINS, END_TITLE_FOR_STABLECOINS))
        fundamental = set(load_document_for_garbage_list(START_TITLE_FOR_FUNDAMENTAL, END_TITLE_FOR_FUNDAMENTAL))
        scam_tokens = set(load_document_for_garbage_list(START_TITLE_FOR_SCAM_TOKENS))

        # Фильтруем токены
        valid_projects = [
            project
            for project in projects
            if project.coin_name not in stablecoins
            and project.coin_name not in fundamental
            and project.coin_name not in scam_tokens
        ]

        # Ограничиваем список до 1000 проектов
        top_1000_projects = valid_projects[:1000]

        for project in top_1000_projects:
            success = await fetch_weekly_data(project.coin_name)
            if not success:
                logging.error(f"Skipping {project.coin_name} due to weekly data fetch error")

        await asyncio.gather(tokens_task, categories_task)

        return True
    except Exception as e:
        logging.error(f"Critical error in update_weekly_data: {e}")
        return False


async def update_dynamic_data():
    """
    Обновление динамических данных (ежедневно).
    """
    try:
        projects = await get_all(Project)

        # Загружаем списки мусорных токенов
        stablecoins = set(load_document_for_garbage_list(START_TITLE_FOR_STABLECOINS, END_TITLE_FOR_STABLECOINS))
        fundamental = set(load_document_for_garbage_list(START_TITLE_FOR_FUNDAMENTAL, END_TITLE_FOR_FUNDAMENTAL))
        scam_tokens = set(load_document_for_garbage_list(START_TITLE_FOR_SCAM_TOKENS))

        # Фильтруем токены
        valid_projects = [
            project
            for project in projects
            if project.coin_name not in stablecoins
            and project.coin_name not in fundamental
            and project.coin_name not in scam_tokens
        ]

        # Ограничиваем список до 1000 проектов
        top_1000_projects = valid_projects[:1000]

        for project in top_1000_projects:
            try:
                success = await fetch_dynamic_data(project.coin_name)

                if not success:
                    logging.error(f"Skipping {project.coin_name} due to data fetch error")
                    continue

            except Exception as error:
                logging.error(f"Error processing dynamic data for {project.coin_name}: {error}")
                return False

        return True
    except Exception as e:
        logging.error(f"Critical error in update_dynamic_data: {e}")
        return False


async def fetch_static_data(symbol: str) -> bool:
    """
    Получает и обновляет статические данные (раз в 3 месяца).

    Возвращает:
    - True, если данные успешно обновлены.
    - False, если возникла ошибка.
    """
    try:
        project = await get_one(Project, coin_name=symbol)
        if not project:
            logging.error(f"Project not found for {symbol}")
            return False

        twitter_name, description, lower_name, categories = await get_twitter_link_by_symbol(symbol)
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
            return False

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

        return True

    except Exception as error:
        logging.error(f"Error processing static data for {symbol}: {error}")
        return False


async def fetch_weekly_data(symbol: str) -> bool:
    """
    Получает и обновляет еженедельные данные.

    Возвращает:
    - True, если данные успешно обновлены.
    - False, если возникла ошибка.
    """
    try:
        project = await get_one(Project, coin_name=symbol)
        if not project:
            logging.error(f"Project not found for {symbol}")
            return False

        basic_metrics = await get_one(BasicMetrics, project_id=project.id)

        twitter_name, description, lower_name, categories = await get_twitter_link_by_symbol(symbol)
        if not lower_name:
            lower_name = await get_lower_name(symbol)

        twitter, twitterscore = await fetch_twitter_data(twitter_name)
        top_100_wallets = await fetch_top_100_wallets(symbol.lower())
        tvl = await fetch_tvl_data(symbol.lower())

        cryptocompare_params = get_cryptocompare_params(symbol)
        cryptocompare_params_with_full_coin_name = get_cryptocompare_params_with_full_name(lower_name.upper())

        if basic_metrics and basic_metrics.market_price:
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

        # Обновление соц. метрик
        await update_or_create(
            SocialMetrics,
            project_id=project.id,
            defaults={"twitter": twitter, "twitterscore": twitterscore},
        )

        # Обновление манипулятивных метрик
        await update_or_create(
            ManipulativeMetrics,
            project_id=project.id,
            defaults={"top_100_wallet": top_100_wallets},
        )

        # Обновление сетевых метрик
        await update_or_create(
            NetworkMetrics,
            project_id=project.id,
            defaults={"tvl": tvl},
        )

        return True

    except Exception as error:
        logging.error(f"Error processing weekly data for {symbol}: {error}")
        return False


async def fetch_dynamic_data(symbol: str) -> bool:
    """
    Получает и обновляет данные о проекте.

    Возвращает:
    - True, если все прошло успешно.
    - False, если возникла ошибка.
    """
    try:
        # Получаем объект проекта
        project = await get_one(Project, coin_name=symbol)
        if not project:
            logging.error(f"Project not found for {symbol}")
            return False

        # Получаем дополнительные данные о проекте
        twitter_name, description, lower_name, categories = await get_twitter_link_by_symbol(symbol)
        if not lower_name:
            lower_name = await get_lower_name(symbol)

        # Подготавливаем параметры для API-запросов
        cryptocompare_params = get_cryptocompare_params(symbol)
        cryptocompare_params_with_full_coin_name = get_cryptocompare_params_with_full_name(lower_name.upper())
        header_params = get_header_params(symbol)

        # Получаем данные с CoinMarketCap или CoinGecko
        data = await fetch_coinmarketcap_data(user_coin_name=symbol, **header_params)
        if not data:
            data = await fetch_coingecko_data(symbol)

        if not data or not isinstance(data, dict):
            logging.error(f"Invalid data returned for {symbol}: {data}")
            return False

        if not all(key in data for key in EXPECTED_KEYS):
            logging.warning(f"Missing required keys in data for {symbol}: {data}")
            return False

        # Данные о цене и капитализации
        capitalization = data.get("capitalization")
        fdv = data.get("coin_fdv")
        price = data.get("price")

        # Получаем границы рынка
        result = await fetch_cryptocompare_data(
            cryptocompare_params,
            cryptocompare_params_with_full_coin_name,
            price,
            "top_and_bottom",
        )

        if result is None:
            result = (None, None, None, None)

        fail_high, growth_low, max_price, min_price = result

        # Обновление капитализации и цены
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

        # Обновление границ рынка
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

        # Обновление манипулятивных метрик
        investing_metrics = await get_one(InvestingMetrics, project_id=project.id)
        if investing_metrics and fdv and investing_metrics.fundraise:
            await update_or_create(
                ManipulativeMetrics,
                project_id=project.id,
                defaults={"fdv_fundraise": fdv / investing_metrics.fundraise},
            )

        logging.info(f"Successfully updated project data for {symbol}")
        return True

    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return False


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
            all_tokens = await fetch_top_tokens(limit=1500)

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

            print("top_1000_tokens: ", top_1000_tokens)

            for token in top_1000_tokens:
                instance, bool_type = await update_or_create_token(
                    token_data=token,
                )

                if bool_type:
                    # Выполняем парсинг для новых проектов
                    static_data_success = await fetch_static_data(token["symbol"])
                    weekly_data_success = await fetch_weekly_data(token["symbol"])

                    if not static_data_success:
                        logging.error(f"Static data fetch failed for {token}")

                    if not weekly_data_success:
                        logging.error(f"Weekly data fetch failed for {token}")

            logging.info("Обновление списка токенов завершено. В базе 1000 отфильтрованных токенов.")
        except Exception as e:
            logging.error(f"Ошибка при обновлении списка токенов: {e}")

        # Ожидание 7 дней
        await asyncio.sleep(7 * 24 * 60 * 60)
