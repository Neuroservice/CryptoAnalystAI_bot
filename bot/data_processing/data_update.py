import datetime
import logging
import re
import traceback

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db_operations import (
    get_one,
    update_or_create,
    get_all,
    get_or_create,
)
from bot.database.models import (
    Project,
    Tokenomics,
    BasicMetrics,
    InvestingMetrics,
    ManipulativeMetrics,
    NetworkMetrics,
    FundsProfit,
    AgentAnswer,
    Category,
)
from bot.utils.common.consts import (
    TICKERS,
    PROJECT_TYPES,
    EXPECTED_KEYS,
    DATA_FOR_ANALYSIS_TEXT,
    ALL_DATA_STRING_FUNDS_AGENT,
    ALL_DATA_STRING_FLAGS_AGENT,
    START_TITLE_FOR_GARBAGE_CATEGORIES,
    END_TITLE_FOR_GARBAGE_CATEGORIES,
    START_TITLE_FOR_STABLECOINS,
    END_TITLE_FOR_STABLECOINS,
)
from bot.utils.common.decorators import save_execute
from bot.utils.common.params import get_header_params
from bot.utils.metrics.metrics_evaluation import (
    determine_project_tier,
    calculate_tokenomics_score,
    analyze_project_metrics,
    calculate_project_score,
    project_investors_level,
)
from bot.utils.project_data import (
    get_twitter_link_by_symbol,
    fetch_top_100_wallets,
    fetch_tvl_data,
    get_user_project_info,
    get_project_and_tokenomics,
    calculate_expected_x,
    get_top_projects_by_capitalization,
    fetch_coinmarketcap_data,
    fetch_coingecko_data,
    generate_flags_answer,
    get_coin_description,
    get_percentage_data,
)
from bot.utils.resources.bot_phrases.bot_phrase_handler import (
    phrase_by_language,
)
from bot.utils.resources.bot_phrases.bot_phrase_strings import (
    calculations_choices,
)
from bot.utils.resources.exceptions.exceptions import ExceptionError
from bot.utils.resources.files_worker.google_doc import (
    load_document_for_garbage_list,
)
from bot.utils.resources.files_worker.pdf_worker import generate_pdf
from bot.utils.resources.gpt.gpt import agent_handler
from bot.utils.validations import (
    extract_red_green_flags,
    extract_calculations,
    format_metric,
    get_metric_value,
)

logging.basicConfig(level=logging.INFO)
current_day = datetime.datetime.now(datetime.timezone.utc).day


async def fetch_crypto_data(async_session: AsyncSession):
    """
    Асинхронный эндпоинт для получения данных о криптопроектах.
    """

    try:
        for project_type in PROJECT_TYPES:
            # Получение топовых проектов
            symbols = await get_top_projects_by_capitalization(
                project_type=project_type, tickers=TICKERS
            )

            if not symbols:
                logging.info(f"No projects found for type: {project_type}")
                continue

            print("0")
            for symbol in symbols:
                try:
                    # ШАГ 1: Получение данных проекта
                    print("1")
                    project = await get_one(Project, coin_name=symbol)
                    if not project:
                        logging.error(f"Project not found for {symbol}")
                        continue
                    header_params = get_header_params(symbol)
                    # ШАГ 2: Получение данных с CoinMarketCap
                    print("2")
                    data = await fetch_coinmarketcap_data(
                        user_coin_name=symbol, **header_params
                    )
                    if not data:
                        # Если данные с CoinMarketCap не получены, пробуем получить данные с CoinGecko
                        logging.info(
                            f"Trying to fetch data from CoinGecko for {symbol}"
                        )
                        data = await fetch_coingecko_data(symbol)
                    print("2.1")
                    if not data or not isinstance(data, dict):
                        logging.error(
                            f"Invalid data returned for {symbol}: {data}"
                        )
                        continue
                    if not all(key in data for key in EXPECTED_KEYS):
                        logging.warning(
                            f"Missing required keys in data for {symbol}: {data}"
                        )
                        continue
                    print("2.3")
                    coin_data = data
                    circulating_supply = coin_data.get("circulating_supply")
                    total_supply = coin_data.get("total_supply")
                    price = coin_data.get("price")
                    market_cap = coin_data.get("capitalization")
                    fdv = coin_data.get("coin_fdv")
                    # ШАГ 3: Обновление Tokenomics
                    print("3")
                    await update_or_create(
                        Tokenomics,
                        project_id=project.id,
                        defaults={
                            "circ_supply": circulating_supply,
                            "total_supply": total_supply,
                            "capitalization": market_cap,
                            "fdv": fdv,
                        },
                    )
                    # ШАГ 4: Обновление BasicMetrics
                    print("4")
                    await update_or_create(
                        BasicMetrics,
                        project_id=project.id,
                        defaults={
                            "market_price": round(float(price), 4),
                        },
                    )
                    # ШАГ 5: Обновление ManipulativeMetrics и других метрик
                    print("5")
                    investing_metrics = await get_one(
                        InvestingMetrics, project_id=project.id
                    )
                    manipulative_metrics = await get_one(
                        ManipulativeMetrics, project_id=project.id
                    )

                    if manipulative_metrics and investing_metrics:
                        fundraise = investing_metrics.fundraise
                        top_100_wallets = await fetch_top_100_wallets(
                            symbol.lower()
                        )
                        if top_100_wallets and fdv and fundraise:
                            await update_or_create(
                                ManipulativeMetrics,
                                project_id=project.id,
                                defaults={
                                    "fdv_fundraise": fdv / fundraise,
                                    "top_100_wallet": top_100_wallets,
                                },
                            )
                    # ШАГ 6: Обновление NetworkMetrics (TVL)
                    print("6")
                    (
                        twitter_name,
                        description,
                        lower_name,
                        categories,
                    ) = await get_twitter_link_by_symbol(symbol)
                    if lower_name:
                        tvl = await fetch_tvl_data(lower_name)
                        if tvl and fdv:
                            await update_or_create(
                                NetworkMetrics,
                                project_id=project.id,
                                defaults={
                                    "tvl": tvl,
                                    "tvl_fdv": tvl / fdv,
                                },
                            )

                    # ШАГ 7: Обновление FundsProfit
                    print("7")
                    funds_profit = await get_one(
                        FundsProfit, project_id=project.id
                    )

                    if (
                        not funds_profit
                        or not funds_profit.distribution
                        or funds_profit.distribution == "-"
                    ):
                        print("7.1")
                        (
                            twitter_link,
                            description,
                            lower_name,
                            categories,
                        ) = await get_twitter_link_by_symbol(symbol)
                        tokenomics_percentage_data = await get_percentage_data(
                            twitter_link, symbol
                        )
                        output_string = (
                            "\n".join(tokenomics_percentage_data)
                            if tokenomics_percentage_data
                            else "-"
                        )
                        await update_or_create(
                            FundsProfit,
                            project_id=project.id,
                            defaults={"distribution": output_string},
                        )

                    # Сохранение изменений
                    print("8")

                except Exception as error:
                    logging.error(f"Error processing {symbol}: {error}")
                    await async_session.rollback()  # Откат транзакции при ошибке
                    raise ExceptionError(
                        f"Error processing symbol {symbol}: {str(error)}"
                    ) from error

        return {"status": "Data fetching completed"}
    except Exception as e:
        logging.error(f"Critical error in fetch_crypto_data: {e}")
        logging.error(f"Exception type: {type(e).__name__}")
        logging.error("Traceback:")
        logging.error(traceback.format_exc())  # Логирует весь стек вызовов
        return {"status": "Error", "message": str(e)}


async def update_agent_answers():
    """
    Функция обновления ответов агентов по каждому токену:
    1. Собирает данные по проекту
    2. Получает анализ от LLM по этим метрикам
    3. Сохраняет новый ответ
    """

    current_time = datetime.datetime.now(datetime.timezone.utc)
    three_days_ago = current_time - datetime.timedelta(days=1)
    current_date = current_time.strftime("%d.%m.%Y")
    comparison_results = ""
    language = "ENG"
    agents_info = []
    data_for_tokenomics = []
    garbage_categories = load_document_for_garbage_list(
        START_TITLE_FOR_GARBAGE_CATEGORIES, END_TITLE_FOR_GARBAGE_CATEGORIES
    )

    outdated_answers = await get_all(
        AgentAnswer, updated_at=f"<={three_days_ago}"
    )

    for agent_answer in outdated_answers:
        project = await get_one(Project, id=agent_answer.project_id)

        if not project:
            continue

        first_phrase = agent_answer.answer.split(" ", 1)[0]

        if first_phrase.startswith("Анализ проектов"):
            language = "RU"

        (
            twitter_name,
            description,
            lower_name,
            categories,
        ) = await get_twitter_link_by_symbol(project.coin_name)
        coin_description = await get_coin_description(lower_name)
        if description:
            coin_description += description

        token_description = await agent_handler(
            "description", topic=coin_description, language=language
        )

        if not categories or len(categories) == 0:
            continue

        # Получаем или создаём категории в БД
        category_instances = []
        for category_name in categories:
            if category_name not in garbage_categories:
                category_instance, _ = await get_or_create(
                    Category, category_name=category_name
                )
                category_instances.append(category_instance)

        if len(category_instances) == 0:
            continue

        project_info = await get_user_project_info(project.coin_name)
        twitter_link = await get_twitter_link_by_symbol(project.coin_name)
        tokenomics_data = project_info.get("tokenomics_data")
        basic_metrics = project_info.get("basic_metrics")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        market_metrics = project_info.get("market_metrics")
        top_and_bottom = project_info.get("top_and_bottom")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")
        _, tokenomics_data_list = await get_project_and_tokenomics(
            categories, project.coin_name
        )

        top_projects = sorted(
            tokenomics_data_list,
            key=lambda item: item[1][0].capitalization
            if item[1][0].capitalization
            else 0,
            reverse=True,
        )[:5]

        for index, (top_projects, tokenomics_data) in enumerate(
            top_projects, start=1
        ):
            project_coin = top_projects.coin_name
            for tokenomics in tokenomics_data:
                calculation_result = calculate_expected_x(
                    entry_price=basic_metrics.market_price,
                    total_supply=tokenomics_data[0].total_supply,
                    fdv=tokenomics.fdv,
                )

                fair_price = calculation_result["fair_price"]
                fair_price = (
                    f"{fair_price:.5f}"
                    if isinstance(fair_price, (int, float))
                    else phrase_by_language(
                        "comparisons_error", agent_answer.language
                    )
                )

                comparison_results += calculations_choices[
                    agent_answer.language
                ].format(
                    user_coin_name=project.coin_name,
                    project_coin_name=project_coin,
                    growth=(calculation_result["expected_x"] - 1.0) * 100,
                    fair_price=fair_price,
                )

        tier_answer = determine_project_tier(
            capitalization=get_metric_value(tokenomics_data, "fdv"),
            fundraising=get_metric_value(investing_metrics, "fundraise"),
            twitter_followers=get_metric_value(social_metrics, "twitter"),
            twitter_score=get_metric_value(social_metrics, "twitterscore"),
            investors=get_metric_value(investing_metrics, "fund_level"),
            language=language if language else "ENG",
        )

        for (
            index,
            coin_name,
            project_coin,
            expected_x,
            fair_price,
        ) in agents_info:
            ticker = project_coin
            growth_percent = expected_x
            data_for_tokenomics.append(
                {ticker: {"growth_percent": growth_percent}}
            )

        tokemonic_answer, tokemonic_score = calculate_tokenomics_score(
            project.coin_name, data_for_tokenomics
        )

        all_data_string_for_funds_agent = ALL_DATA_STRING_FUNDS_AGENT.format(
            funds_profit_distribution=get_metric_value(
                funds_profit, "distribution"
            )
        )
        funds_agent_answer = await agent_handler(
            "funds_agent", topic=all_data_string_for_funds_agent
        )

        fdv = (
            float(tokenomics_data.fdv)
            if tokenomics_data and tokenomics_data.fdv
            else (phrase_by_language("no_data", language))
        )
        fundraising_amount = (
            float(investing_metrics.fundraise)
            if investing_metrics and investing_metrics.fundraise
            else (phrase_by_language("no_data", language))
        )

        funds_agent_answer = await funds_agent_answer
        investors_percent = float(funds_agent_answer.strip("%")) / 100

        if isinstance(fdv, float) and isinstance(fundraising_amount, float):
            result_ratio = (fdv * investors_percent) / fundraising_amount
            final_score = f"{result_ratio:.2%}"
        else:
            result_ratio = phrase_by_language("no_data", language)
            final_score = result_ratio

        (
            funds_answer,
            funds_scores,
            funds_score,
            growth_and_fall_score,
        ) = analyze_project_metrics(
            final_score,
            get_metric_value(
                market_metrics,
                "growth_low",
                transform=lambda x: round((x - 100) * 100, 2),
            ),
            get_metric_value(
                market_metrics,
                "fail_high",
                transform=lambda x: round(x * 100, 2),
            ),
            get_metric_value(
                manipulative_metrics,
                "top_100_wallet",
                transform=lambda x: x * 100,
            ),
            get_metric_value(
                network_metrics,
                "tvl",
                transform=lambda tvl: (tvl / tokenomics_data.capitalization)
                * 100
                if tokenomics_data and tokenomics_data.capitalization
                else None,
            ),
        )

        if investing_metrics and investing_metrics.fund_level:
            project_investors_level_result = project_investors_level(
                investors=investing_metrics.fund_level
            )
            investors_level = project_investors_level_result["level"]
            investors_level_score = project_investors_level_result["score"]
        else:
            investors_level = phrase_by_language("no_data", language)
            investors_level_score = 0

        project_rating_result = calculate_project_score(
            get_metric_value(investing_metrics, "fundraise"),
            tier_answer,
            investors_level_score,
            get_metric_value(social_metrics, "twitter"),
            get_metric_value(social_metrics, "twitterscore"),
            int((network_metrics.tvl / tokenomics_data.capitalization) * 100)
            if network_metrics
            and network_metrics.tvl
            and tokenomics_data
            and tokenomics_data.total_supply
            and tokenomics_data.capitalization
            else 0,
            round(manipulative_metrics.top_100_wallet * 100, 2)
            if manipulative_metrics and manipulative_metrics.top_100_wallet
            else 0,
            int(growth_and_fall_score),
            tokemonic_score,
            funds_scores,
            language,
        )

        project_rating_answer = project_rating_result["calculations_summary"]
        fundraising_score = project_rating_result["fundraising_score"]
        followers_score = project_rating_result["followers_score"]
        twitter_engagement_score = project_rating_result[
            "twitter_engagement_score"
        ]
        overal_final_score = project_rating_result["preliminary_score"]
        tokenomics_score = project_rating_result["tokenomics_score"]
        project_rating_text = project_rating_result["project_rating"]

        all_data_string_for_flags_agent = ALL_DATA_STRING_FLAGS_AGENT.format(
            project_coin_name=project.coin_name,
            project_categories=categories,
            tier_answer=tier_answer,
            tokemonic_answer=tokemonic_answer,
            funds_answer=funds_answer,
            project_rating_answer=project_rating_answer,
            social_metrics_twitter=social_metrics.twitter,
            twitter_link=twitter_link,
            social_metrics_twitterscore=social_metrics.twitterscore,
        )

        flags_answer = await generate_flags_answer(
            all_data_string_for_flags_agent=all_data_string_for_flags_agent,
            project=project,
            tokenomics_data=tokenomics_data,
            investing_metrics=investing_metrics,
            social_metrics=social_metrics,
            funds_profit=funds_profit,
            market_metrics=market_metrics,
            manipulative_metrics=manipulative_metrics,
            network_metrics=network_metrics,
            tier=tier_answer,
            funds_answer=funds_answer,
            tokenomic_answer=tokemonic_answer,
            categories=categories,
            twitter_link=twitter_link,
            top_and_bottom=top_and_bottom,
            language=agent_answer.language,
        )

        answer = re.sub(
            r"\n\s*\n",
            "\n",
            flags_answer.replace("**", "")
            + DATA_FOR_ANALYSIS_TEXT
            + comparison_results,
        )

        red_green_flags = extract_red_green_flags(answer, language)
        calculations = extract_calculations(answer, language)

        top_and_bottom_answer = phrase_by_language(
            "top_bottom_values",
            language,
            current_value=round(basic_metrics.market_price, 4),
            min_value=phrase_by_language("no_data", language),
            max_value=phrase_by_language("no_data", language),
        )

        if (
            top_and_bottom
            and top_and_bottom.lower_threshold
            and top_and_bottom.upper_threshold
        ):
            top_and_bottom_answer = phrase_by_language(
                "top_bottom_values",
                language,
                current_value=round(basic_metrics.market_price, 4),
                min_value=round(top_and_bottom.lower_threshold, 4),
                max_value=round(top_and_bottom.upper_threshold, 4),
            )

        profit_text = phrase_by_language(
            "investor_profit_text",
            language=language,
            fdv=f"{fdv:,.2f}" if isinstance(fdv, float) else fdv,
            investors_percent=f"{investors_percent:.0%}"
            if isinstance(investors_percent, float)
            else investors_percent,
            fundraising_amount=f"{fundraising_amount:,.2f}"
            if isinstance(fundraising_amount, float)
            else fundraising_amount,
            result_ratio=f"{result_ratio:.4f}"
            if isinstance(result_ratio, float)
            else result_ratio,
            final_score=final_score,
        )

        if funds_profit and funds_profit.distribution:
            distribution_items = funds_profit.distribution.split("\n")
            formatted_distribution = "\n".join(
                [f"- {item}" for item in distribution_items]
            )
        else:
            formatted_distribution = phrase_by_language(
                "no_token_distribution", language
            )

        formatted_metrics = [
            format_metric(
                "capitalization",
                f"${round(get_metric_value(tokenomics_data, 'capitalization', 0), 0)}"
                if get_metric_value(tokenomics_data, "capitalization")
                else None,
                language,
            ),
            format_metric(
                "fdv",
                f"${round(get_metric_value(tokenomics_data, 'fdv', 0), 0)}"
                if get_metric_value(tokenomics_data, "fdv")
                else None,
                language,
            ),
            format_metric(
                "total_supply",
                f"{round(get_metric_value(tokenomics_data, 'total_supply', 0), 0)}"
                if get_metric_value(tokenomics_data, "total_supply")
                else None,
                language,
            ),
            format_metric(
                "fundraising",
                f"${round(get_metric_value(investing_metrics, 'fundraise', 0), 0)}"
                if get_metric_value(investing_metrics, "fundraise")
                else None,
                language,
            ),
            format_metric(
                "twitter_followers",
                f"{get_metric_value(social_metrics, 'twitter')} ({twitter_link[0]})"
                if get_metric_value(social_metrics, "twitter")
                else None,
                language,
            ),
            format_metric(
                "twitter_score",
                f"{get_metric_value(social_metrics, 'twitterscore')}"
                if get_metric_value(social_metrics, "twitterscore")
                else None,
                language,
            ),
            format_metric(
                "tvl",
                f"${round(get_metric_value(network_metrics, 'tvl', 0), 0)}"
                if get_metric_value(network_metrics, "tvl")
                else None,
                language,
            ),
            format_metric(
                "top_100_wallet",
                f"{round(get_metric_value(manipulative_metrics, 'top_100_wallet', 0) * 100, 2)}%"
                if get_metric_value(manipulative_metrics, "top_100_wallet")
                else None,
                language,
            ),
            format_metric(
                "investors",
                f"{get_metric_value(investing_metrics, 'fund_level')}"
                if get_metric_value(investing_metrics, "fund_level")
                else None,
                language,
            ),
        ]

        formatted_metrics_text = "\n".join(formatted_metrics)
        project_evaluation = phrase_by_language(
            "project_rating_details",
            language,
            fundraising_score=round(fundraising_score, 2),
            tier=investors_level,
            tier_score=investors_level_score,
            followers_score=int(followers_score),
            twitter_engagement_score=round(twitter_engagement_score, 2),
            tokenomics_score=tokenomics_score,
            profitability_score=round(funds_score, 2),
            preliminary_score=int(growth_and_fall_score),
            top_100_percent=round(manipulative_metrics.top_100_wallet * 100, 2)
            if manipulative_metrics and manipulative_metrics.top_100_wallet
            else 0,
            tvl_percent=int(
                (network_metrics.tvl / tokenomics_data.capitalization) * 100
            )
            if network_metrics.tvl and tokenomics_data.total_supply
            else 0,
        )

        pdf_output, extracted_text = await generate_pdf(
            funds_profit=formatted_distribution,
            tier_answer=tier_answer,
            language=language,
            formatted_metrics_text=formatted_metrics_text,
            profit_text=profit_text,
            red_green_flags=red_green_flags,
            top_and_bottom_answer=top_and_bottom_answer,
            calculations=calculations,
            project_evaluation=project_evaluation,
            overal_final_score=overal_final_score,
            project_rating_text=project_rating_text,
            current_date=current_date,
            token_description=token_description,
            categories=categories,
            lower_name=lower_name.capitalize(),
            coin_name=project.coin_name.upper(),
        )

        await update_or_create(
            model=AgentAnswer,
            id=agent_answer.id,
            defaults={
                "answer": extracted_text,
                "updated_at": current_time,
            },
        )
