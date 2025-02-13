import logging
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Type, Any, Tuple, Union, Dict

from bot.database.models import User
from bot.utils.common.decorators import save_execute
from bot.utils.common.sessions import redis_client, session_local
from bot.utils.resources.exceptions.exceptions import (
    DatabaseError,
    DatabaseCreationError,
    DatabaseFetchError,
)


@save_execute
async def get_one(model: Type[Any], **filters) -> Optional[Any]:
    """
    Получить одну запись из базы данных.
    """
    try:
        query = select(model).filter_by(**filters)
        result = await session_local.execute(query)
        return result.scalars().first()
    except SQLAlchemyError as e:
        raise DatabaseFetchError(str(e))


@save_execute
async def get_all(model: Type[Any], **filters) -> list[Any]:
    """
    Получить все записи из базы данных.
    """
    try:
        query = select(model).filter_by(**filters)
        result = await session_local.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        raise DatabaseFetchError(str(e))


@save_execute
async def create(model: Type[Any], **fields) -> Any:
    """
    Создать новую запись в базе данных.

    Простой атомарный метод, который не пытается искать запись —
    только создаёт и возвращает.
    """
    try:
        instance = model(**fields)
        session_local.add(instance)
        await session_local.commit()
        return instance
    except SQLAlchemyError as e:
        await session_local.rollback()
        raise DatabaseCreationError(str(e))


@save_execute
async def get_or_create(
    model: Type[Any], defaults: Optional[dict] = None, **filters
) -> Tuple[Any, bool]:
    """
    Получить запись по фильтрам или создать (если не найдена).

    - Возвращает (instance, created), где created = True, если запись создана.
    - Внутри использует get_one + create.
    """
    instance = await get_one(model, **filters)
    if instance:
        return instance, False

    # Если записи нет, создаём
    params = {**filters}
    if defaults:
        params.update(defaults)
    new_instance = await create(model, **params)
    return new_instance, True


@save_execute
async def get_user_from_redis_or_db(user_id: int) -> Optional[Dict[str, str]]:
    """
    Сначала пытается получить данные из Redis.
    Если их нет, получает или создаёт пользователя в БД,
    затем сохраняет данные в Redis и возвращает словарь.

    Возвращает:
    - dict ({"telegram_id": ..., "language": ...}) — если данные найдены
    - None — если произошла ошибка
    """
    # 1. Проверяем Redis
    user_data = await redis_client.hgetall(f"user:{user_id}")
    if user_data:
        return user_data

    # 2. Если нет в Redis, пытаемся получить или создать пользователя в БД
    try:
        user, _ = await get_or_create(
            User, defaults={"language": "ENG"}, telegram_id=user_id
        )

        # 3. Сохраняем в Redis и возвращаем словарь
        user_dict = {
            "telegram_id": str(user.telegram_id),
            "language": user.language or "ENG",
        }
        await redis_client.hset(f"user:{user_id}", mapping=user_dict)

        return user_dict
    except DatabaseError as e:
        logging.error(f"Ошибка при работе с БД: {e.detail}")
        return None


@save_execute
async def update_or_create(
    model: Any,
    project_id: Optional[int] = None,
    id: Optional[int] = None,
    defaults: Optional[dict] = None,
    **kwargs: Any,
) -> Any:
    """
    Функция для обновления или создания записи.
    """
    logging.info(
        f"project_id: {project_id}, id: {id}, defaults: {defaults}, kwargs: {kwargs}"
    )
    defaults = defaults or {}
    kwargs = kwargs or {}

    query = select(model)
    if id:
        query = query.filter_by(id=id)
    elif project_id:
        query = query.filter_by(project_id=project_id)
    else:
        raise ValueError(
            "Необходимо указать id или project_id для поиска записи."
        )

    result = await session_local.execute(query)
    instance = result.scalars().first()

    if instance:
        for key, value in defaults.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
            else:
                logging.warning(
                    f"Поле '{key}' отсутствует в модели '{model.__name__}'. Пропускаем."
                )
    else:
        params = {**kwargs, **defaults}
        if id:
            instance = model(id=id, **params)
        elif project_id:
            instance = model(project_id=project_id, **params)
        else:
            raise ValueError(
                "Необходимо указать id или project_id для создания записи."
            )
        session_local.add(instance)

    await session_local.commit()
    return instance
