from aiogram.fsm.state import StatesGroup, State


class CalculateProject(StatesGroup):
    """
    Состояния бота:
    - choosing_analysis_type - выбор анализируемого блока
    - waiting_for_data - ожидание ввода необходимых данных
    - waiting_for_basic_data - ожидание ввода основных характеристик проекта
    """

    choosing_analysis_type = State()
    waiting_for_data = State()
    waiting_for_basic_data = State()
