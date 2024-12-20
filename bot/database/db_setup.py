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
from bot.utils.consts import engine
from bot.utils.validations import save_execute


async def create_db():
    try:
        async with engine.begin() as conn:
            # Создание таблиц
            try:
                await conn.run_sync(User.metadata.create_all)
            except Exception as user_error:
                print(f"Ошибка при создании таблицы User: {user_error}")

            try:
                await conn.run_sync(Project.metadata.create_all)
            except Exception as project_error:
                print(f"Ошибка при создании таблицы Project: {project_error}")

            try:
                await conn.run_sync(Calculation.metadata.create_all)
            except Exception as calculation_error:
                print(f"Ошибка при создании таблицы Calculation: {calculation_error}")

            try:
                await conn.run_sync(BasicMetrics.metadata.create_all)
            except Exception as basic_metrics_error:
                print(f"Ошибка при создании таблицы BasicMetrics: {basic_metrics_error}")

            try:
                await conn.run_sync(InvestingMetrics.metadata.create_all)
            except Exception as investing_metrics_error:
                print(f"Ошибка при создании таблицы InvestingMetrics: {investing_metrics_error}")

            try:
                await conn.run_sync(SocialMetrics.metadata.create_all)
            except Exception as social_metrics_error:
                print(f"Ошибка при создании таблицы SocialMetrics: {social_metrics_error}")

            try:
                await conn.run_sync(Tokenomics.metadata.create_all)
            except Exception as tokenomics_error:
                print(f"Ошибка при создании таблицы Tokenomics: {tokenomics_error}")

            try:
                await conn.run_sync(FundsProfit.metadata.create_all)
            except Exception as funds_profit_error:
                print(f"Ошибка при создании таблицы FundsProfit: {funds_profit_error}")

            try:
                await conn.run_sync(TopAndBottom.metadata.create_all)
                print("Таблица TopAndBottom создана успешно.")
            except Exception as top_and_bottom_error:
                print(f"Ошибка при создании таблицы TopAndBottom: {top_and_bottom_error}")

            try:
                await conn.run_sync(MarketMetrics.metadata.create_all)
            except Exception as market_metrics_error:
                print(f"Ошибка при создании таблицы MarketMetrics: {market_metrics_error}")

            try:
                await conn.run_sync(ManipulativeMetrics.metadata.create_all)
            except Exception as manipulative_metrics_error:
                print(f"Ошибка при создании таблицы ManipulativeMetrics: {manipulative_metrics_error}")

            try:
                await conn.run_sync(NetworkMetrics.metadata.create_all)
            except Exception as network_metrics_error:
                print(f"Ошибка при создании таблицы NetworkMetrics: {network_metrics_error}")

            try:
                await conn.run_sync(AgentAnswer.metadata.create_all)
            except Exception as agent_answer_error:
                print(f"Ошибка при создании таблицы AgentAnswer: {agent_answer_error}")

    except Exception as e:
        print(f"Общая ошибка при создании базы данных: {e}")
