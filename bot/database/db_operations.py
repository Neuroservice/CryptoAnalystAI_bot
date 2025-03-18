import logging

from sqlalchemy.future import select
from sqlalchemy import Table, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Type, Any, Tuple, Dict, Union, Callable

from bot.database.models import User, Project
from bot.utils.common.sessions import redis_client
from bot.utils.common.decorators import save_execute
from bot.utils.resources.exceptions.exceptions import (
    DatabaseError,
    DatabaseCreationError,
    DatabaseFetchError,
)


@save_execute
async def get_one(session: AsyncSession, model: Type[Any], **filters: Any) -> Optional[Any]:
    """
    Получить одну запись из базы данных.
    """
    try:
        query = select(model).filter_by(**filters)
        result = await session.execute(query)
        return result.scalars().first()
    except SQLAlchemyError as e:
        raise DatabaseFetchError(str(e))


@save_execute
async def get_all(
    session: AsyncSession,
    model: Type[Any],
    join_model: Optional[Union[Type[Any], Callable[[Any], Any]]] = None,
    order_by: Optional[Any] = None,
    limit: Optional[int] = None,
    options: Optional[list[Any]] = None,
    **filters: Any,
) -> list[Any]:
    """
    Получить все записи из базы данных с возможностью сортировки, ограничения количества, объединения таблиц и eager loading.

    Аргументы:
    - `session`: Сессия SQLAlchemy.
    - `model`: Основная модель SQLAlchemy, из которой будет осуществляться выборка.
    - `join_model`: Модель или таблица для JOIN, если требуется объединение с другой сущностью (например, для сортировки).
    - `order_by`: Объект сортировки (например, Model.field.desc()).
    - `limit`: Ограничение количества возвращаемых записей.
    - `options`: Список опций для eager loading (например, [selectinload(Model.relationship)]).
    - `filters`: Фильтры для выборки. Поддерживаются простые значения, а также функции (например, lambda col: col.in_([...])) для динамической фильтрации.

    Возвращает:
    - Список найденных объектов модели.
    """
    try:
        query = select(model)

        # Если join_model передан, проверяем, является ли он вызываемым
        if join_model:
            if callable(join_model):
                query = join_model(query)
            else:
                query = query.join(join_model)

        if options:
            for opt in options:
                query = query.options(opt)

        # Добавляем фильтры
        for key, value in filters.items():
            if callable(value):
                query = query.filter(value(getattr(model, key)))
            else:
                query = query.filter(getattr(model, key) == value)

        if order_by is not None:
            query = query.order_by(order_by)
        if limit is not None:
            query = query.limit(limit)

        result = await session.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        raise DatabaseFetchError(str(e))


@save_execute
async def create(session: AsyncSession, model: Type[Any], **fields: Any) -> Any:
    """
    Создать новую запись в базе данных.

    Простой атомарный метод, который не пытается искать запись — только создаёт и возвращает.
    """
    try:
        instance = model(**fields)
        session.add(instance)
        await session.commit()
        return instance
    except SQLAlchemyError as e:
        await session.rollback()
        raise DatabaseCreationError(str(e))


@save_execute
async def get_or_create(
    session: AsyncSession,
    model: Type[Any],
    defaults: Optional[dict] = None,
    **filters: Any,
) -> Tuple[Any, bool]:
    """
    Получить запись по фильтрам или создать (если не найдена).

    - Возвращает (instance, created), где created = True, если запись создана.
    - Внутри использует get_one + create.
    """
    instance = await get_one(model=model, **filters)
    if instance:
        return instance, False

    # Если записи нет, создаём
    params = {**filters}
    if defaults:
        params.update(defaults)
    new_instance = await create(model=model, **params)
    return new_instance, True


@save_execute
async def update_or_create_token(session: AsyncSession, token_data: dict) -> Tuple[Any, bool]:
    """
    Обновляет токен, если он уже существует, иначе создаёт новый.

    Аргументы:
    - session: Сессия SQLAlchemy.
    - token_data: Словарь с данными токена, содержащий ключи "symbol" и "cmc_rank".

    Возвращает:
    - Кортеж (instance, created), где created = True, если запись была создана,
      и False, если запись обновлена.
    """
    symbol = token_data["symbol"]
    cmc_rank = token_data.get("cmc_rank")

    instance = await get_one(Project, coin_name=symbol)
    if instance:
        # Обновляем значение рейтинга и сохраняем изменения
        instance.cmc_rank = cmc_rank
        print("Instance", instance.coin_name, instance.cmc_rank)
        session.add(instance)
        await session.commit()
        return instance, False
    else:
        # Создаём новый проект
        new_instance = await create(Project, coin_name=symbol, cmc_rank=cmc_rank)
        print("New instance created:", new_instance.coin_name)

        return new_instance, True


@save_execute
async def get_user_from_redis_or_db(session: AsyncSession, user_id: int) -> Optional[Dict[str, str]]:
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
        user, _ = await get_or_create(session, User, defaults={"language": "ENG"}, telegram_id=user_id)

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
    session: AsyncSession,
    model: Any,
    project_id: Optional[int] = None,
    id: Optional[int] = None,
    defaults: Optional[dict] = None,
    **kwargs: Any,
) -> Any:
    """
    Функция для обновления или создания записи.
    """
    logging.info(f"project_id: {project_id}, id: {id}, defaults: {defaults}, kwargs: {kwargs}")
    defaults = defaults or {}
    kwargs = kwargs or {}

    query = select(model)
    if id:
        query = query.filter_by(id=id)
    elif project_id:
        query = query.filter_by(project_id=project_id)
    else:
        raise ValueError("Необходимо указать id или project_id для поиска записи.")

    result = await session.execute(query)
    instance = result.scalars().first()

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


@save_execute
async def create_association(session: AsyncSession, table: Table, **fields: Any):
    """
    Создать запись в таблице связей (например, project_category_association).
    """
    try:
        query = select(table).filter_by(**fields)
        result = await session.execute(query)
        existing_association = result.scalars().first()

        if not existing_association:
            insert_query = insert(table).values(**fields)
            await session.execute(insert_query)
            await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        raise DatabaseCreationError(str(e))
