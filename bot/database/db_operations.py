import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Type, Any

from bot.database.models import User
from bot.utils.common.decorators import save_execute
from bot.utils.common.sessions import redis_client
from bot.utils.resources.exceptions.exceptions import DatabaseError, DatabaseCreationError, DatabaseFetchError


async def get_one(session: AsyncSession, model: Type[Any], **filters) -> Optional[Any]:
    """
    Универсальная функция для получения одной записи из базы данных.
    """
    try:
        query = select(model).filter_by(**filters)
        result = await session.execute(query)
        return result.scalars().first()
    except SQLAlchemyError as e:
        raise DatabaseFetchError(str(e))


@save_execute
async def get_all(session: AsyncSession, model: Type[Any], **filters) -> list[Any]:
    """
    Универсальная функция для получения всех записей из базы данных.
    """
    try:
        query = select(model).filter_by(**filters)
        result = await session.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        raise DatabaseFetchError(str(e))


async def get_or_create(
    session: AsyncSession, model: Type[Any], defaults: Optional[dict] = None, **filters
) -> tuple[Any, bool]:
    """
    Универсальная функция для получения или создания записи в базе данных.
    """
    try:
        instance = await get_one(session, model, **filters)
        if instance:
            return instance, False

        params = {**filters}
        if defaults:
            params.update(defaults)
        instance = model(**params)
        session.add(instance)
        await session.commit()
        return instance, True
    except SQLAlchemyError as e:
        await session.rollback()
        raise DatabaseCreationError(str(e))


async def get_user_from_redis_or_db(user_id: int, session: AsyncSession) -> Any:
    """
    Получает пользователя сначала из Redis. Если его там нет, то пытается получить пользователя из базы данных.
    Если пользователя нет в базе данных, создаёт нового.
    """
    # Проверяем наличие пользователя в Redis
    user_data = await redis_client.hgetall(f"user:{user_id}")
    if user_data:
        return await get_one(session, User, telegram_id=user_id)

    # Если пользователя нет в Redis, ищем в базе данных
    try:
        user = await get_one(session, User, telegram_id=user_id)
        if user:  # Если нашли в базе данных, сохраняем его в Redis
            await redis_client.hset(
                f"user:{user_id}",
                mapping={"telegram_id": user.telegram_id, "language": user.language or "ENG"}
            )

            return user

        # Если пользователя нет в базе данных, создаём нового
        return await create_user(user_id, session)

    except DatabaseError as e:
        print(f"Ошибка работы с базой данных: {e.detail}")
        return None


async def create_user(user_id: int, session: AsyncSession) -> Any:
    """
    Создаёт нового пользователя в базе данных и сохраняет его в Redis.
    """
    defaults = {
        "telegram_id": user_id,
        "language": "ENG",
    }
    try:
        user, _ = await get_or_create(session, User, defaults=defaults, telegram_id=user_id)

        # Сохраняем созданного пользователя в Redis
        await redis_client.hset(
            f"user:{user_id}",
            mapping={"telegram_id": user.telegram_id, "language": user.language}
        )

        return user

    except DatabaseError as e:
        print(f"Ошибка при создании пользователя: {e.detail}")
        return None


async def get_user_language(user_id: int, session: AsyncSession) -> str:
    """
    Получить язык пользователя из Redis или базы данных.
    Если язык отсутствует, возвращает язык по умолчанию ('ENG').
    """
    # Получаем пользователя из Redis или базы данных
    user = await get_user_from_redis_or_db(user_id=user_id, session=session)

    # Проверяем наличие языка, если он есть у пользователя
    if user and user.language:
        return user.language

    # Возвращаем язык по умолчанию, если язык не задан
    return "ENG"


@save_execute
async def update_or_create(
    session: AsyncSession,
    model: Any,
    project_id: Optional[int] = None,
    id: Optional[int] = None,
    defaults: Optional[dict] = None,
    **kwargs: Any
) -> Any:
    """
    Вспомогательная функция для обновления или создания записи.
    """

    # Логирование входных данных
    logging.info(f"project_id: {project_id}, id: {id}, defaults: {defaults}, kwargs: {kwargs}")

    # Инициализация defaults и kwargs
    defaults = defaults or {}
    kwargs = kwargs or {}

    # Оптимизация выборки записи
    query = select(model)
    if id:
        query = query.filter_by(id=id)
    elif project_id:
        query = query.filter_by(project_id=project_id)
    else:
        raise ValueError("Необходимо указать id или project_id для поиска записи.")

    # Выполняем запрос
    result = await session.execute(query)
    instance = result.scalars().first()

    # Обновление или создание записи
    if instance:
        for key, value in defaults.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
            else:
                logging.warning(f"Поле '{key}' отсутствует в модели '{model.__name__}'. Пропускаем.")
    else:
        params = {**kwargs, **defaults}
        if id:
            instance = model(id=id, **params)
        elif project_id:
            instance = model(project_id=project_id, **params)
        else:
            raise ValueError("Необходимо указать id или project_id для создания записи.")
        session.add(instance)

    await session.commit()

    return instance