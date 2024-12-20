import json
import os

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.base import StorageKey
from sqlalchemy import select

from bot.config import API_TOKEN
from bot.database.models import User
from bot.utils.consts import STATE_FILE, SessionLocal
from bot.utils.validations import save_execute


def save_states_to_file(states):
    """Сохраняет состояния пользователей в файл JSON."""
    with open(STATE_FILE, "w") as f:
        json.dump(states, f)


def load_states_from_file():
    """Загружает состояния пользователей из файла JSON."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


@save_execute
async def restore_states(storage, bot, dispatcher: Dispatcher):
    """Восстанавливает состояния пользователей из файла JSON и проверяет установленные состояния в FSMContext."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            all_states = json.load(file)
    except FileNotFoundError:
        all_states = {}

    print("Состояния из файла JSON:", all_states)

    # Восстановление состояний
    for user_id, user_data in all_states.items():
        state = user_data.get("state")
        print(f"Исходное состояние: {state}")
        data = user_data.get("data", {})
        chat_id = user_id.split(":")[1]

        if state:
            # Получаем объект FSMContext через dispatcher
            user_state = await dispatcher.storage.get_state(chat_id)

            if user_state is None:
                print(f"Нет состояния для пользователя с chat_id {chat_id}. Устанавливаем начальное состояние.")

                # Если состояния нет, восстанавливаем его вручную
                await dispatcher.storage.set_state(chat_id, state)

                # Если есть данные, восстанавливаем их
                if data:
                    await dispatcher.storage.set_data(chat_id, data)
            else:
                print(f"Восстановлено состояние для пользователя с chat_id {chat_id}")

    # Проверка текущих состояний в хранилище
    print("Текущее состояние в памяти:")
    for user_id in all_states.keys():
        chat_id = user_id.split(":")[1]

        # Используем тот же формат ключа
        key = chat_id  # Используем только chat_id для хранилища

        # Заменяем вызов на объект FSMContext для получения состояния и данных
        state = await storage.get_state(key)  # Вместо user_state.get_state
        data = await storage.get_data(key)  # Вместо user_state.get_data
        print(f"Ключ: {key}, Состояние: {state}, Данные: {data}")


@save_execute
async def save_all_states(storage):
    """Сохраняет состояния всех пользователей в файл JSON."""
    all_states = {}
    async with AiohttpSession() as aiohttp_session:
        bot = Bot(token=API_TOKEN, session=aiohttp_session)
        active_users = await get_all_users()

        for id, telegram_id, language in active_users:
            key = StorageKey(bot_id=bot.id, chat_id=telegram_id, user_id=telegram_id)  # Указываем bot_id
            state = await storage.get_state(key=key)  # Получаем состояние
            data = await storage.get_data(key=key)  # Получаем данные
            all_states[f"user:{telegram_id}"] = {
                "state": state,
                "data": data,
                "language": language
            }

        print(all_states)

        # Сохранение всех состояний в файл JSON
        with open(STATE_FILE, "w", encoding="utf-8") as file:
            json.dump(all_states, file, ensure_ascii=False, indent=4)


async def get_all_users():
    async with SessionLocal() as session:
        # Правильный запрос с выбором только нужных столбцов
        users_stmt = select(User.id, User.telegram_id, User.language)
        result = await session.execute(users_stmt)
        users = result.all()
        # Преобразуем результат в список кортежей с нужными полями
        return [(user.id, user.telegram_id, user.language) for user in users]
