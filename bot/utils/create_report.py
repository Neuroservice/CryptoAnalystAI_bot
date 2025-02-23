import logging
import re
import traceback
from datetime import datetime
from typing import Optional, Union

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db_operations import get_one, get_user_from_redis_or_db
from bot.database.models import Calculation, AgentAnswer
from bot.utils.common.bot_states import CalculateProject
from bot.utils.common.consts import (
    PROJECT_POINTS_ENG,
    PROJECT_POINTS_RU,
    TICKERS,
    DATA_FOR_ANALYSIS_TEXT,
    ALL_DATA_STRING_FLAGS_AGENT,
    ALL_DATA_STRING_FUNDS_AGENT,
    REPLACED_PROJECT_TWITTER,
)
from bot.utils.common.decorators import save_execute
from bot.utils.common.sessions import session_local
from bot.utils.metrics.metrics_evaluation import (
    calculate_tokenomics_score,
    calculate_project_score,
    determine_project_tier,
    project_investors_level,
    analyze_project_metrics,
)
from bot.utils.project_data import (
    generate_flags_answer,
    get_user_project_info,
    calculate_expected_x,
    get_project_and_tokenomics,
    get_top_projects_by_capitalization_and_category,
)
from bot.utils.resources.bot_phrases.bot_phrase_handler import (
    phrase_by_user,
    phrase_by_language,
)
from bot.utils.resources.bot_phrases.bot_phrase_strings import (
    calculations_choices,
)
from bot.utils.resources.exceptions.exceptions import ValueProcessingError
from bot.utils.resources.files_worker.pdf_worker import (
    generate_pdf,
    create_pdf_file,
)
from bot.utils.resources.gpt.gpt import agent_handler
from bot.utils.validations import (
    format_metric,
    extract_calculations,
    extract_red_green_flags,
    get_metric_value,
)


@save_execute
async def create_basic_report(
    session: AsyncSession,
    state: FSMContext,
    message: Message = None,
    user_id: Optional[int] = None,
):
    """
    Создание базового отчета для пользователя в текстовом формате, без файла.
    Возвращает текст отчета.
    """

    state_data = await state.get_data()
    user_coin_name = state_data.get("user_coin_name")
    categories = state_data.get("categories")
    user_data = await get_user_from_redis_or_db(user_id)
    language = user_data.get("language", "ENG")
    agents_info = []

    try:
        project_info = await get_user_project_info(user_coin_name)
        project = project_info.get("project")
        basic_metrics = project_info.get("basic_metrics")

        projects, tokenomics_data_list = await get_project_and_tokenomics(
            categories, user_coin_name
        )
        top_projects = get_top_projects_by_capitalization_and_category(
            tokenomics_data_list
        )

        for index, (project, tokenomics_data) in enumerate(
            top_projects, start=1
        ):
            for tokenomics in tokenomics_data:
                fdv = tokenomics.fdv if tokenomics.fdv else 0
                calculation_result = calculate_expected_x(
                    entry_price=basic_metrics.entry_price,
                    total_supply=tokenomics.total_supply,
                    fdv=fdv,
                )

                if "error" in calculation_result:
                    raise ValueProcessingError(
                        str(calculation_result["error"])
                    )

                fair_price = calculation_result["fair_price"]
                fair_price = (
                    f"{fair_price:.5f}"
                    if isinstance(fair_price, (int, float))
                    else phrase_by_language("comparisons_error", language)
                )

                if project.coin_name in TICKERS:
                    agents_info.append(
                        [
                            index,
                            user_coin_name,
                            project.coin_name,
                            round(
                                (float(calculation_result["expected_x"]) - 1.0)
                                * 100,
                                2,
                            ),
                            fair_price,
                        ]
                    )

        comparison_results = ""
        result_index = 1
        for (
            index,
            coin_name,
            project_coin,
            expected_x,
            fair_price,
        ) in agents_info:
            if project_coin != user_coin_name:
                if project.coin_name in TICKERS:
                    try:
                        if not isinstance(fair_price, (str, int, float)):
                            raise ValueProcessingError(
                                f"Unexpected type for fair_price: {type(fair_price)}"
                            )

                        if not isinstance(index, int):
                            raise ValueProcessingError(
                                f"Unexpected type for index: {type(index)}"
                            )
                        if not isinstance(user_coin_name, str):
                            raise ValueProcessingError(
                                f"Unexpected type for user_coin_name: {type(user_coin_name)}"
                            )
                        if not isinstance(project_coin, str):
                            raise ValueProcessingError(
                                f"Unexpected type for project_coin: {type(project_coin)}"
                            )

                        comparison_results += calculations_choices[
                            language
                        ].format(
                            user_coin_name=user_coin_name,
                            project_coin_name=project_coin,
                            growth=expected_x,
                            fair_price=fair_price,
                        )
                        result_index += 1

                    except ValueProcessingError as e:
                        logging.error(f"{e}")
                        logging.error(f"index: {index}, type: {type(index)}")
                        logging.error(
                            f"user_coin_name: {user_coin_name}, type: {type(user_coin_name)}"
                        )
                        logging.error(
                            f"project_coin: {project_coin}, type: {type(project_coin)}"
                        )
                        logging.error(
                            f"growth: {expected_x}, type: {type(expected_x)}"
                        )
                        logging.error(
                            f"fair_price: {fair_price}, type: {type(fair_price)}"
                        )
                        raise

        answer = comparison_results + "\n"
        answer = answer.replace("**", "").strip()

        return answer

    except ValueProcessingError as e:
        error_message = f"{e}\n{traceback.format_exc()}"
        return f"{await phrase_by_user('error_not_valid_input_data', user_id, session)}\n{error_message}"


@save_execute
async def create_pdf_report(
    session: AsyncSession,
    state: FSMContext,
    message: Optional[Union[Message, str]] = None,
    user_id: Optional[int] = None,
):
    """
    Создание pdf-файла с анализом метрик проекта.
    """

    state_data = await state.get_data()
    new_project = state_data.get("new_project")
    coin_name = state_data.get("coin_name")
    twitter_link = state_data.get("twitter_name")
    token_description = state_data.get("token_description")
    price = state_data.get("price")
    total_supply = state_data.get("total_supply")
    calculation_record = state_data.get("calculation_record")

    row_data = []
    coin_twitter, about, lower_name, categories = twitter_link
    twitter_name = REPLACED_PROJECT_TWITTER.get(coin_twitter, twitter_link)
    user_data = await get_user_from_redis_or_db(user_id)
    language = user_data.get("language", "ENG")
    current_date = datetime.now().strftime("%d.%m.%Y")
    existing_calculation = await get_one(Calculation, id=calculation_record["id"])

    try:
        result = await get_project_and_tokenomics(
            categories, coin_name
        )

        if not isinstance(result, tuple) or len(result) != 2:
            raise ValueProcessingError(
                "Unexpected result format from get_project_and_tokenomics."
            )

        projects, tokenomics_data_list = result

        top_projects = get_top_projects_by_capitalization_and_category(
            tokenomics_data_list
        )

        if "error" in projects:
            raise ValueProcessingError(
                f"Error from project data: {projects['error']}"
            )

        for index, (project, tokenomics_data) in enumerate(
            top_projects, start=1
        ):
            if tokenomics_data:
                for tokenomics in tokenomics_data:

                    fdv = tokenomics.fdv if tokenomics.fdv is not None else 0
                    calculation_result = calculate_expected_x(
                        entry_price=price,
                        total_supply=total_supply,
                        fdv=fdv,
                    )

                    if "error" in calculation_result:
                        raise ValueProcessingError(
                            str(calculation_result["error"])
                        )

                    fair_price = (
                        f"{calculation_result['fair_price']:.5f}"
                        if isinstance(
                            calculation_result["fair_price"], (int, float)
                        )
                        else phrase_by_language("comparisons_error", language)
                    )
                    expected_x = f"{calculation_result['expected_x']:.5f}"

                    row_data.append(
                        [
                            index,
                            coin_name,
                            project.coin_name,
                            round((float(expected_x) - 1.0) * 100, 2),
                            fair_price,
                        ]
                    )

        project_info = await get_user_project_info(new_project["coin_name"])
        project = project_info.get("project")
        basic_metrics = project_info.get("basic_metrics")
        tokenomics_data = project_info.get("tokenomics_data")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        market_metrics = project_info.get("market_metrics")
        manipulative_metrics = project_info.get("manipulative_metrics")
        top_and_bottom = project_info.get("top_and_bottom")
        network_metrics = project_info.get("network_metrics")

        existing_answer = await get_one(
            AgentAnswer, project_id=project.id, language=language
        )

        comparison_results = ""
        result_index = 1

        for index, coin_name, project_coin, expected_x, fair_price in row_data:
            if project_coin != coin_name:
                if project_coin in TICKERS:
                    try:
                        # Проверка fair_price, чтобы убедиться, что это строка или число
                        if not isinstance(fair_price, (str, int, float)):
                            raise ValueProcessingError(
                                f"Unexpected type for fair_price: {type(fair_price)}"
                            )

                        # Проверяем типы других переменных
                        if not isinstance(index, int):
                            raise ValueProcessingError(
                                f"Unexpected type for index: {type(index)}"
                            )
                        if not isinstance(coin_name, str):
                            raise ValueProcessingError(
                                f"Unexpected type for user_coin_name: {type(coin_name)}"
                            )
                        if not isinstance(project_coin, str):
                            raise ValueProcessingError(
                                f"Unexpected type for project_coin_name: {type(project_coin)}"
                            )

                        comparison_results += calculations_choices[
                            language
                        ].format(
                            index=index,
                            user_coin_name=coin_name,
                            project_coin_name=project_coin,
                            growth=expected_x,
                            fair_price=fair_price,
                        )
                        result_index += 1

                    except ValueProcessingError as e:
                        # Логируем и обрабатываем ошибку
                        error_message = (
                            f"Value processing error: {e}\n"
                            f"index: {index}, type: {type(index)}\n"
                            f"user_coin_name: {coin_name}, type: {type(coin_name)}\n"
                            f"project_coin: {project_coin}, type: {type(project_coin)}\n"
                            f"growth: {expected_x}, type: {type(expected_x)}\n"
                            f"fair_price: {fair_price}, type: {type(fair_price)}"
                        )
                        raise ValueProcessingError(error_message)

        all_data_string_for_funds_agent = ALL_DATA_STRING_FUNDS_AGENT.format(
            funds_profit_distribution=get_metric_value(
                funds_profit, "distribution"
            )
        )
        funds_agent_answer = await agent_handler(
            "funds_agent", topic=all_data_string_for_funds_agent
        )

        capitalization = (
            float(tokenomics_data.capitalization)
            if tokenomics_data and tokenomics_data.capitalization
            else (phrase_by_language("no_data", language))
        )
        fundraising_amount = (
            float(investing_metrics.fundraise)
            if investing_metrics and investing_metrics.fundraise
            else (phrase_by_language("no_data", language))
        )
        investors_percent = float(funds_agent_answer.strip("%")) / 100

        if isinstance(capitalization, float) and isinstance(
            fundraising_amount, float
        ):
            result_ratio = (
                capitalization * investors_percent
            ) / fundraising_amount
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

        tier_answer = determine_project_tier(
            capitalization=tokenomics_data.fdv
            if tokenomics_data and tokenomics_data.fdv
            else "N/A",
            fundraising=investing_metrics.fundraise
            if investing_metrics and investing_metrics.fundraise
            else "N/A",
            twitter_followers=social_metrics.twitter
            if social_metrics and social_metrics.twitter
            else "N/A",
            twitter_score=social_metrics.twitterscore
            if social_metrics and social_metrics.twitterscore
            else "N/A",
            category=project.category
            if project and project.category
            else "N/A",
            investors=investing_metrics.fund_level
            if investing_metrics and investing_metrics.fund_level
            else "N/A",
            language=language,
        )

        if existing_answer is None:
            data_for_tokenomics = []
            for (
                index,
                coin_name,
                project_coin,
                expected_x,
                fair_price,
            ) in row_data:
                ticker = project_coin
                growth_percent = expected_x
                data_for_tokenomics.append(
                    {ticker: {"growth_percent": growth_percent}}
                )

            tokemonic_answer, tokemonic_score = calculate_tokenomics_score(
                project.coin_name, data_for_tokenomics
            )
            project_rating_result = calculate_project_score(
                investing_metrics.fundraise
                if investing_metrics and investing_metrics.fundraise
                else 0.0,
                f"{tier_answer}",
                investors_level_score,
                social_metrics.twitter
                if social_metrics and social_metrics.twitter
                else 0,
                social_metrics.twitterscore
                if social_metrics and social_metrics.twitterscore
                else 0.0,
                tokemonic_score if tokemonic_score else 0.0,
                int(
                    (network_metrics.tvl / tokenomics_data.capitalization)
                    * 100
                )
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
                funds_score if funds_score else "N/A",
                language,
            )

            project_rating_answer = project_rating_result["calculations_summary"]
            fundraising_score = project_rating_result["fundraising_score"]
            followers_score = project_rating_result["followers_score"]
            twitter_engagement_score = project_rating_result["twitter_engagement_score"]
            tokenomics_score = project_rating_result["tokenomics_score"]
            overal_final_score = project_rating_result["preliminary_score"]
            project_rating_text = project_rating_result["project_rating"]

            all_data_string_for_flags_agent = (
                ALL_DATA_STRING_FLAGS_AGENT.format(
                    project_coin_name=project.coin_name,
                    project_category=project.category,
                    tier_answer=tier_answer,
                    tokemonic_answer=tokemonic_answer,
                    funds_answer=funds_answer,
                    project_rating_answer=project_rating_answer,
                    social_metrics_twitter=social_metrics.twitter,
                    twitter_link=twitter_name,
                    social_metrics_twitterscore=social_metrics.twitterscore,
                )
            )

            flags_answer = await generate_flags_answer(
                user_id,
                all_data_string_for_flags_agent,
                project,
                tokenomics_data,
                investing_metrics,
                social_metrics,
                funds_profit,
                market_metrics,
                manipulative_metrics,
                network_metrics,
                tier_answer,
                funds_answer,
                tokemonic_answer,
                categories,
                twitter_link,
                top_and_bottom,
                language,
            )

            answer = flags_answer
            answer = answer.replace("**", "")
            answer += DATA_FOR_ANALYSIS_TEXT + comparison_results
            answer = re.sub(r"\n\s*\n", "\n", answer)

            red_green_flags = extract_red_green_flags(answer, language)
            calculations = extract_calculations(answer, language)

            top_and_bottom_answer = await phrase_by_user(
                "top_bottom_values",
                message.from_user.id,
                session_local,
                current_value=round(basic_metrics.market_price, 4),
                min_value=phrase_by_language("no_data", language),
                max_value=phrase_by_language("no_data", language),
            )

            if (
                top_and_bottom
                and top_and_bottom.lower_threshold
                and top_and_bottom.upper_threshold
            ):
                top_and_bottom_answer = await phrase_by_user(
                    "top_bottom_values",
                    message.from_user.id,
                    session_local,
                    current_value=round(basic_metrics.market_price, 4),
                    min_value=round(top_and_bottom.lower_threshold, 4),
                    max_value=round(top_and_bottom.upper_threshold, 4),
                )

            profit_text = await phrase_by_user(
                "investor_profit_text",
                message.from_user.id,
                session_local,
                fdv=f"{fdv:,.2f}"
                if isinstance(fdv, float)
                else fdv,
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
                print(funds_profit, funds_profit.distribution)
                distribution_items = funds_profit.distribution.split("\n")
                print(distribution_items)
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
                    f"{get_metric_value(social_metrics, 'twitter')} ({twitter_name[0]})"
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
            project_evaluation = await phrase_by_user(
                "project_rating_details",
                user_id,
                session_local,
                fundraising_score=round(fundraising_score, 2),
                tier=investors_level,
                tier_score=investors_level_score,
                followers_score=int(followers_score),
                twitter_engagement_score=round(twitter_engagement_score, 2),
                tokenomics_score=tokenomics_score,
                profitability_score=round(funds_score, 2),
                preliminary_score=int(growth_and_fall_score),
                top_100_percent=round(
                    manipulative_metrics.top_100_wallet * 100, 2
                )
                if manipulative_metrics and manipulative_metrics.top_100_wallet
                else 0,
                tvl_percent=int(
                    (network_metrics.tvl / tokenomics_data.capitalization)
                    * 100
                )
                if network_metrics
                and network_metrics.tvl
                and tokenomics_data
                and tokenomics_data.total_supply
                and tokenomics_data.capitalization
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
                coin_name=coin_name.upper(),
            )

        else:
            flags_answer = existing_answer.answer

            match = re.search(PROJECT_POINTS_ENG, flags_answer)

            if language == "RU":
                match = re.search(PROJECT_POINTS_RU, flags_answer)

            overal_final_score = phrase_by_language(
                "no_project_rating", language
            )
            project_rating_text = phrase_by_language(
                "no_project_score", language
            )

            if match:
                overal_final_score = float(match.group(1))  # Извлекаем баллы
                project_rating_text = match.group(2)  # Извлекаем оценку
                print(f"Итоговые баллы: {overal_final_score}")
                print(f"Оценка проекта: {project_rating_text}")

            pdf_output, extracted_text = create_pdf_file(
                existing_calculation, language, flags_answer
            )

        if not existing_answer or (
            existing_answer and not existing_answer.answer
        ):
            new_answer = AgentAnswer(
                project_id=project.id, answer=extracted_text, language=language
            )
            session.add(new_answer)

        existing_calculation.agent_answer = extracted_text
        session.add(existing_calculation)

        await session.commit()
        await state.set_state(CalculateProject.waiting_for_data)

        return (
            phrase_by_language("project_analysis_result", language).format(
                lower_name=lower_name.capitalize(),
                project_score=overal_final_score,
                project_rating=project_rating_text,
            ),
            pdf_output,
            f"{phrase_by_language('analyse_filename', language).format(token_name=lower_name.capitalize())}.pdf",
        )

    except ValueProcessingError as processing_error:
        error_message = str(processing_error)
        logging.error(f"ValueProcessingError: {error_message}")

        return f"{await phrase_by_user('error_not_valid_input_data', message.from_user.id, session_local)}\n{error_message}"
