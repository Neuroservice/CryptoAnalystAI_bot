from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.handlers.calculate import CalculateProject
from bot.utils.keyboards.calculate_keyboards import analysis_type_keyboard

analysis_router = Router()


@analysis_router.message(Command("analysis"))
async def handle_analysis_command(message: types.Message, state: FSMContext):
    await message.answer(
        "Выберите блок аналитики:",
        reply_markup=analysis_type_keyboard(message.from_user.id)
    )
    await state.set_state(CalculateProject.choosing_analysis_type)
