from bot.utils.project_data import clean_fundraise_data, clean_twitter_subs


def determine_project_tier(
    capitalization, fundraising, twitter_followers, twitter_score, category, investors
):
    """
    Determine the tier of a project based on provided metrics.

    Parameters:
    - capitalization (float): The project's market capitalization in USD.
    - fundraising (float): Funds raised by the project in USD.
    - twitter_followers (int): Number of Twitter followers.
    - twitter_score (int): Twitter engagement score.
    - category (str): The project's category.
    - investors (list): List of investors with their tiers (e.g., "A16Z (TIER 1+)").

    Returns:
    - str: The tier of the project (e.g., "Tier 1", "Tier 2", etc.).
    """
    # Define tier criteria
    tier_criteria = {
        "Tier 1": {
            "capitalization": 1_000_000_000,
            "fundraising": 100_000_000,
            "twitter_followers": 500_000,
            "twitter_score": 300,
            "categories": [
                "Layer 1",
                "Layer 2 (ETH)",
                "Financial sector",
                "Infrastructure",
            ],
            "required_investors": {"TIER 1": 1, "TIER 2": 2},
        },
        "Tier 2": {
            "capitalization": 200_000_000,
            "fundraising": 50_000_000,
            "twitter_followers": 100_000,
            "twitter_score": 100,
            "categories": [
                "Layer 1 (OLD)",
                "DeFi",
                "Modular Blockchain",
                "AI",
                "RWA",
                "Digital Identity",
            ],
            "required_investors": {"TIER 2": 1, "TIER 3": 1},
        },
        "Tier 3": {
            "capitalization": 50_000_000,
            "fundraising": 20_000_000,
            "twitter_followers": 50_000,
            "twitter_score": 50,
            "categories": [
                "GameFi / Metaverse",
                "NFT Platforms / Marketplaces",
                "SocialFi",
            ],
            "required_investors": {"TIER 3": 1, "TIER 4": 1},
        },
        "Tier 4": {
            "capitalization": 10_000_000,
            "fundraising": 5_000_000,
            "twitter_followers": 10_000,
            "twitter_score": 20,
            "categories": ["TON"],
            "required_investors": {"TIER 4": 1},
        },
    }

    tier_rank = {"TIER 1": 1, "TIER 2": 2, "TIER 3": 3, "TIER 4": 4}

    # Parse investor tiers from input
    parsed_investors = []
    if isinstance(investors, str):
        investors = [inv.strip() for inv in investors.split(",")]

    for investor in investors:
        print("Investor entry:", investor)
        if "(" in investor and ")" in investor:
            name, tier = investor.rsplit("(", 1)
            tier = tier.strip(")").replace("+", "")  # Убираем "+" в конце
            parsed_investors.append(tier)

    investor_counts = {tier: 0 for tier in tier_rank}
    print("Parsed Investors:", parsed_investors)
    for tier in parsed_investors:
        if tier in tier_rank:
            investor_counts[tier] += 1

    # Determine tier
    for tier, criteria in tier_criteria.items():
        print(f"Checking {tier}: {criteria}")

        # Проверка всех основных метрик
        passes_metrics = (
                int(capitalization) >= int(criteria["capitalization"])
                and int(fundraising) >= int(criteria["fundraising"])
                and int(clean_twitter_subs(twitter_followers)) >= int(clean_twitter_subs(criteria["twitter_followers"]))
                and int(twitter_score) >= int(criteria["twitter_score"])
        )

        # Если метрики не подходят, сразу переходим к следующему Tier
        if not passes_metrics:
            print(f"Metrics do not fit for {tier}, moving to the next tier.")
            continue

        # Проверка категории как минимального требования
        if category not in criteria["categories"]:
            print(f"Category {category} does not fit for {tier}, but metrics fit. Moving to the next tier.")
            continue

        # Проверка инвесторов
        remaining_requirements = criteria["required_investors"].copy()
        for inv_tier, required_count in remaining_requirements.items():
            for higher_tier in tier_rank:
                if tier_rank[higher_tier] <= tier_rank[inv_tier]:
                    satisfied = min(investor_counts[higher_tier], required_count)
                    remaining_requirements[inv_tier] -= satisfied
                    investor_counts[higher_tier] -= satisfied

        print(f"Remaining investor requirements for {tier}: {remaining_requirements}")

        # Если инвесторы удовлетворены
        if all(count <= 0 for count in remaining_requirements.values()):
            print(f"Project fits into {tier}!")
            return tier

        # Если не удовлетворяет ни одному Tier, присваиваем Tier 5
    print("Project does not fit into any tier, assigning TIER 5.")
    return "TIER 5"


def calculate_tokenomics_score(project_name, comparisons):
    total_score = 0
    results = []

    for comparison in comparisons:
        for ticker, data in comparison.items():
            if ticker != project_name:
                growth_percent = data.get('growth_percent', 0)
                print(f"Calculating tokenomics score {comparison}")
                print(f"ticker: {ticker}, growth: {growth_percent}")

                if abs(growth_percent) <= 1:
                    score = 0
                else:
                    score = round(growth_percent / 10, 2)

                total_score += score
                results.append(f"{ticker} = {score} баллов")

    total_score = round(total_score, 2)

    result_string = (
        f"Общая оценка токеномики проекта {project_name}: {total_score} баллов.\n\n"
        f"Отдельные набранные баллы в сравнении с другими проектами:\n"
        + ",\n".join(results) + "."
    )

    return result_string, total_score


def analyze_project_metrics(fund_distribution, fundraise, total_supply, market_price, growth_percentage, fall_percentage, top_100_percentage, tvl_percentage):
    tvl_score = 0
    top_100_score = 0
    growth_and_fall_score = 0
    funds_score = 0

    if fundraise != 'N/A' and total_supply != 'N/A':
        avg_price = float(fundraise) / (float(total_supply) * float(fund_distribution.replace('%', '').strip()))
        x_funds = round(float(market_price) / avg_price, 2)
        percente_of_funds_profit = (x_funds * 100) - 100

        if percente_of_funds_profit <= 200:
            funds_score = percente_of_funds_profit / 20
        elif 201 <= percente_of_funds_profit <= 1000:
            funds_score = (200 / 20) + ((percente_of_funds_profit - 200) / 100) * (-0.5)
        elif 1001 <= percente_of_funds_profit <= 3000:
            funds_score = (200 / 20) + (800 / 100) * (-0.5) + ((percente_of_funds_profit - 1000) / 100) * (-1)
        elif 3001 <= percente_of_funds_profit <= 5000:
            funds_score = (200 / 20) + (800 / 100) * (-0.5) + (2000 / 100) * (-1) + (
                        (percente_of_funds_profit - 3000) / 100) * (-1.5)
        elif percente_of_funds_profit > 5000:
            funds_score = (200 / 20) + (800 / 100) * (-0.5) + (2000 / 100) * (-1) + (2000 / 100) * (-1.5) + (
                        (percente_of_funds_profit - 5000) / 100) * (-2)

        funds_result = f"По данному показателю проект получает {round(funds_score, 2)} баллов.\n"
    else:
        funds_result = "Данные для расчета средней цены и доходности фондов отсутствуют.\n"

    if growth_percentage != 'N/A' and fall_percentage != 'N/A':
        growth_and_fall_score = fall_percentage - growth_percentage
        if growth_and_fall_score < -50:
            growth_and_fall_score = -50
        growth_and_fall_result = f"Проект {'потерял' if growth_and_fall_score < 0 else 'получил'} {round(abs(growth_and_fall_score), 2)} баллов по показателю роста от минимальных значений и падения от максимальных значений.\n"
    else:
        growth_and_fall_result = "Данные для расчета роста и падения отсутствуют.\n"

    if top_100_percentage != 'N/A':
        top_100_score = max(0, int(top_100_percentage) - 70)
        top_100_result = f"Проект {'потерял' if top_100_score == 0 else 'получил'} {top_100_score} баллов по показателю процента монет на топ 100 кошельков.\n"
    else:
        top_100_result = "Данные для расчета процента монет на топ 100 кошельков отсутствуют.\n"

    if tvl_percentage != 'N/A':
        tvl_score = int(tvl_percentage)
        tvl_result = f"Проект {'потерял' if tvl_score == 0 else 'получил'} {tvl_score} баллов по показателю процента заблокированных монет.\n"
    else:
        tvl_result = "Данные для расчета процента заблокированных монет отсутствуют.\n"

    report = funds_result + growth_and_fall_result + top_100_result + tvl_result
    print(tvl_score + top_100_score + growth_and_fall_score + funds_score)
    return report, tvl_score + top_100_score + growth_and_fall_score + funds_score


def calculate_project_score(fundraising, tier, twitter_followers, twitter_score, tokenomics_score, profitability_score):
    FUNDRAISING_DIVISOR = 5_000_000
    FOLLOWERS_DIVISOR = 15_000
    TWITTER_SCORE_MULTIPLIER = 0.1
    TIER_SCORES = {
        "TIER 1": 100,
        "TIER 2": 80,
        "TIER 3": 60,
        "TIER 4": 30,
        "TIER 5": 0
    }
    TIER_COEFFICIENTS = {
        "TIER 1": 1.00,
        "TIER 2": 0.90,
        "TIER 3": 0.80,
        "TIER 4": 0.70,
        "TIER 5": 0.60
    }

    # Обработка значений N/A и их замена на 0
    if fundraising == 'N/A' or not isinstance(fundraising, (int, float)):
        fundraising = 0
    else:
        fundraising = float(fundraising)  # Преобразуем в число

    if tier == 'N/A':
        tier = 'TIER 5'  # Можно задать значение по умолчанию для TIER

    if twitter_followers == 'N/A' or not isinstance(twitter_followers, (int, float)):
        twitter_followers = 0
    else:
        twitter_followers = float(twitter_followers)  # Преобразуем в число

    if twitter_score == 'N/A' or not isinstance(twitter_score, (int, float)):
        twitter_score = 0
    else:
        twitter_score = float(twitter_score)  # Преобразуем в число

    if tokenomics_score == 'N/A' or not isinstance(tokenomics_score, (int, float)):
        tokenomics_score = 0
    else:
        tokenomics_score = float(tokenomics_score)  # Преобразуем в число

    if profitability_score == 'N/A' or not isinstance(profitability_score, (int, float)):
        profitability_score = 0
    else:
        profitability_score = float(profitability_score)  # Преобразуем в число

    fundraising_score = round(fundraising / FUNDRAISING_DIVISOR, 2)
    tier_score = TIER_SCORES.get(tier, 0)
    followers_score = round(twitter_followers / FOLLOWERS_DIVISOR, 2)
    twitter_engagement_score = round(twitter_score * TWITTER_SCORE_MULTIPLIER, 2)

    preliminary_score = (
        fundraising_score +
        tier_score +
        followers_score +
        twitter_engagement_score +
        tokenomics_score +
        profitability_score
    )

    tier_coefficient = TIER_COEFFICIENTS.get(tier, 0.60)
    final_score = round(preliminary_score * tier_coefficient, 2)

    calculations_summary = """
    Расчеты:
        Баллы за привлеченные инвестиции: {fundraising_score} баллов.
        Баллы за Тир проекта: {tier_score} баллов.
        Баллы за количество подписчиков в Twitter: {followers_score} баллов.
        Баллы за Twitter Score: {twitter_engagement_score} баллов.
        Баллы от оценки токеномики: {tokenomics_score} баллов.
        Оценка прибыльности фондов: {profitability_score} баллов.

    Предварительное общее количество баллов проекта до снижения: {preliminary_score} баллов.
    Применен снижающий коэффициент: {tier_coefficient}.
    Итоговое общее количество баллов проекта: {final_score} баллов.
    """.format(
        fundraising_score=fundraising_score,
        tier_score=tier_score,
        followers_score=followers_score,
        twitter_engagement_score=twitter_engagement_score,
        tokenomics_score=tokenomics_score,
        profitability_score=profitability_score,
        preliminary_score=preliminary_score,
        tier_coefficient=tier_coefficient,
        final_score=final_score
    )

    result = {
        "fundraising_score": fundraising_score,
        "tier_score": tier_score,
        "followers_score": followers_score,
        "twitter_engagement_score": twitter_engagement_score,
        "tokenomics_score": tokenomics_score,
        "profitability_score": profitability_score,
        "preliminary_score": preliminary_score,
        "tier_coefficient": tier_coefficient,
        "final_score": final_score,
        "calculations_summary": calculations_summary
    }

    return result






