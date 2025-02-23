import logging
from datetime import datetime

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, ReplyKeyboardRemove

from bot.database.db_operations import (
    get_one,
    update_or_create,
    get_or_create,
    get_user_from_redis_or_db,
    create_association,
)
from bot.database.models import (
    Project,
    Tokenomics,
    Calculation,
    BasicMetrics,
    SocialMetrics,
    InvestingMetrics,
    NetworkMetrics,
    ManipulativeMetrics,
    FundsProfit,
    MarketMetrics,
    TopAndBottom,
    project_category_association,
    Category,
)
from bot.utils.common.bot_states import CalculateProject
from bot.utils.common.consts import (
    TICKERS,
    MODEL_MAPPING,
    REPLACED_PROJECT_TWITTER,
    PROJECT_ANALYSIS_RU,
    PROJECT_ANALYSIS_ENG,
    NEW_PROJECT,
    LISTING_PRICE_BETA_RU,
    LISTING_PRICE_BETA_ENG,
    LIST_OF_TEXT_FOR_REBALANCING_BLOCK,
    LIST_OF_TEXT_FOR_ANALYSIS_BLOCK, START_TITLE_FOR_GARBAGE_CATEGORIES, END_TITLE_FOR_GARBAGE_CATEGORIES,
)
from bot.utils.common.params import get_header_params
from bot.utils.common.sessions import session_local
from bot.utils.create_report import create_pdf_report, create_basic_report
from bot.utils.keyboards.calculate_keyboards import analysis_type_keyboard
from bot.utils.metrics.metrics import process_metrics
from bot.utils.project_data import (
    get_twitter_link_by_symbol,
    fetch_coinmarketcap_data,
    get_user_project_info,
    get_coin_description,
    get_lower_name,
    check_and_run_tasks,
    fetch_coingecko_data,
)
from bot.utils.resources.bot_phrases.bot_phrase_handler import (
    phrase_by_user,
    phrase_by_language,
)
from bot.utils.resources.exceptions.exceptions import (
    ValueProcessingError,
    ExceptionError,
)
from bot.utils.resources.files_worker.google_doc import load_document_for_garbage_list
from bot.utils.resources.gpt.gpt import agent_handler
from bot.utils.validations import validate_user_input

calculate_router = Router()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@calculate_router.message(
    lambda message: message.text == PROJECT_ANALYSIS_RU
    or message.text == PROJECT_ANALYSIS_ENG
    or message.text == NEW_PROJECT
)
async def project_chosen(message: types.Message, state: FSMContext):
    """
    Хендлер для обработки пункта меню 'Анализ проектов'.
    Предлагает пользователю выбрать определенный блок аналитики.
    """

    await message.answer(
        await phrase_by_user(
            "calculation_type_choice", message.from_user.id, session_local
        ),
        reply_markup=await analysis_type_keyboard(message.from_user.id),
    )
    await state.set_state(CalculateProject.choosing_analysis_type)


@calculate_router.message(
    lambda message: message.text == LISTING_PRICE_BETA_RU
    or message.text == LISTING_PRICE_BETA_ENG
)
async def project_chosen(message: types.Message, state: FSMContext):
    """
    Хендлер для обработки пункта меню 'Блок анализа цены на листинге'.
    P.S.: Блок в разработке
    """

    await message.answer(
        await phrase_by_user(
            "beta_block", message.from_user.id, session_local
        ),
        reply_markup=await analysis_type_keyboard(message.from_user.id),
    )


@calculate_router.message(CalculateProject.choosing_analysis_type)
async def analysis_type_chosen(message: types.Message, state: FSMContext):
    """
    Функция, для обработки выбранного пользователем блока аналитики.
    Делает проверку выбранного пользователем пункта меню,
    и предлагает ввести тикер токена, выставляя соответствующее состояние ожидания ввода данных.
    """

    analysis_type = message.text.lower()

    if analysis_type in LIST_OF_TEXT_FOR_REBALANCING_BLOCK:
        await message.answer(
            await phrase_by_user(
                "rebalancing_input_token", message.from_user.id, session_local
            )
        )
        await state.set_state(CalculateProject.waiting_for_basic_data)

    elif analysis_type in LIST_OF_TEXT_FOR_ANALYSIS_BLOCK:
        await message.answer(
            await phrase_by_user(
                "analysis_input_token", message.from_user.id, session_local
            )
        )
        await state.set_state(CalculateProject.waiting_for_data)


@calculate_router.message(CalculateProject.waiting_for_basic_data)
async def receive_basic_data(message: types.Message, state: FSMContext):
    """
    Функция, для обработки выбранного пользователем пункта 'Блок ребалансировки портфеля'.
    Функция проверяет существование в базе данных базовых метрик, которые нужны для расчетов
    и производит расчеты по предполагаемой цене токена.
    По окончанию работы вызывает функцию create_basic_report().
    """

    user_coin_name = message.text.upper().replace(" ", "")
    fundraise = None
    user_data = await get_user_from_redis_or_db(message.from_user.id)
    garbage_categories = load_document_for_garbage_list(START_TITLE_FOR_GARBAGE_CATEGORIES, END_TITLE_FOR_GARBAGE_CATEGORIES)
    language = user_data.get("language", "ENG")

    if await validate_user_input(user_coin_name, message, state):
        return
    else:
        await message.answer(
            await phrase_by_user(
                "wait_for_calculations", message.from_user.id, session_local
            )
        )

    twitter_name, description, lower_name, categories = await get_twitter_link_by_symbol(user_coin_name)
    twitter_name = REPLACED_PROJECT_TWITTER.get(twitter_name, twitter_name)
    if not lower_name:
        lower_name = await get_lower_name(user_coin_name)

    coin_description = await get_coin_description(lower_name)
    if description:
        coin_description += description

    if not categories or len(categories) == 0:
        await message.answer(
            await phrase_by_user(
                "error_project_inappropriate_category",
                message.from_user.id,
                session_local,
            )
        )

    # Получаем или создаём категории в БД
    category_instances = []
    for category_name in categories:
        if category_name not in garbage_categories:
            category_instance, _ = await get_or_create(Category, category_name=category_name)
            category_instances.append(category_instance)

    if len(category_instances) == 0:
        return await message.answer(
            await phrase_by_user(
                "category_in_garbage_list",
                message.from_user.id,
                session_local,
            )
        )

    new_project, _ = await get_or_create(Project, coin_name=lower_name)

    # Добавляем связи между проектом и категориями
    for category in category_instances:
        existing_association = await get_one(
            project_category_association, project_id=new_project.id, category_id=category.id
        )

        if not existing_association:
            await create_association(
                project_category_association,
                project_id=new_project.id,
                category_id=category.id
            )

    try:
        header_params = get_header_params(user_coin_name)

        coin_data = await fetch_coinmarketcap_data(
            message, user_coin_name, **header_params
        )
        if not coin_data:
            coin_data = await fetch_coingecko_data(user_coin_name)
            if not coin_data:
                return await message.answer(
                    await phrase_by_user(
                        "error_input_token_from_user",
                        message.from_user.id,
                        session_local,
                    )
                )

        circulating_supply = coin_data["circulating_supply"]
        total_supply = coin_data["total_supply"]
        price = coin_data["price"]
        capitalization = coin_data["capitalization"]
        coin_fdv = coin_data["coin_fdv"]

        # Обновление или создание BasicMetrics
        await update_or_create(
            model=BasicMetrics,
            project_id=new_project.id,
            defaults={
                "entry_price": price,
                "market_price": price,
            },
        )

        # Обновление или создание Tokenomics
        await update_or_create(
            model=Tokenomics,
            project_id=new_project.id,
            defaults={
                "total_supply": total_supply,
                "circ_supply": circulating_supply,
                "capitalization": capitalization,
                "fdv": coin_fdv,
            },
        )

        if new_project:
            await get_or_create(
                Calculation,
                defaults={"date": datetime.now()},
                user_id=message.from_user.id,
                project_id=new_project.id,
            )

        project_info = await get_user_project_info(user_coin_name)
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        top_and_bottom = project_info.get("top_and_bottom")
        market_metrics = project_info.get("market_metrics")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")

        tasks = await check_and_run_tasks(
            project=new_project,
            price=price,
            top_and_bottom=top_and_bottom,
            funds_profit=funds_profit,
            social_metrics=social_metrics,
            market_metrics=market_metrics,
            investing_metrics=investing_metrics,
            manipulative_metrics=manipulative_metrics,
            network_metrics=network_metrics,
            twitter_name=twitter_name,
            user_coin_name=user_coin_name,
            lower_name=lower_name,
            model_mapping=MODEL_MAPPING,
        )

        if user_coin_name not in TICKERS:
            await update_or_create(
                Project,
                id=new_project.id,
                defaults={
                    "coin_name": user_coin_name,
                },
            )
        else:
            new_project = await get_one(Project, coin_name=user_coin_name)

        await update_or_create(
            BasicMetrics,
            project_id=new_project.id,
            defaults={
                "entry_price": price,
                "market_price": price,
            },
        )

        if tasks.get("social_metrics", []):
            (twitter_subs, twitter_twitterscore) = tasks.get(
                "social_metrics", []
            )[0]
            twitter = twitter_subs
            twitterscore = twitter_twitterscore
            if twitter and twitterscore:
                await update_or_create(
                    SocialMetrics,
                    project_id=new_project.id,
                    defaults={
                        "twitter": twitter,
                        "twitterscore": twitterscore,
                    },
                )

        if tasks.get("investing_metrics", []):
            fundraise, investors = tasks.get("investing_metrics", [])[0]
            if user_coin_name not in TICKERS and fundraise and investors:
                await update_or_create(
                    InvestingMetrics,
                    project_id=new_project.id,
                    defaults={"fundraise": fundraise, "fund_level": investors},
                )
            elif fundraise:
                await update_or_create(
                    InvestingMetrics,
                    project_id=new_project.id,
                    defaults={
                        "fundraise": fundraise,
                    },
                )

        if tasks.get("network_metrics", []):
            last_tvl = tasks.get("network_metrics", [])[0]
            if last_tvl and price and total_supply:
                await update_or_create(
                    NetworkMetrics,
                    project_id=new_project.id,
                    defaults={
                        "tvl": last_tvl if last_tvl else 0,
                        "tvl_fdv": last_tvl / (price * total_supply)
                        if last_tvl and total_supply and price
                        else 0,
                    },
                )

        if tasks.get("manipulative_metrics", []):
            top_100_wallets = tasks.get("manipulative_metrics", [])[0]
            await update_or_create(
                ManipulativeMetrics,
                project_id=new_project.id,
                defaults={
                    "fdv_fundraise": (price * total_supply) / fundraise
                    if fundraise
                    else None,
                    "top_100_wallet": top_100_wallets,
                },
            )

        funds_profit_data = tasks.get("funds_profit", [])
        output_string = (
            "\n".join(funds_profit_data[0])
            if funds_profit_data and funds_profit_data[0]
            else ""
        )

        if output_string and output_string != "":
            await update_or_create(
                FundsProfit,
                project_id=new_project.id,
                defaults={
                    "distribution": output_string,
                },
            )

        if tasks.get("market_metrics", []):
            fail_high, growth_low = tasks.get("market_metrics", [])[0]
            await update_or_create(
                MarketMetrics,
                project_id=new_project.id,
                defaults={"fail_high": fail_high, "growth_low": growth_low},
            )

        if tasks.get("top_and_bottom", []):
            max_price, min_price = tasks.get("top_and_bottom", [])[0]
            await update_or_create(
                TopAndBottom,
                project_id=new_project.id,
                defaults={
                    "lower_threshold": min_price,
                    "upper_threshold": max_price,
                },
            )

        data = {
            "user_coin_name": user_coin_name,
            "categories": categories,
        }

        await state.update_data(**data)
        report = await create_basic_report(
            session_local, state, message=message, user_id=message.from_user.id
        )

        await message.answer(report)
        await message.answer(
            phrase_by_language("input_next_token_for_basic_report", language),
            reply_markup=ReplyKeyboardRemove(),
        )

    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))


@calculate_router.message(CalculateProject.waiting_for_data)
async def receive_data(message: types.Message, state: FSMContext):
    """
    Функция, для обработки выбранного пользователем пункта 'Блок анализа и оценки проектов'.
    Функция проверяет существование в базе данных базовых метрик, которые нужны для расчетов
    и производит расчеты по предполагаемой цене токена.
    По окончанию работы вызывает функцию create_pdf_report().
    """

    user_coin_name = message.text.upper().replace(" ", "")
    investors = None
    price = None
    total_supply = None
    fundraise = None
    calculation_record = None
    user_data = await get_user_from_redis_or_db(message.from_user.id)
    garbage_categories = load_document_for_garbage_list(START_TITLE_FOR_GARBAGE_CATEGORIES, END_TITLE_FOR_GARBAGE_CATEGORIES)
    language = user_data.get("language", "ENG")

    user_input = await validate_user_input(user_coin_name, message, state)
    if user_input:
        return await message.answer(user_input)
    else:
        # Сообщаем пользователю, что будут производиться расчеты
        await message.answer(
            await phrase_by_user(
                "wait_for_calculations", message.from_user.id, session_local
            )
        )

    twitter_name, description, lower_name, categories = await get_twitter_link_by_symbol(user_coin_name)
    coin_description = await get_coin_description(lower_name)
    if description:
        coin_description += description

    token_description = await agent_handler(
        "description", topic=coin_description, language=language
    )

    if not categories or len(categories) == 0:
        return await message.answer(
            await phrase_by_user(
                "error_project_inappropriate_category",
                message.from_user.id,
                session_local,
            )
        )

    # Получаем или создаём категории в БД
    category_instances = []
    for category_name in categories:
        if category_name not in garbage_categories:
            category_instance, _ = await get_or_create(Category, category_name=category_name)
            category_instances.append(category_instance)

    if len(category_instances) == 0:
        return await message.answer(
            await phrase_by_user(
                "category_in_garbage_list",
                message.from_user.id,
                session_local,
            )
        )

    # Получаем проект (если его ещё нет)
    project_instance, _ = await get_or_create(Project, coin_name=lower_name)

    # Добавляем связи между проектом и категориями
    for category in category_instances:
        existing_association = await get_one(
            project_category_association, project_id=project_instance.id, category_id=category.id
        )

        if not existing_association:
            await create_association(
                project_category_association,
                project_id=project_instance.id,
                category_id=category.id
            )

    project_info = await get_user_project_info(user_coin_name)
    base_project = project_info.get("project")
    tokenomics_data = project_info.get("tokenomics_data")
    basic_metrics = project_info.get("basic_metrics")
    investing_metrics = project_info.get("investing_metrics")
    social_metrics = project_info.get("social_metrics")
    funds_profit = project_info.get("funds_profit")
    top_and_bottom = project_info.get("top_and_bottom")
    market_metrics = project_info.get("market_metrics")
    manipulative_metrics = project_info.get("manipulative_metrics")
    network_metrics = project_info.get("network_metrics")

    header_params = get_header_params(coin_name=user_coin_name)
    twitter_name = await get_twitter_link_by_symbol(user_coin_name)

    try:
        if (
            not tokenomics_data
            or not tokenomics_data.circ_supply
            or not tokenomics_data.total_supply
            or not tokenomics_data.capitalization
            or not tokenomics_data.fdv
            or not basic_metrics.market_price
        ):
            coinmarketcap_data = await fetch_coinmarketcap_data(
                message, user_coin_name, **header_params
            )
            if coinmarketcap_data:
                circulating_supply = coinmarketcap_data["circulating_supply"]
                total_supply = coinmarketcap_data["total_supply"]
                price = coinmarketcap_data["price"]
                capitalization = coinmarketcap_data["capitalization"]
                coin_fdv = coinmarketcap_data["coin_fdv"]

            else:
                coin_data = await fetch_coingecko_data(user_coin_name)
                print("coingecko_data: ", coin_data)
                if not coin_data:
                    return await message.answer(
                        await phrase_by_user(
                            "error_input_token_from_user",
                            message.from_user.id,
                            session_local,
                        )
                    )

                circulating_supply = coin_data["circulating_supply"]
                total_supply = coin_data["total_supply"]
                price = coin_data["price"]
                capitalization = coin_data["capitalization"]
                coin_fdv = coin_data["coin_fdv"]

            await update_or_create(
                Tokenomics,
                project_id=base_project.id,
                defaults={
                    "capitalization": capitalization,
                    "total_supply": total_supply,
                    "circ_supply": circulating_supply,
                    "fdv": coin_fdv,
                },
            )

            await update_or_create(
                BasicMetrics,
                project_id=base_project.id,
                defaults={"entry_price": price, "market_price": price},
            )
        else:
            total_supply = tokenomics_data.total_supply
            price = basic_metrics.market_price

    except Exception as e:
        raise ExceptionError(str(e))

    tasks = await check_and_run_tasks(
        project=base_project,
        price=price,
        top_and_bottom=top_and_bottom,
        funds_profit=funds_profit,
        social_metrics=social_metrics,
        market_metrics=market_metrics,
        investing_metrics=investing_metrics,
        manipulative_metrics=manipulative_metrics,
        network_metrics=network_metrics,
        twitter_name=twitter_name,
        user_coin_name=user_coin_name,
        lower_name=lower_name,
        model_mapping=MODEL_MAPPING,
    )

    if tasks.get("social_metrics", []):
        (twitter_subs, twitter_twitterscore) = tasks.get("social_metrics", [])[0]
        twitter = twitter_subs
        twitterscore = twitter_twitterscore
        if twitter and twitterscore:
            await update_or_create(
                SocialMetrics,
                project_id=base_project.id,
                defaults={"twitter": twitter, "twitterscore": twitterscore},
            )

    if tasks.get("investing_metrics", []):
        fundraise, investors = tasks.get("investing_metrics", [])[0]
        if user_coin_name not in TICKERS and fundraise and investors:
            await update_or_create(
                InvestingMetrics,
                project_id=base_project.id,
                defaults={"fundraise": fundraise, "fund_level": investors},
            )
        elif fundraise:
            await update_or_create(
                InvestingMetrics,
                project_id=base_project.id,
                defaults={
                    "fundraise": fundraise,
                },
            )

    if tasks.get("network_metrics", []):
        last_tvl = tasks.get("network_metrics", [])[0]
        if last_tvl and price and total_supply:
            await update_or_create(
                NetworkMetrics,
                project_id=base_project.id,
                defaults={
                    "tvl": last_tvl if last_tvl else 0,
                    "tvl_fdv": last_tvl / (price * total_supply)
                    if last_tvl and total_supply and price
                    else 0,
                },
            )

    if tasks.get("manipulative_metrics", []):
        top_100_wallets = tasks.get("manipulative_metrics", [])[0]
        await update_or_create(
            ManipulativeMetrics,
            project_id=base_project.id,
            defaults={
                "fdv_fundraise": (price * total_supply) / fundraise
                if fundraise
                else None,
                "top_100_wallet": top_100_wallets,
            },
        )

    new_project = await process_metrics(
        user_coin_name,
        base_project,
        categories,
        tasks,
        price,
        total_supply,
        fundraise,
        investors,
    )

    if new_project:
        calculation_record, created = await get_or_create(
            Calculation,
            user_id=message.from_user.id,
            project_id=new_project.id,
            defaults={"date": datetime.now()},
        )

    data = {
        "new_project": new_project.to_dict(),
        "calculation_record": calculation_record.to_dict(),
        "token_description": token_description,
        "twitter_name": twitter_name,
        "coin_name": user_coin_name,
        "price": price,
        "total_supply": total_supply,
    }

    await state.update_data(**data)
    result = await create_pdf_report(
        session_local, state, message=message, user_id=message.from_user.id
    )

    if isinstance(result, tuple):
        result_message, pdf_output, filename = result

        await message.answer(result_message)
        await message.answer_document(
            document=BufferedInputFile(
                pdf_output.getvalue(), filename=filename
            )
        )
        await message.answer(
            await phrase_by_user(
                "input_next_token_for_analysis",
                message.from_user.id,
                session_local,
            ),
            reply_markup=ReplyKeyboardRemove(),
        )

    elif isinstance(result, str):
        await message.answer(result)
