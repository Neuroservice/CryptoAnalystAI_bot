import re
import asyncio
import logging
import datetime
import traceback

from tenacity import retry, stop_after_attempt, wait_fixed

from bot.utils.resources.files_worker.pdf_worker import generate_pdf
from bot.utils.resources.gpt.gpt import agent_handler
from bot.data_processing.data_pipeline import (
    update_static_data,
    update_weekly_data,
    update_dynamic_data,
    update_current_price,
)
from bot.database.db_operations import (
    get_one,
    update_or_create,
    get_all,
    get_or_create,
)
from bot.database.models import (
    Project,
    AgentAnswer,
    Category,
)
from bot.utils.common.consts import (
    DATA_FOR_ANALYSIS_TEXT,
    ALL_DATA_STRING_FUNDS_AGENT,
    ALL_DATA_STRING_FLAGS_AGENT,
    START_TITLE_FOR_GARBAGE_CATEGORIES,
    END_TITLE_FOR_GARBAGE_CATEGORIES,
)
from bot.utils.metrics.metrics_evaluation import (
    determine_project_tier,
    calculate_tokenomics_score,
    analyze_project_metrics,
    calculate_project_score,
    project_investors_level,
)
from bot.utils.project_data import (
    get_twitter_link_by_symbol,
    get_user_project_info,
    get_project_and_tokenomics,
    calculate_expected_x,
    generate_flags_answer,
    get_coin_description,
    get_top_projects_by_capitalization_and_category,
)
from bot.utils.resources.bot_phrases.bot_phrase_handler import (
    phrase_by_language,
)
from bot.utils.resources.bot_phrases.bot_phrase_strings import (
    calculations_choices,
)
from bot.utils.resources.files_worker.google_doc import (
    load_document_for_garbage_list,
)
from bot.utils.validations import (
    extract_red_green_flags,
    extract_calculations,
    format_metric,
    get_metric_value,
)

logging.basicConfig(level=logging.INFO)
current_day = datetime.datetime.now(datetime.timezone.utc).day


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def fetch_crypto_data():
    """
    Асинхронный эндпоинт для получения данных о криптопроектах.
    Запускает три фоновых обновления:
    - `update_static_data` (раз в 3 месяца)
    - `update_weekly_data` (раз в неделю)
    - `update_dynamic_data` (ежедневно)
    - `update_current_price` (раз в 6 часов)
    """
    try:
        logging.info("Starting fetch_crypto_data...")

        asyncio.create_task(update_static_data())
        asyncio.create_task(update_weekly_data())
        asyncio.create_task(update_dynamic_data())
        asyncio.create_task(periodically_update_answers())
        asyncio.create_task(update_current_price())

        logging.info("All update tasks started successfully.")

    except Exception as e:
        logging.error(f"Critical error in fetch_crypto_data: {e}")
        logging.error(f"Exception type: {type(e).__name__}")
        logging.error("Traceback:")
        logging.error(traceback.format_exc())


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def update_agent_answers():
    """
    Функция обновления ответов агентов по каждому токену:
    1. Собирает данные по проекту
    2. Получает анализ от LLM по этим метрикам
    3. Сохраняет новый ответ
    """

    current_time = datetime.datetime.now(datetime.timezone.utc)
    current_time_naive = current_time.replace(tzinfo=None)
    one_days_ago = (current_time - datetime.timedelta(days=1)).replace(tzinfo=None)
    current_date = current_time.strftime("%d.%m.%Y")

    # Начальные переменные
    data_for_tokenomics = []

    logging.info("=== Начало update_agent_answers() ===")
    logging.info(f"Текущая дата/время: {current_time.isoformat()}")
    logging.info(f"Будем обновлять ответы, у которых updated_at <= {one_days_ago.isoformat()}")

    # Загружаем мусорные категории
    logging.info("Загружаем список категорий (garbage_categories)...")
    garbage_categories = load_document_for_garbage_list(
        START_TITLE_FOR_GARBAGE_CATEGORIES,
        END_TITLE_FOR_GARBAGE_CATEGORIES,
    )
    logging.info(f"garbage_categories загружено, размер: {len(garbage_categories)}")

    logging.info("Получаем все устаревшие AgentAnswer (outdated_answers)...")
    outdated_answers = await get_all(
        AgentAnswer,
        updated_at=lambda col: col <= one_days_ago
    )
    logging.info(f"Найдено {len(outdated_answers)} устаревших ответов для обновления")

    for agent_answer in outdated_answers:
        logging.info(f"--- Обработка agent_answer.id={agent_answer.id} / project_id={agent_answer.project_id} ---")

        # 1. Ищем Project
        project = await get_one(Project, id=agent_answer.project_id)
        if not project:
            logging.warning(f"Project не найден для project_id={agent_answer.project_id}, пропускаем.")
            continue

        logging.info(f"Обновляем ответ агента по проекту: {project.coin_name}")

        # 2. Определяем язык
        first_phrase = agent_answer.answer.split(" ", 1)[0]

        if first_phrase.startswith("Анализ"):
            language = "RU"
        else:
            language = "ENG"

        logging.info(f"Определён язык: {language}")

        # 3. Получаем твиттер и описание
        twitter_name, description, lower_name, categories = await get_twitter_link_by_symbol(project.coin_name)
        coin_description = await get_coin_description(lower_name)
        if description:
            coin_description += description

        logging.info(f"[{project.coin_name}] Длина coin_description: {len(coin_description)} символов")

        # 4. Генерируем общее описание токена
        token_description = await agent_handler("description", topic=coin_description, language=language)
        logging.info(f"[{project.coin_name}] token_description (AI) получен, длина={len(token_description)}")

        if not categories or len(categories) == 0:
            logging.warning(f"[{project.coin_name}] Нет категорий у проекта, пропускаем.")
            continue

        # 5. Получаем или создаем категории (не входящие в мусорный список)
        category_instances = []
        logging.info(f"[{project.coin_name}] Обрабатываем {len(categories)} категорий...")
        for category_name in categories:
            if category_name not in garbage_categories:
                category_instance, _ = await get_or_create(Category, category_name=category_name)
                category_instances.append(category_instance)

        if len(category_instances) == 0:
            logging.warning(f"[{project.coin_name}] Все категории оказались в мусорном списке, пропускаем.")
            continue

        # 6. Собираем данные проекта
        project_info = await get_user_project_info(project.coin_name)
        logging.info(f"[{project.coin_name}] Получен project_info: {list(project_info.keys())}")

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

        # 7. Получаем список проектов с токеномикой
        _, tokenomics_data_list = await get_project_and_tokenomics(categories, project.tier)
        logging.info(f"[{project.coin_name}] Получено {len(tokenomics_data_list)} проектов c токеномикой.")

        # Берём топ-5 проектов по капитализации
        top_projects = get_top_projects_by_capitalization_and_category(tokenomics_data_list)
        logging.info(f"[{project.coin_name}] Топ-5 проектов для сравнения, всего {len(top_projects)}.")

        # 8. Генерируем текст сравнения
        comparison_results = ""
        for index, (top_proj, tok_data_list) in enumerate(top_projects, start=1):
            if tok_data_list:
                logging.info(f"[{project.coin_name}] Сравнение с проектом {top_proj.coin_name} (index={index}).")
                for tok_data in tok_data_list:
                    # Собираем данные
                    entry_price = basic_metrics.market_price
                    total_supply = tok_data.total_supply
                    fdv = tok_data.fdv

                    # Логируем текущие значения
                    logging.info(
                        f"[{project.coin_name}] entry_price={entry_price}, "
                        f"total_supply={total_supply}, fdv={fdv} "
                        f"(для проекта {top_proj.coin_name})"
                    )

                    # Общая проверка: если что-то из нужных полей отсутствует — пропускаем
                    if entry_price is None or total_supply is None or fdv is None:
                        logging.warning(
                            f"[{project.coin_name}] Недостаточно данных (entry_price or total_supply or fdv == None), "
                            f"пропускаем расчёт для {top_proj.coin_name}."
                        )
                        continue

                    # Если дошли сюда, значит все три значения не None
                    calculation_result = calculate_expected_x(
                        entry_price=entry_price,
                        total_supply=total_supply,
                        fdv=fdv,
                    )

                    fair_price = calculation_result["fair_price"]
                    if isinstance(fair_price, (int, float)):
                        fair_price = f"{fair_price:.5f}"
                    else:
                        fair_price = phrase_by_language("comparisons_error", agent_answer.language)

                    # Формируем итоговое сообщение о сравнении
                    comparison_results += calculations_choices[agent_answer.language].format(
                        user_coin_name=project.coin_name,
                        project_coin_name=top_proj.coin_name,
                        growth=(calculation_result["expected_x"] - 1.0) * 100,
                        fair_price=fair_price,
                    )

        # 9. Определяем tier проекта
        tier_answer = determine_project_tier(
            capitalization=get_metric_value(tokenomics_data, "fdv"),
            fundraising=get_metric_value(investing_metrics, "fundraise"),
            twitter_followers=get_metric_value(social_metrics, "twitter"),
            twitter_score=get_metric_value(social_metrics, "twitterscore"),
            investors=get_metric_value(investing_metrics, "fund_level"),
            language=language,
        )
        logging.info(f"[{project.coin_name}] Tier: {tier_answer}")

        # 10. Запускаем токеномику
        tokemonic_answer, tokemonic_score = calculate_tokenomics_score(
            project.coin_name,
            data_for_tokenomics
        )
        logging.info(f"[{project.coin_name}] токеномика: {tokemonic_answer} / score={tokemonic_score}")

        # 11. Запрашиваем у агента данные по фондам
        all_data_string_for_funds_agent = ALL_DATA_STRING_FUNDS_AGENT.format(
            funds_profit_distribution=get_metric_value(funds_profit, "distribution")
        )
        try:
            funds_agent_answer = await agent_handler("funds_agent", topic=all_data_string_for_funds_agent)
            logging.info(
                f"[{project.coin_name}] funds_agent_answer: '{funds_agent_answer}' (тип: {type(funds_agent_answer)}, длина: {len(str(funds_agent_answer)) if funds_agent_answer else 0})")

            if not funds_agent_answer or not str(funds_agent_answer).strip() or str(funds_agent_answer).strip() == "0":
                logging.warning(f"[{project.coin_name}] Пустой или нулевой ответ от funds_agent")
                funds_agent_answer = "0%"
        except Exception as e:
            logging.error(f"[{project.coin_name}] Ошибка получения funds_agent_answer: {e}")
            funds_agent_answer = "0%"

        # 12. Считаем FDV / fundraising_amount
        fdv = (
            float(tokenomics_data.fdv)
            if tokenomics_data and tokenomics_data.fdv
            else phrase_by_language("no_data", language)
        )

        logging.info(f"investing_metrics.fundraise -------------- {investing_metrics.fundraise}")
        try:
            fundraising_amount = (
                float(investing_metrics.fundraise)
                if (investing_metrics and
                    hasattr(investing_metrics, 'fundraise') and
                    str(investing_metrics.fundraise).strip().lower() not in ["", "none", "no data", "nan"])
                else 0
            )
            logging.info(f"fundraising_amount --- {fundraising_amount}")
        except (ValueError, AttributeError) as e:
            logging.error(f"[{project.coin_name}] Ошибка преобразования fundraising_amount: {e}")
            fundraising_amount = 0

        # Инвесторы (строка вида "30%"?) — парсим
        investors_percent_str = funds_agent_answer.strip("%") if funds_agent_answer else "0"
        try:
            investors_percent = float(investors_percent_str) / 100
        except ValueError:
            logging.warning(f"[{project.coin_name}] Не удалось привести {investors_percent_str} к float, ставим 0.")
            investors_percent = 0

        logging.info(f"[{project.coin_name}] fdv={fdv}, fundraising={fundraising_amount}, investors_percent={investors_percent}")

        result_ratio = phrase_by_language("no_data", language)
        final_score = result_ratio

        try:
            if all([
                isinstance(fdv, (int, float)),
                isinstance(fundraising_amount, (int, float)) and fundraising_amount != 0,
                isinstance(investors_percent, (int, float))
            ]):
                result_ratio = (fdv * investors_percent) / fundraising_amount
                final_score = f"{result_ratio:.2%}"

        except Exception as e:
            logging.error(f"[{project.coin_name}] Ошибка расчета result_ratio. "
                          f"fdv={fdv}({type(fdv)}), "
                          f"fundraising={fundraising_amount}({type(fundraising_amount)}), "
                          f"investors={investors_percent}({type(investors_percent)}). Ошибка: {e}")

        logging.info(f"[{project.coin_name}] result_ratio={result_ratio}, final_score={final_score}")

        if isinstance(final_score, str):
            if '%' in final_score:
                final_score = float(final_score.strip('%')) / 100
            else:
                final_score = final_score
        else:
            final_score = float(final_score)

        logging.info(f"final score {final_score}")

        # analyze_project_metrics => funds_answer etc.
        (funds_answer, funds_scores, funds_score, growth_and_fall_score,) = analyze_project_metrics(
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
                transform=lambda tvl: (tvl / tokenomics_data.capitalization) * 100
                if tokenomics_data and tokenomics_data.capitalization
                else None,
            ),
        )

        # 13. Определяем уровень инвесторов
        if investing_metrics and investing_metrics.fund_level:
            project_investors_level_result = project_investors_level(
                investors=investing_metrics.fund_level
            )
            investors_level = project_investors_level_result["level"]
            investors_level_score = project_investors_level_result["score"]
        else:
            investors_level = phrase_by_language("no_data", language)
            investors_level_score = 0

        logging.info(f"[{project.coin_name}] investors_level={investors_level}, investors_level_score={investors_level_score}")

        # 14. Считаем рейтинг проекта
        project_rating_result = calculate_project_score(
            get_metric_value(investing_metrics, "fundraise"),
            tier_answer,
            investors_level,
            investors_level_score,
            get_metric_value(social_metrics, "twitter"),
            get_metric_value(social_metrics, "twitterscore"),
            int((network_metrics.tvl / tokenomics_data.capitalization) * 100)
            if network_metrics.tvl
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
        logging.info(f"[{project.coin_name}] Итоги rating: {project_rating_result}")

        project_rating_answer = project_rating_result["calculations_summary"]
        fundraising_score = project_rating_result["fundraising_score"]
        followers_score = project_rating_result["followers_score"]
        twitter_engagement_score = project_rating_result["twitter_engagement_score"]
        overal_final_score = project_rating_result["preliminary_score"]
        tokenomics_score = project_rating_result["tokenomics_score"]
        project_rating_text = project_rating_result["project_rating"]

        logging.info(f"[{project.coin_name}] project_rating_answer: {project_rating_answer, project_rating_text}")

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

        logging.info(f"[{project.coin_name}] all_data_string_for_flags_agent: {all_data_string_for_flags_agent}")

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

        logging.info(f"[{project.coin_name}] flags_answer: {flags_answer}")

        answer = re.sub(
            r"\n\s*\n",
            "\n",
            flags_answer.replace("**", "") + DATA_FOR_ANALYSIS_TEXT + comparison_results,
        )

        red_green_flags = extract_red_green_flags(answer, language)
        calculations = extract_calculations(answer, language)

        logging.info(f"[{project.coin_name}] red_green_flags: {red_green_flags, calculations}")

        top_and_bottom_answer = phrase_by_language(
            "top_bottom_values",
            language,
            current_value=round(basic_metrics.market_price, 4),
            min_value=phrase_by_language("no_data", language),
            max_value=phrase_by_language("no_data", language),
        )

        logging.info(f"[{project.coin_name}] top_and_bottom_answer (1): {top_and_bottom_answer}")

        if top_and_bottom and top_and_bottom.lower_threshold and top_and_bottom.upper_threshold:
            top_and_bottom_answer = phrase_by_language(
                "top_bottom_values",
                language,
                current_value=round(basic_metrics.market_price, 4),
                min_value=round(top_and_bottom.lower_threshold, 4),
                max_value=round(top_and_bottom.upper_threshold, 4),
            )

            logging.info(f"[{project.coin_name}] top_and_bottom_answer (2): {top_and_bottom_answer}")

        profit_text = phrase_by_language(
            "investor_profit_text",
            language=language,
            fdv=f"{fdv:,.2f}" if isinstance(fdv, float) else fdv,
            investors_percent=f"{investors_percent:.0%}" if isinstance(investors_percent, float) else investors_percent,
            fundraising_amount=f"{fundraising_amount:,.2f}"
            if isinstance(fundraising_amount, float)
            else fundraising_amount,
            result_ratio=f"{result_ratio:.4f}" if isinstance(result_ratio, float) else result_ratio,
            final_score=final_score,
        )

        logging.info(f"profit_text: --- {profit_text}")

        if funds_profit and funds_profit.distribution:
            distribution_items = funds_profit.distribution.split("\n")
            formatted_distribution = "\n".join([f"- {item}" for item in distribution_items])
        else:
            formatted_distribution = phrase_by_language("no_token_distribution", language)

        logging.info(f"formatted_distribution: --- {formatted_distribution}")

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
            tvl_percent=int((network_metrics.tvl / tokenomics_data.capitalization) * 100)
            if network_metrics.tvl and tokenomics_data.total_supply
            else 0,
        )

        logging.info(f"project_evaluation ------------ {project_evaluation}")

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

        logging.info(f"[{project.coin_name}] Обновляем AgentAnswer.id={agent_answer.id}")
        await update_or_create(
            model=AgentAnswer,
            id=agent_answer.id,
            defaults={
                "answer": extracted_text,
                "updated_at": current_time_naive,
            },
        )

        logging.info(f"[{project.coin_name}] Успешно обновлён agent_answer, ждём 10 сек...")
        await asyncio.sleep(10)

    logging.info("=== update_agent_answers() завершена ===")


async def periodically_update_answers():
    """
    Задача обновления ответов модели. Выполняется раз в 12 часов
    """

    while True:
        try:
            logging.info("Обновление ответов")
            await update_agent_answers()
            logging.info("Конец обновления")
        except Exception as e:
            logging.error(f"Ошибка при обновлении ответов агентов: {e}")

        await asyncio.sleep(60 * 60 * 12)