from aiogram.fsm.state import StatesGroup, State


class CalculateProject(StatesGroup):
    """
    Состояния бота:
    - choosing_analysis_type - выбор анализируемого блока
    - waiting_for_data - ожидание ввода тикера для полного анализа
    - waiting_for_basic_data - ожидание ввода тикера для базового анализа
    """

    choosing_analysis_type = State()
    waiting_for_data = State()
    waiting_for_basic_data = State()


class UpdateOrCreateProject(StatesGroup):
    """
    Состояния бота для создания или обновления информации о проекте.

    - update_or_create_state - выбор анализируемого блока

    Последовательность шагов для создания нового проекта:
    1. wait_for_project_name - ввод названия проекта
    2. wait_for_cmc_rank - ввод CoinMarketCap Rank
    3. wait_for_categories - ввод категорий проекта
    4. wait_for_market_price - ввод рыночной цены
    5. wait_for_fundraise - ввод информации о фандрейзе (инвестициях)
    6. wait_for_investors - ввод списка инвесторов
    7. wait_for_twitter_followers - ввод количества подписчиков в Twitter
    8. wait_for_twitter_score - ввод баллов TwitterScore
    9. wait_for_circulating_supply - ввод circulating supply
    10. wait_for_total_supply - ввод total supply
    11. wait_for_capitalization - ввод капитализации
    12. wait_for_fdv - ввод fully diluted valuation (FDV)
    13. wait_for_token_distribution - ввод распределения токенов
    14. wait_for_max_price - ввод максимального значения цены токена за 2 года
    15. wait_for_min_price - ввод минимального значения цены токена за 2 года
    16. wait_for_top100_holders - ввод процента токенов на топ-100 кошельках
    17. wait_for_tvl - ввод TVL (Total Value Locked)
    """

    update_or_create_state = State()
    wait_for_project_name = State()
    wait_for_cmc_rank = State()
    wait_for_categories = State()
    wait_for_market_price = State()
    wait_for_fundraise = State()
    wait_for_investors = State()
    wait_for_twitter_followers = State()
    wait_for_twitter_score = State()
    wait_for_circulating_supply = State()
    wait_for_total_supply = State()
    wait_for_capitalization = State()
    wait_for_fdv = State()
    wait_for_token_distribution = State()
    wait_for_max_price = State()
    wait_for_min_price = State()
    wait_for_top100_holders = State()
    wait_for_tvl = State()
