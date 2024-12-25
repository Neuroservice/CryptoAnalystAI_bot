from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

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
from bot.utils.consts import engine, async_engine


# Создание асинхронной сессии и подключения
async def create_db():
    try:
        # Используем асинхронное подключение
        async with async_engine.connect() as conn:  # Асинхронное подключение
            async with conn.begin():  # Асинхронная транзакция
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
                    print(f"Ошибка при создании таблиц: {e}")
    except Exception as e:
        print(f"Общая ошибка при создании базы данных: {e}")
