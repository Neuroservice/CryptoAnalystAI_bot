import logging
from typing import Any

from bot.utils.project_data import get_project_rating
from bot.utils.validations import clean_twitter_subs, process_metric
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_language
from bot.utils.common.consts import (
    TIER_CRITERIA,
    RESULT_STRING,
    FUNDRAISING_DIVISOR,
    FOLLOWERS_DIVISOR,
    TWITTER_SCORE_MULTIPLIER,
    CALCULATIONS_SUMMARY_STR,
    LEVEL_TO_SCORE,
)


def determine_project_tier(
    capitalization: float,
    fundraising: float,
    twitter_followers: str,
    twitter_score: int,
    investors: str,
    language: str,
):
    """
    Функция определения тира проекта. Сначала вычисляет тир на основе метрик,
    а затем смотрит на тир инвесторов. Если инвесторы «хуже» (больше по числу),
    то итоговый тир повышается до их уровня.

    Пример:
    - Если по метрикам проект Tier 3, а инвесторы Tier 2 -> итог будет Tier 3.
    - Если по метрикам проект Tier 2, а инвесторы Tier 3 -> итог будет Tier 3.
    """

    if any(
        value in ("N/A", None, "")
        for value in [
            capitalization,
            fundraising,
            twitter_followers,
            twitter_score,
            investors,
        ]
    ):
        return phrase_by_language("no_data", language)

    metrics_tier = 5
    for tier_name, criteria in TIER_CRITERIA.items():
        passes_metrics = (
            int(capitalization) >= int(criteria["capitalization"])
            and int(fundraising) >= int(criteria["fundraising"])
            and int(clean_twitter_subs(twitter_followers)) >= int(clean_twitter_subs(criteria["twitter_followers"]))
            and int(twitter_score) >= int(criteria["twitter_score"])
        )
        if passes_metrics:
            metrics_tier = int(tier_name.split()[-1])
            break

    investors_level_data = project_investors_level(investors)
    investors_tier = investors_level_data["level"]

    final_tier = max(metrics_tier, investors_tier)

    if final_tier == 5:
        print("Project does not fit into any tier, assigning Tier 5.")
        return "Tier 5"

    return f"Tier {final_tier}"


def calculate_tokenomics_score(project_name: str, comparisons: list[dict[str, dict[str, Any]]]):
    """
    Функция расчета баллов по оценке токеномики проекта.
    """

    total_score = 0
    results = []

    for comparison in comparisons:
        for ticker, data in comparison.items():
            if ticker != project_name:
                growth_percent = data.get("growth_percent", 0)

                if abs(growth_percent) <= 1:
                    score = 0
                else:
                    score = round(growth_percent / 10, 2)

                total_score += score
                results.append(f"{ticker} = {score} баллов")

    total_score = max(-50, min(100, round(total_score, 2)))

    result_string = RESULT_STRING.format(
        project_name=project_name,
        total_score=total_score,
        results=",\n".join(results),
    )

    return result_string, total_score


def analyze_project_metrics(
    final_score: float,
    growth_percentage: float,
    fall_percentage: float,
    top_100_percentage: float,
    tvl_percentage: float,
):
    """
    Функция анализа проекта по показателям.
    """

    tvl_score = 0
    top_100_score = 0
    growth_and_fall_score = 0
    funds_score = 0

    growth_and_fall_result = ""
    detailed_report = ""

    print("final_score: ", final_score)

    if type(final_score) is not float and final_score != "Нет данных":
        final_score = float(final_score[:-1])

    if final_score and type(final_score) is float:
        if final_score <= 200:
            funds_score = final_score / 20
            detailed_report += f"  Баллы доходности фондов = Процент доходности фондов / 20 = {funds_score}\n"
        elif 201 <= final_score <= 1000:
            funds_score = (200 / 20) + ((final_score - 200) / 100) * (-0.5)
            detailed_report += (
                f"  Баллы доходности фондов = (200 / 20) + (({final_score} - 200) / 100) * (-0.5) = {funds_score}\n"
            )
        elif 1001 <= final_score <= 3000:
            funds_score = (200 / 20) + (800 / 100) * (-0.5) + ((final_score - 1000) / 100) * (-1)
            detailed_report += f"  Баллы доходности фондов = (200 / 20) + (800 / 100) * (-0.5) + (({final_score} - 1000) / 100) * (-1) = {funds_score}\n"
        elif 3001 <= final_score <= 5000:
            funds_score = (200 / 20) + (800 / 100) * (-0.5) + (2000 / 100) * (-1) + ((final_score - 3000) / 100) * (-1.5)
            detailed_report += f"  Баллы доходности фондов = (200 / 20) + (800 / 100) * (-0.5) + (2000 / 100) * (-1) + (({final_score} - 3000) / 100) * (-1.5) = {funds_score}\n"
        elif final_score > 5000:
            funds_score = (
                (200 / 20)
                + (800 / 100) * (-0.5)
                + (2000 / 100) * (-1)
                + (2000 / 100) * (-1.5)
                + ((final_score - 5000) / 100) * (-2)
            )
            detailed_report += f"  Баллы доходности фондов = (200 / 20) + (800 / 100) * (-0.5) + (2000 / 100) * (-1) + (2000 / 100) * (-1.5) + (({final_score} - 5000) / 100) * (-2) = {funds_score}\n"

        funds_score = max(min(funds_score, 100), -50)
        funds_result = f"По показателю доходности фондов проект получает {round(funds_score, 2)} баллов.\n"
    else:
        funds_result = "Данные для расчета средней цены и доходности фондов отсутствуют. 0 баллов.\n"

    # Логика расчета роста и падения
    if growth_percentage != "N/A" and fall_percentage != "N/A":
        growth_and_fall_score = fall_percentage - growth_percentage

        if growth_and_fall_score < -50:
            growth_and_fall_score = -50
            detailed_report += (
                f"\n[Growth and Fall Calculation]:\n"
                f"  Падение: {fall_percentage} - Рост: {growth_percentage} = {growth_and_fall_score} (баллы оказались меньше 50, выставлено значение -50)\n"
            )
        elif growth_and_fall_score > 100:
            growth_and_fall_score = 100
            detailed_report += (
                f"\n[Growth and Fall Calculation]:\n"
                f"  Падение: {fall_percentage} - Рост: {growth_percentage} = {growth_and_fall_score} баллы оказались больше 100, выставлено значение 100)\n"
            )
        else:
            detailed_report += (
                f"\n[Growth and Fall Calculation]:\n"
                f"  Падение: {fall_percentage} - Рост: {growth_percentage} = {growth_and_fall_score}\n"
            )

            growth_and_fall_result = f"Проект {'потерял' if growth_and_fall_score < 0 else 'получил'} {round(abs(growth_and_fall_score), 2)} баллов по показателю роста от минимальных значений и падения от максимальных значений.\n"
    else:
        growth_and_fall_result = "Данные для расчета роста и падения отсутствуют. 0 баллов.\n"

    # Логика расчета топ-100 кошельков
    if top_100_percentage != "N/A":
        top_100_score = max(0, int(top_100_percentage) - 70)
        detailed_report += (
            f"\n[Top 100 Wallets Calculation]:\n"
            f"  Процент монет на топ-100 кошельках: {top_100_percentage}%\n"
            f"  Баллы рассчитываются как: max(0, {top_100_percentage} - 70)\n"
            f"  Здесь max() возвращает большее из двух значений: либо 0, либо ({top_100_percentage} - 70).\n"
            f"  Итоговые баллы: {top_100_score}\n"
        )

        top_100_result = f"Проект {'потерял' if top_100_score == 0 else 'получил'} {top_100_score} баллов по показателю процента монет на топ 100 кошельков.\n"
    else:
        top_100_result = "Данные для расчета процента монет на топ 100 кошельков отсутствуют. 0 баллов.\n"

    # Логика расчета TVL
    if tvl_percentage != "N/A":
        tvl_score = int(tvl_percentage)
        detailed_report += (
            f"\n[TVL Calculation]:\n"
            f"  Процент заблокированных монет (TVL): {tvl_percentage}\n"
            f"  Баллы = {tvl_percentage}\n"
        )

        tvl_result = f"Проект {'потерял' if tvl_score < 0 else 'получил'} {tvl_score} баллов по показателю процента заблокированных монет.\n"
    else:
        tvl_result = "Данные для расчета процента заблокированных монет отсутствуют. 0 баллов.\n"

    # Общий отчет
    report = funds_result + growth_and_fall_result + top_100_result + tvl_result
    detailed_report += report

    total_score = tvl_score + top_100_score + growth_and_fall_score + funds_score
    detailed_report += f"\n[Total Score]: {total_score}\n"

    return detailed_report, total_score, funds_score, growth_and_fall_score


def project_investors_level(investors: str):
    """
    Получает строку с инвесторами и определяет общий (худший) тир инвесторов.
    Если нет подходящих инвесторов, будет Tier 5 по умолчанию.
    """

    investors_tier = 5
    if isinstance(investors, str):
        investors_list = [inv.strip() for inv in investors.split(",")]
    else:
        investors_list = investors

    parsed_investors = []
    for investor in investors_list:
        if "(" in investor and ")" in investor:
            name, raw_tier = investor.rsplit("(", 1)
            raw_tier = raw_tier.strip(")").replace("+", "").strip()

            if raw_tier.upper().startswith("TIER"):
                raw_tier = raw_tier.split()[-1]

            if raw_tier.isdigit():
                tier = int(raw_tier)
                parsed_investors.append(tier)

    if parsed_investors:
        investors_tier = min(parsed_investors)

    score = LEVEL_TO_SCORE[investors_tier]

    print(f"\n\n {investors_tier, score} \n\n")

    return {
        "level": investors_tier,
        "score": score,
    }


def calculate_project_score(
    fundraising: float,
    tier: str,
    investors_tier: str,
    investors_level_score: int,
    twitter_followers: str,
    twitter_score: int,
    tokenomics_score: float,
    tvl: int,
    top_100_wallet: float,
    growth_and_fall_score: int,
    profitability_score: float,
    language: str,
):
    """
    Функция расчета баллов по метрикам проекта.
    """

    logging.info(f"----- project {fundraising} {tier} {investors_tier} {twitter_followers} {twitter_followers} {twitter_score} {tokenomics_score} {tvl} {top_100_wallet} {growth_and_fall_score} {profitability_score} {language}")

    # Обработка значений с использованием process_metric
    fundraising = process_metric(fundraising)
    twitter_followers = process_metric(clean_twitter_subs(twitter_followers))
    twitter_score = process_metric(twitter_score)
    tokenomics_score = process_metric(tokenomics_score)
    profitability_score = process_metric(profitability_score)

    fundraising_score = round(fundraising / FUNDRAISING_DIVISOR, 2)
    followers_score = round(twitter_followers / FOLLOWERS_DIVISOR, 2)
    twitter_engagement_score = round(twitter_score * TWITTER_SCORE_MULTIPLIER, 2)

    preliminary_score = round(
        fundraising_score
        + investors_level_score
        + followers_score
        + twitter_engagement_score
        + tokenomics_score
        + tvl
        + top_100_wallet
        + growth_and_fall_score
        + profitability_score,
        2,
    )

    calculations_summary = CALCULATIONS_SUMMARY_STR.format(
        fundraising_score=fundraising_score,
        tier=investors_tier,
        tier_score=investors_level_score,
        followers_score=followers_score,
        twitter_engagement_score=twitter_engagement_score,
        tokenomics_score=tokenomics_score,
        profitability_score=profitability_score,
        final_score=preliminary_score,
    )

    project_rating = get_project_rating(preliminary_score, language)

    return {
        "fundraising_score": fundraising_score,
        "tier_score": tier,
        "followers_score": followers_score,
        "twitter_engagement_score": twitter_engagement_score,
        "tokenomics_score": tokenomics_score,
        "profitability_score": profitability_score,
        "preliminary_score": preliminary_score,
        "project_rating": project_rating,
        "calculations_summary": calculations_summary,
    }
