from bot.database.models import (
    User,
    Project,
    Calculation,
    BasicMetrics,
    InvestingMetrics,
    SocialMetrics,
    Tokenomics,
    FundsProfit,
    TopAndBottom,
    MarketMetrics,
    ManipulativeMetrics,
    NetworkMetrics,
    AgentAnswer,
)
from bot.utils.resources.exceptions.exceptions import ExceptionError
from bot.utils.common.sessions import async_engine


async def create_db():
    """
    Фукнция создания всех таблиц в базе данных
    """

    try:
        async with async_engine.connect() as conn:
            async with conn.begin():
                try:
                    # Создание таблиц асинхронным методом
                    await conn.run_sync(User.metadata.create_all)
                    await conn.run_sync(Project.metadata.create_all)
                    await conn.run_sync(Calculation.metadata.create_all)
                    await conn.run_sync(BasicMetrics.metadata.create_all)
                    await conn.run_sync(InvestingMetrics.metadata.create_all)
                    await conn.run_sync(SocialMetrics.metadata.create_all)
                    await conn.run_sync(Tokenomics.metadata.create_all)
                    await conn.run_sync(FundsProfit.metadata.create_all)
                    await conn.run_sync(TopAndBottom.metadata.create_all)
                    await conn.run_sync(MarketMetrics.metadata.create_all)
                    await conn.run_sync(ManipulativeMetrics.metadata.create_all)
                    await conn.run_sync(NetworkMetrics.metadata.create_all)
                    await conn.run_sync(AgentAnswer.metadata.create_all)
                    print("Все таблицы созданы успешно.")

                except Exception as e:
                    raise ExceptionError(str(e))

    except Exception as e:
        raise ExceptionError(str(e))
