from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.handlers.calculate import CalculateProject
from bot.utils.common.sessions import session_local
from bot.utils.keyboards.calculate_keyboards import analysis_type_keyboard
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user

analysis_router = Router()


@analysis_router.message(Command("analysis"))
async def handle_analysis_command(message: types.Message, state: FSMContext):
    """
    Хендлер для обработки пункта меню 'Выбрать блок аналитики'.
    Отдает пользователю меню (клавиатуру) с пунктами выбора блока аналитики.
    Устанавливает состояние ожидания выбора пользователем пункта меню.
    """

    await message.answer(
        await phrase_by_user("analysis_block_choose", message.from_user.id, session_local),
        reply_markup=await analysis_type_keyboard(message.from_user.id)
    )
    await state.set_state(CalculateProject.choosing_analysis_type)
