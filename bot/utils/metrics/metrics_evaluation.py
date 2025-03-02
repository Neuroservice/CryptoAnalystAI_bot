from typing import Any

from bot.utils.common.consts import (
    TIER_RANK,
    TIER_CRITERIA,
    TIER_RANK_LIST,
    RESULT_STRING,
    FUNDRAISING_DIVISOR,
    FOLLOWERS_DIVISOR,
    TWITTER_SCORE_MULTIPLIER,
    TIER_COEFFICIENTS,
    CALCULATIONS_SUMMARY_STR,
    LEVEL_TO_SCORE,
    NO_COEFFICIENT,
)
from bot.utils.project_data import get_project_rating
from bot.utils.resources.bot_phrases.bot_phrase_handler import (
    phrase_by_language,
)
from bot.utils.validations import clean_twitter_subs, process_metric


def determine_project_tier(
    capitalization: float,
    fundraising: float,
    twitter_followers: str,
    twitter_score: int,
    investors: str,
    language: str,
):
    """
    Функция определения тира проекта.
    Принимает данные о проекте (капитализация, фандрейз, кол-во подписчиков в твиттере,
    баллы твиттерскора, категория, инвесторы). На основе этих входящих метрик делает сравнение с
    минимальными требованиями для каждого тира. Определяет общий тир проекта и возвращает его.
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

    parsed_investors = []
    if isinstance(investors, str):
        investors = [inv.strip() for inv in investors.split(",")]

    for investor in investors:
        if "(" in investor and ")" in investor:
            name, tier = investor.rsplit("(", 1)
            tier = tier.strip(")").replace("+", "").strip()  # Убираем "+" и пробелы

            # Приводим к формату "Tier: {цифра}"
            if tier.upper().startswith("TIER"):
                tier = tier.split()[-1]  # Берем число после "TIER"
            if tier.isdigit():
                tier = f"Tier: {tier}"

            parsed_investors.append(tier)

    investor_counts = {tier: 0 for tier in TIER_RANK}
    for tier in parsed_investors:
        if tier in TIER_RANK:
            investor_counts[tier] += 1

    # Determine tier
    for tier, criteria in TIER_CRITERIA.items():

        # Проверка всех основных метрик
        passes_metrics = (
            capitalization != "N/A"
            and int(capitalization) >= int(criteria["capitalization"])
            and fundraising != "N/A"
            and int(fundraising) >= int(criteria["fundraising"])
            and twitter_followers != "N/A"
            and int(clean_twitter_subs(twitter_followers)) >= int(clean_twitter_subs(criteria["twitter_followers"]))
            and twitter_score != "N/A"
            and int(twitter_score) >= int(criteria["twitter_score"])
        )

        if not passes_metrics:
            print(f"Metrics do not fit for {tier}, moving to the next tier.")
            continue

        if "Tier: 1" in parsed_investors:
            return "Tier 1"
        elif "Tier: 2" in investor_counts:
            return "Tier 2"
        elif "Tier: 3" in investor_counts:
            return "Tier 3"
        elif "Tier: 4" in investor_counts:
            return "Tier 4"

    print("Project does not fit into any tier, assigning TIER 5.")
    return "Tier 5"


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

        tvl_result = f"Проект {'потерял' if tvl_score == 0 else 'получил'} {tvl_score} баллов по показателю процента заблокированных монет.\n"
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
    Получает строку с инвесторами и определяет общий тир инвесторов.
    """

    # Парсинг инвесторов
    parsed_investors = []
    if isinstance(investors, str):
        investors = [inv.strip() for inv in investors.split(",")]

    for investor in investors:
        if "(" in investor and ")" in investor:
            name, tier = investor.rsplit("(", 1)
            tier = tier.strip(")").replace("+", "").strip()

            # Приводим к формату "Tier: {цифра}"
            if tier.upper().startswith("TIER"):
                tier = tier.split()[-1]  # Берем число после "TIER"
            if tier.isdigit():
                tier = f"Tier: {tier}"

            parsed_investors.append(tier)

    # Считаем количество фондов по каждому Тиру
    investor_counts = {tier: 0 for tier in TIER_RANK_LIST}
    for tier in parsed_investors:
        if tier in TIER_RANK_LIST:
            investor_counts[tier] += 1

    # Определяем общий уровень инвесторов
    investor_level = 5  # По умолчанию Tier 5 (наименьший)
    for tier in TIER_RANK_LIST:  # Проходим по тиру от 1 до 5
        if investor_counts[tier] > 0:
            investor_level = int(tier.split(": ")[1])  # Берем номер тира
            break  # Как только нашли — останавливаемся

    score = LEVEL_TO_SCORE[investor_level]

    return {
        "level": investor_level,
        "score": score,
        "details": investor_counts,
    }


def calculate_project_score(
    fundraising: float,
    tier: str,
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
        tier_score=tier,
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
