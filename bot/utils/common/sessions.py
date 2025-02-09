import redis.asyncio as redis

from aiohttp import ClientSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from bot.utils.common.config import REDIS_HOST, DB_PASSWORD, REDIS_PORT
from bot.utils.common.consts import DATABASE_URL

async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_timeout=60,
    connect_args={"timeout": 60},
)

SessionLocal = sessionmaker(
    class_=AsyncSession,
    expire_on_commit=False,
)
SessionLocal.configure(bind=async_engine)

session_local = SessionLocal()
client_session = ClientSession

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
