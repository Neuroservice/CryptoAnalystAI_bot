from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db_operations import get_one, update_or_create
from bot.database.models import (
    BasicMetrics,
    TopAndBottom,
    MarketMetrics,
    FundsProfit,
    ManipulativeMetrics,
    NetworkMetrics,
    InvestingMetrics,
    SocialMetrics,
    Project
)
from bot.utils.common.consts import TICKERS
from bot.utils.resources.exceptions.exceptions import ExceptionError
from bot.utils.common.decorators import save_execute


@save_execute
async def update_project(session: AsyncSession, user_coin_name: str, chosen_project: str, project: Project):
    """
    Обновляет информацию о проекте в базе данных.
    """

    if user_coin_name not in TICKERS:
        instance = await update_or_create(
            session, Project,
            id=project.id,
            defaults={
                "coin_name": user_coin_name,
                "category": chosen_project
            },
        )
        return instance
    else:
        return await get_one(session, Project, coin_name=user_coin_name)


@save_execute
async def update_social_metrics(session: AsyncSession, project_id: int, social_metrics: dict[int]):
    """
    Обновляет информацию о социальных метриках проекта.
    """

    if social_metrics:
        twitter_subs, twitter_twitterscore = social_metrics[0]
        await update_or_create(
            session, SocialMetrics,
            project_id=project_id,
            defaults={
                'twitter': twitter_subs,
                'twitterscore': twitter_twitterscore
            },
        )


@save_execute
async def update_investing_metrics(session: AsyncSession, project_id: int, investing_metrics: dict[int], user_coin_name: str, investors: str):
    """
    Обновляет информацию об инвестиционных метриках проекта.
    """

    if investing_metrics:
        fundraise, fund_tier = investing_metrics[0]
        if user_coin_name not in TICKERS and fundraise and investors:
            await update_or_create(
                session, InvestingMetrics,
                project_id=project_id,
                defaults={'fundraise': fundraise, 'fund_level': investors},
            )
        elif fundraise:
            await update_or_create(
                session, InvestingMetrics,
                project_id=project_id,
                defaults={'fundraise': fundraise},
            )


@save_execute
async def update_network_metrics(session: AsyncSession, project_id: int, network_metrics: dict[int], price: int, total_supply: int):
    """
    Обновляет информацию о сетевых метриках проекта.
    """

    if network_metrics:
        last_tvl = network_metrics[0]
        if last_tvl and price and total_supply:
            await update_or_create(
                session, NetworkMetrics,
                project_id=project_id,
                defaults={
                    'tvl': last_tvl,
                    'tvl_fdv': last_tvl / (price * total_supply) if price * total_supply else 0
                },
            )


@save_execute
async def update_manipulative_metrics(session: AsyncSession, project_id: int, manipulative_metrics: dict[int], price: int, total_supply: int, fundraise: int):
    """
    Обновление данных по манипулятивным метрикам
    """

    if manipulative_metrics:
        top_100_wallets = manipulative_metrics[0]
        await update_or_create(
            session, ManipulativeMetrics,
            project_id=project_id,
            defaults={
                'fdv_fundraise': (price * total_supply) / fundraise if fundraise else None,
                'top_100_wallet': top_100_wallets
            },
        )


@save_execute
async def update_funds_profit(session, project_id, funds_profit_data):
    """
    Обновляет информацию о распределении токенов проекта.
    """

    output_string = '\n'.join(funds_profit_data[0]) if funds_profit_data and funds_profit_data[0] else ''
    if output_string:
        await update_or_create(
            session, FundsProfit,
            project_id=project_id,
            defaults={'distribution': output_string},
        )


@save_execute
async def update_market_metrics(session, project_id, market_metrics):
    """
    Обновляет информацию о рыночных метриках проекта
    """

    try:
        if market_metrics:
            fail_high, growth_low, max_price, min_price = market_metrics[0]
            if all([fail_high, growth_low, max_price, min_price]):
                await update_or_create(
                    session, MarketMetrics,
                    project_id=project_id,
                    defaults={'fail_high': fail_high, 'growth_low': growth_low},
                )
                await update_or_create(
                    session, TopAndBottom,
                    project_id=project_id,
                    defaults={'lower_threshold': min_price, 'upper_threshold': max_price},
                )

    except Exception as e:
        await session.rollback()
        raise ExceptionError(str(e))


@save_execute
async def process_metrics(
    session: "AsyncSession",
    user_coin_name: str,
    project: "Project",
    chosen_project: str,
    results: dict,
    price: int,
    total_supply: int,
    fundraise: int,
    investors: str
) -> "Project":
    """
    Обрабатывает метрики для указанного проекта и обновляет соответствующие записи в базе данных.
    """

    # Обновление или создание проекта
    new_project = await update_project(session, user_coin_name, chosen_project, project)

    # Обновление или создание базовых метрик
    await update_or_create(
        session, BasicMetrics,
        project_id=new_project.id,
        defaults={
            'entry_price': price,
            'sphere': chosen_project,
            'market_price': price
        },
    )

    await update_social_metrics(session, new_project.id, results.get("social_metrics"))
    await update_investing_metrics(session, new_project.id, results.get("investing_metrics"), user_coin_name, investors)
    await update_network_metrics(session, new_project.id, results.get("network_metrics"), price, total_supply)
    await update_manipulative_metrics(session, new_project.id, results.get("manipulative_metrics"), price, total_supply, fundraise)
    await update_funds_profit(session, new_project.id, results.get("funds_profit"))
    await update_market_metrics(session, new_project.id, results.get("market_metrics"))

    return new_project

