import json
from aiogram import BaseMiddleware
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update, Message, CallbackQuery, InlineQuery
from aiogram.fsm.context import FSMContext

from bot.utils.consts import STATE_FILE


class RestoreStateMiddleware(BaseMiddleware):
    """Middleware для восстановления состояния пользователя перед обработкой запросов."""

    async def __call__(self, handler, event: Update, data: dict):
        # Проверяем, что событие содержит сообщение
        print(f"Event: {event}")  # Для отладки структуры event

        # Проверяем, что в событии есть атрибут message
        if not hasattr(event, 'message') or not isinstance(event.message, Message):
            return await handler(event, data)  # Пропускаем все, кроме сообщений

        # Теперь можем безопасно работать с message
        message = event.message
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Прочие действия для обработки состояния, как в предыдущем коде
        if 'storage' not in data:
            data['storage'] = MemoryStorage()

        bot = data.get("bot")
        storage = data.get("storage")
        dispatcher = data.get("dispatcher")

        if bot and storage and dispatcher:
            user_key = f"user:{user_id}"

            # Загружаем состояния из файла
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as file:
                    all_states = json.load(file)
                    print("----", all_states)
            except FileNotFoundError:
                all_states = {}

            # Проверяем наличие состояния для текущего пользователя
            user_data = all_states.get(user_key, {})
            print(user_data)
            state = user_data.get("state")
            data_to_restore = user_data.get("data", {})

            # Используем FSMContext для получения состояния
            fsm_context = FSMContext(storage=storage, key=f"user:{user_id}")

            current_state = await fsm_context.get_state()
            print(f"Текущее состояние для пользователя {user_id}: {current_state}")

            # Если текущего состояния нет, восстанавливаем его
            if current_state is None and state:
                print(f"Восстанавливаем состояние для пользователя {user_id} - {state}")
                await fsm_context.set_state(state)

                # Восстанавливаем данные, если они есть
                if data_to_restore:
                    await fsm_context.update_data(**data_to_restore)

        # Передаем управление следующему обработчику
        return await handler(event, data)