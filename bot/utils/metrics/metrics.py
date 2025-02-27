import logging

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db_operations import (
    get_one,
    update_or_create,
    get_or_create,
    create_association,
)
from bot.utils.common.consts import TICKERS
from bot.utils.resources.exceptions.exceptions import ExceptionError
from bot.utils.common.decorators import save_execute
from bot.database.models import (
    BasicMetrics,
    TopAndBottom,
    MarketMetrics,
    FundsProfit,
    ManipulativeMetrics,
    NetworkMetrics,
    InvestingMetrics,
    SocialMetrics,
    Project,
    Category,
    project_category_association,
)


async def update_project(
    user_coin_name: str,
    categories: list,
    project: Project,
):
    """
    Обновляет информацию о проекте в базе данных.
    """

    if user_coin_name not in TICKERS:
        instance = await update_or_create(
            Project,
            id=project.id,
            defaults={"coin_name": user_coin_name},
        )

        for category in categories:
            category_instance, _ = await get_or_create(
                Category,
                defaults={"category_name": category},
            )
            await create_association(
                project_category_association,
                project_id=instance.id,
                category_id=category_instance.id,
            )
        return instance
    else:
        return await get_one(Project, coin_name=user_coin_name)


async def update_social_metrics(project_id: int, social_metrics: dict[int]):
    """
    Обновляет информацию о социальных метриках проекта.
    """

    if social_metrics:
        twitter_subs, twitter_twitterscore = social_metrics[0]
        await update_or_create(
            SocialMetrics,
            project_id=project_id,
            defaults={
                "twitter": twitter_subs,
                "twitterscore": twitter_twitterscore,
            },
        )


async def update_investing_metrics(
    project_id: int,
    investing_metrics: dict[int],
    user_coin_name: str,
    investors: str,
):
    """
    Обновляет информацию об инвестиционных метриках проекта.
    """

    if investing_metrics:
        fundraise, fund_tier = investing_metrics[0]
        if user_coin_name not in TICKERS and fundraise and investors:
            await update_or_create(
                InvestingMetrics,
                project_id=project_id,
                defaults={"fundraise": fundraise, "fund_level": investors},
            )
        elif fundraise:
            await update_or_create(
                InvestingMetrics,
                project_id=project_id,
                defaults={"fundraise": fundraise},
            )


async def update_network_metrics(
    project_id: int,
    network_metrics: dict[int],
    price: int,
    total_supply: int,
):
    """
    Обновляет информацию о сетевых метриках проекта.
    """

    if network_metrics:
        last_tvl = network_metrics[0]
        if last_tvl and price and total_supply:
            await update_or_create(
                NetworkMetrics,
                project_id=project_id,
                defaults={
                    "tvl": last_tvl,
                    "tvl_fdv": last_tvl / (price * total_supply)
                    if price * total_supply
                    else 0,
                },
            )


async def update_manipulative_metrics(
    project_id: int,
    manipulative_metrics: dict[int],
    price: int,
    total_supply: int,
    fundraise: int,
):
    """
    Обновление данных по манипулятивным метрикам
    """

    if manipulative_metrics:
        top_100_wallets = manipulative_metrics[0]
        await update_or_create(
            ManipulativeMetrics,
            project_id=project_id,
            defaults={
                "fdv_fundraise": (price * total_supply) / fundraise
                if fundraise
                else None,
                "top_100_wallet": top_100_wallets,
            },
        )


async def update_funds_profit(project_id: int, funds_profit_data: dict):
    """
    Обновляет информацию о распределении токенов проекта.
    """

    output_string = (
        "\n".join(funds_profit_data[0])
        if funds_profit_data and funds_profit_data[0]
        else ""
    )
    if output_string:
        await update_or_create(
            FundsProfit,
            project_id=project_id,
            defaults={"distribution": output_string},
        )


async def update_market_metrics(
    project_id: int, market_metrics: dict, top_and_bottom: dict
):
    """
    Обновляет информацию о рыночных метриках проекта
    """

    try:
        if market_metrics:
            fail_high, growth_low = market_metrics[0]
            max_price, min_price = top_and_bottom[0]
            if fail_high and growth_low:
                await update_or_create(
                    MarketMetrics,
                    project_id=project_id,
                    defaults={
                        "fail_high": fail_high,
                        "growth_low": growth_low,
                    },
                )
            if max_price and min_price:
                await update_or_create(
                    TopAndBottom,
                    project_id=project_id,
                    defaults={
                        "lower_threshold": min_price,
                        "upper_threshold": max_price,
                    },
                )

    except Exception as e:
        raise ExceptionError(str(e))


async def process_metrics(
    user_coin_name: str,
    project: "Project",
    categories: list,
    results: dict,
    price: int,
    total_supply: int,
    fundraise: int,
    investors: str,
) -> "Project":
    """
    Обрабатывает метрики для указанного проекта и обновляет соответствующие записи в базе данных.
    """

    # Обновление или создание проекта
    new_project = await update_project(user_coin_name, categories, project)

    # Обновление или создание базовых метрик
    await update_or_create(
        BasicMetrics,
        project_id=new_project.id,
        defaults={
            "entry_price": price,
            "market_price": price,
        },
    )

    # Обновление социальных метрик, проверка на None
    social_metrics = results.get("social_metrics")
    if social_metrics is not None:
        await update_social_metrics(new_project.id, social_metrics)

    # Обновление инвестиционных метрик, проверка на None
    investing_metrics = results.get("investing_metrics")
    if investing_metrics is not None:
        await update_investing_metrics(
            new_project.id, investing_metrics, user_coin_name, investors
        )

    # Обновление сетевых метрик, проверка на None
    network_metrics = results.get("network_metrics")
    if network_metrics is not None:
        await update_network_metrics(
            new_project.id, network_metrics, price, total_supply
        )

    # Обновление манипулятивных метрик, проверка на None
    manipulative_metrics = results.get("manipulative_metrics")
    if manipulative_metrics is not None:
        await update_manipulative_metrics(
            new_project.id,
            manipulative_metrics,
            price,
            total_supply,
            fundraise,
        )

    # Обновление прибыли фондов, проверка на None
    funds_profit = results.get("funds_profit")
    if funds_profit is not None:
        await update_funds_profit(new_project.id, funds_profit)

    # Обновление рыночных метрик, проверка на None
    market_metrics = results.get("market_metrics")
    top_and_bottom = results.get("top_and_bottom")
    # Проверка на None и наличие значений
    if market_metrics and all(metric is not None for metric in market_metrics):
        await update_market_metrics(
            new_project.id, market_metrics, top_and_bottom
        )
    else:
        logging.warning(
            "Неверные данные для рыночных метрик или отсутствуют значения."
        )

    return new_project
