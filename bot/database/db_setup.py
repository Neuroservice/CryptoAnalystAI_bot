from sqlalchemy import create_engine
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
    NetworkMetrics
)

DATABASE_URL = "sqlite:///./crypto_analysis.db"  # Для локалки
# DATABASE_URL = "sqlite:///bot/crypto_analysis.db"  # Для прода

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Функция для отображения созданных таблиц
# def show_tables():
#     inspector = inspect(engine)
#     tables = inspector.get_table_names()
#     print("Созданные таблицы:", tables)


def create_db():
    User.__table__.create(bind=engine, checkfirst=True)
    Project.__table__.create(bind=engine, checkfirst=True)
    Calculation.__table__.create(bind=engine, checkfirst=True)
    BasicMetrics.__table__.create(bind=engine, checkfirst=True)
    InvestingMetrics.__table__.create(bind=engine, checkfirst=True)
    SocialMetrics.__table__.create(bind=engine, checkfirst=True)
    Tokenomics.__table__.create(bind=engine, checkfirst=True)
    FundsProfit.__table__.create(bind=engine, checkfirst=True)
    TopAndBottom.__table__.create(bind=engine, checkfirst=True)
    MarketMetrics.__table__.create(bind=engine, checkfirst=True)
    ManipulativeMetrics.__table__.create(bind=engine, checkfirst=True)
    NetworkMetrics.__table__.create(bind=engine, checkfirst=True)

    # show_tables()
