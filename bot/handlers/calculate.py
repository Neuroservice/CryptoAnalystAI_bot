import logging
import traceback
import xlsxwriter

from datetime import datetime
from io import BytesIO
from typing import Optional, Union
from aiogram import Router, types, Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardRemove,
    BufferedInputFile,
    Message
)

from bot.config import API_TOKEN
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
    AgentAnswer, User
)
from bot.utils.consts import user_languages, prepare_ru_data_for_analysis
from bot.utils.consts import (
    tickers,
    field_mapping,
    model_mapping,
    checking_map,
    dejavu_path,
    logo_path, color_palette, get_header_params, SessionLocal, calculations_choices, async_session, session_local,
    sync_session
)
from bot.utils.gpt import (
    agent_handler
)
from bot.utils.keyboards.calculate_keyboards import analysis_type_keyboard
from bot.utils.keyboards.history_keyboards import file_format_keyboard
from bot.utils.metrics import (
    process_metrics,
    check_missing_fields,
    generate_cells_content,
    create_project_data_row
)
from bot.utils.metrics_evaluation import determine_project_tier, calculate_tokenomics_score, analyze_project_metrics, \
    calculate_project_score
from bot.utils.project_data import (
    get_project_and_tokenomics,
    get_full_info,
    get_twitter_link_by_symbol,
    fetch_coinmarketcap_data,
    get_user_project_info,
    get_coin_description,
    standardize_category,
    get_lower_name,
    check_and_run_tasks,
    calculate_expected_x,
    send_long_message,
    get_top_projects_by_capitalization_and_category,
    process_and_update_models, fetch_coingecko_data, generate_flags_answer, find_record, update_or_create
)
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.resources.files_worker.pdf_worker import generate_pie_chart, PDF
from bot.utils.resources.headers.headers import ru_additional_headers, eng_additional_headers
from bot.utils.resources.headers.headers_handler import results_header_by_user, calculation_header_by_user
from bot.utils.validations import validate_user_input, extract_overall_category, save_execute

calculate_router = Router()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CalculateProject(StatesGroup):
    choosing_analysis_type = State()
    choosing_file_format = State()
    waiting_for_data = State()
    waiting_for_basic_data = State()
    waiting_for_basic_results = State()
    waiting_for_next_action = State()
    waiting_for_excel = State()
    waiting_for_pdf = State()


@calculate_router.message(CalculateProject.waiting_for_excel)
async def await_to_create_excel(message: types.Message, state: FSMContext):
    await create_excel(session_local, state, message)


@calculate_router.message(CalculateProject.waiting_for_pdf)
async def await_to_create_pdf(message: types.Message, state: FSMContext):
    await create_pdf(session_local, state, message)


@calculate_router.message(CalculateProject.waiting_for_basic_results)
async def await_basic_report(message: types.Message, state: FSMContext):
    await create_basic_report(session_local, state, message)


@calculate_router.message(CalculateProject.waiting_for_next_action)
async def handle_next_action(message: types.Message, state: FSMContext):
    user_choice = message.text
    if user_choice == "Продолжить с другим проектом":
        await message.answer("Пожалуйста, выберите новый проект для расчета.")
        await file_format_chosen(message, state)
    elif user_choice == "Начать заново /start":
        await message.answer("Вы начали заново. Введите /start для начала.")
        await state.clear()
    else:
        await message.answer("Пожалуйста, выберите вариант: продолжить или начать заново.")


async def project_chosen(message: types.Message):
    await message.answer(phrase_by_user("file_format", message.from_user.id), reply_markup=file_format_keyboard())


@calculate_router.message(lambda message: message.text == 'Анализ проектов' or message.text == 'Project analysis' or message.text == "Пожалуйста, выберите новый проект для расчета.")
async def project_chosen(message: types.Message, state: FSMContext):
    await message.answer(phrase_by_user("calculation_type_choice", message.from_user.id), reply_markup=analysis_type_keyboard(message.from_user.id))
    await state.set_state(CalculateProject.choosing_analysis_type)


@calculate_router.message(CalculateProject.choosing_analysis_type)
async def analysis_type_chosen(message: types.Message, state: FSMContext):
    analysis_type = message.text.lower()

    if analysis_type in ['блок ребалансировки портфеля', 'block of portfolio rebalancing']:
        await message.answer(phrase_by_user("rebalancing_input_token", message.from_user.id), reply_markup=ReplyKeyboardRemove())
        await state.set_state(CalculateProject.waiting_for_basic_data)

    elif analysis_type in ['блок анализа и оценки проектов', 'block of projects analysis and evaluation']:
        await message.answer(phrase_by_user("file_format", message.from_user.id), reply_markup=file_format_keyboard())
        await state.set_state(CalculateProject.choosing_file_format)


@calculate_router.message(CalculateProject.choosing_file_format)
async def file_format_chosen(message: types.Message, state: FSMContext):
    file_format = message.text.lower()

    if file_format in ['pdf', 'excel']:
        await state.update_data(file_format=file_format)
        await message.answer(phrase_by_user("analysis_input_token", message.from_user.id), reply_markup=ReplyKeyboardRemove())
        await state.set_state(CalculateProject.waiting_for_data)
    else:
        await message.answer(phrase_by_user("error_file_format_message", message.from_user.id), reply_markup=file_format_keyboard())


@calculate_router.message(CalculateProject.waiting_for_basic_data)
async def receive_basic_data(message: types.Message, state: FSMContext):
    user_coin_name = message.text.upper().replace(" ", "")
    new_project = None
    price = None
    total_supply = None
    fundraise = None
    calculation_record = None
    language = 'RU' if user_languages.get(message.from_user.id) == 'RU' else 'ENG'

    if await validate_user_input(user_coin_name, message, state):
        return

    twitter_name, description, lower_name = await get_twitter_link_by_symbol(user_coin_name)
    if not lower_name:
        lower_name = await get_lower_name(user_coin_name)

    coin_description = await get_coin_description(lower_name)
    if description:
        coin_description += description

    # Получение категории проекта
    category_answer = agent_handler("category", topic=coin_description)
    overall_category = extract_overall_category(category_answer)
    chosen_project_name = standardize_category(overall_category)

    if chosen_project_name == 'Unknown Category':
        await message.answer(phrase_by_user("error_project_inappropriate_category", message.from_user.id))

    try:
        projects, tokenomics_data_list = await get_project_and_tokenomics(async_session, chosen_project_name, user_coin_name)
        top_projects = get_top_projects_by_capitalization_and_category(tokenomics_data_list)

        results = []
        agents_info = []
        for index, (project, tokenomics_data) in enumerate(top_projects, start=1):
            for tokenomics in tokenomics_data:
                header_params = get_header_params(user_coin_name)

                coin_data = await fetch_coinmarketcap_data(message, user_coin_name, **header_params)
                if not coin_data:
                    coin_data = await fetch_coingecko_data(user_coin_name)
                    if not coin_data:
                        await message.answer("Ошибка: данные о монете не получены. Проверьте введённый тикер.")
                        return

                circulating_supply = coin_data["circulating_supply"]
                total_supply = coin_data["total_supply"]
                price = coin_data["price"]
                capitalization = coin_data["capitalization"]
                coin_fdv = coin_data["coin_fdv"]

                base_project = await find_record(Project, session_local, coin_name=project.coin_name)

                fdv = tokenomics.fdv if tokenomics.fdv else 0
                calculation_result = calculate_expected_x(
                    entry_price=price,
                    total_supply=total_supply,
                    fdv=fdv,
                )

                existing_project = await find_record(Project, session_local, coin_name=user_coin_name)
                if existing_project:
                    new_project = existing_project
                else:
                    new_project = Project(
                        category=chosen_project_name,
                        coin_name=user_coin_name
                    )
                    session_local.add(new_project)

                existing_basic_metrics = await find_record(BasicMetrics, session_local, project_id=new_project.id)
                if not existing_basic_metrics:
                    basic_metrics = BasicMetrics(
                        project_id=new_project.id,
                        entry_price=price,
                        sphere=chosen_project_name,
                        market_price=price,
                    )
                    session_local.add(basic_metrics)

                existing_tokenomic = await find_record(Tokenomics, session_local, project_id=new_project.id)
                if not existing_tokenomic:
                    tokenomic = Tokenomics(
                        project_id=new_project.id,
                        total_supply=total_supply,
                        circ_supply=circulating_supply,
                        capitalization=capitalization,
                        fdv=coin_fdv
                    )
                    session_local.add(tokenomic)
                elif existing_tokenomic.capitalization != capitalization:
                    existing_tokenomic.capitalization = capitalization
                    session_local.add(existing_tokenomic)

                if "error" in calculation_result:
                    raise ValueError(calculation_result["error"])

                fair_price = calculation_result['fair_price']
                fair_price = f"{fair_price:.5f}" if isinstance(fair_price, (int, float)) else "Ошибка в расчетах" if user_languages.get(message.from_user.id) == 'RU' else "Error on market"

                if project.coin_name in tickers:
                    results.append(calculations_choices[language].format(
                        index=index,
                        user_coin_name=user_coin_name,
                        project_coin_name=project.coin_name,
                        growth=round((float(calculation_result['expected_x']) - 1.0) * 100, 2),
                        fair_price=fair_price
                    ))

                agents_info.append([
                    index,
                    user_coin_name,
                    project.coin_name,
                    round((float(calculation_result['expected_x']) - 1.0) * 100, 2),
                    fair_price
                ])

        if new_project:
            calculation_record = Calculation(
                user_id=message.from_user.id,
                project_id=new_project.id,
                date=datetime.now()
            )
            session_local.add(calculation_record)

        project_info = await get_user_project_info(session_local, user_coin_name)
        tokenomics_data = project_info.get("tokenomics_data")
        basic_metrics = project_info.get("basic_metrics")
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
            session=session_local,
            model_mapping=model_mapping
        )

        await session_local.commit()
        if user_coin_name not in tickers:
            await update_or_create(
                session_local, Project,
                id=new_project.id,
                defaults={
                    'category': chosen_project_name,
                    'coin_name': user_coin_name
                },
            )
        else:
            new_project = await find_record(Project, session_local, coin_name=user_coin_name)

        await update_or_create(
            session_local, BasicMetrics,
            project_id=new_project.id,
            defaults={
                'entry_price': price,
                'sphere': chosen_project_name,
                'market_price': price,
            },
        )

        if tasks.get("social_metrics", []):
            (twitter_subs, twitter_twitterscore) = tasks.get("social_metrics", [])[0]
            twitter = twitter_subs
            twitterscore = twitter_twitterscore
            if twitter and twitterscore:
                await update_or_create(
                    session_local, SocialMetrics,
                    project_id=new_project.id,
                    defaults={
                        'twitter': twitter,
                        'twitterscore': twitterscore
                    }
                )

        if tasks.get("investing_metrics", []):
            fundraise, investors = tasks.get("investing_metrics", [])[0]
            if user_coin_name not in tickers and fundraise and investors:
                await update_or_create(
                    session_local, InvestingMetrics,
                    project_id=new_project.id,
                    defaults={
                        'fundraise': fundraise,
                        'fund_level': investors
                    },
                )
            elif fundraise:
                await update_or_create(
                    session_local, InvestingMetrics,
                    project_id=new_project.id,
                    defaults={
                        'fundraise': fundraise,
                    },
                )

        if tasks.get("network_metrics", []):
            last_tvl = tasks.get("network_metrics", [])[0]
            if last_tvl and price and total_supply:
                await update_or_create(
                    session_local, NetworkMetrics,
                    project_id=new_project.id,
                    defaults={
                        'tvl': last_tvl if last_tvl else 0,
                        'tvl_fdv': last_tvl / (price * total_supply) if last_tvl and total_supply and price else 0
                    },
                )

        if tasks.get("manipulative_metrics", []):
            top_100_wallets = tasks.get("manipulative_metrics", [])[0]
            await update_or_create(
                session_local, ManipulativeMetrics,
                project_id=new_project.id,
                defaults={
                    'fdv_fundraise': (price * total_supply) / fundraise if fundraise else None,
                    'top_100_wallet': top_100_wallets
                }
            )

        funds_profit_data = tasks.get("funds_profit", [])
        output_string = '\n'.join(funds_profit_data[0]) if funds_profit_data and funds_profit_data[0] else ''

        if output_string and output_string != '':
            await update_or_create(
                session_local, FundsProfit,
                project_id=new_project.id,
                defaults={
                    'distribution': output_string,
                }
            )

        if tasks.get("market_metrics", []):
            fail_high, growth_low = tasks.get("market_metrics", [])[0]
            await update_or_create(
                session_local, MarketMetrics,
                project_id=new_project.id,
                defaults={'fail_high': fail_high, 'growth_low': growth_low},
            )

        if tasks.get("top_and_bottom", []):
            max_price, min_price = tasks.get("top_and_bottom", [])[0]
            await update_or_create(
                session_local, TopAndBottom,
                project_id=new_project.id,
                defaults={'lower_threshold': min_price, 'upper_threshold': max_price},
            )

        project_info = await get_user_project_info(session_local, user_coin_name)
        tokenomics_data = project_info.get("tokenomics_data")
        basic_metrics = project_info.get("basic_metrics")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        top_and_bottom = project_info.get("top_and_bottom")
        market_metrics = project_info.get("market_metrics")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")

        metrics_data = {
            "circ_supply": tokenomics_data.circ_supply if tokenomics_data else None,
            "total_supply": tokenomics_data.total_supply if tokenomics_data else None,
            "capitalization": tokenomics_data.capitalization if tokenomics_data else None,
            "fdv": tokenomics_data.fdv if tokenomics_data else None,
            "entry_price": basic_metrics.entry_price if basic_metrics else None,
            "market_price": basic_metrics.market_price if basic_metrics else None,
            "sphere": basic_metrics.sphere if basic_metrics else None,
            "fundraise": investing_metrics.fundraise if investing_metrics else None,
            "fund_level": investing_metrics.fund_level if investing_metrics else None,
            "twitter": social_metrics.twitter if social_metrics else None,
            "twitterscore": social_metrics.twitterscore if social_metrics else None,
            "distribution": funds_profit.distribution if funds_profit else None,
            "lower_threshold": top_and_bottom.lower_threshold if top_and_bottom else None,
            "upper_threshold": top_and_bottom.upper_threshold if top_and_bottom else None,
            "fail_high": market_metrics.fail_high if market_metrics else None,
            "growth_low": market_metrics.growth_low if market_metrics else None,
            "top_100_wallet": manipulative_metrics.top_100_wallet if manipulative_metrics else None,
            "tvl": network_metrics.tvl if network_metrics else None
        }

        missing_fields, examples = check_missing_fields(metrics_data, checking_map)
        missing_fields_string = ', '.join(missing_fields)

        data = {
            "user_coin_name": user_coin_name,
            "calculation_record": calculation_record.to_dict(),
            "category_answer": category_answer,
            "chosen_project": chosen_project_name,
            "new_project": new_project.to_dict(),
            "results": results,
            "agents_info": agents_info,
            "missing_fields": missing_fields,
            "twitter_name": twitter_name,
        }
        await session_local.commit()

        if missing_fields_string:
            response_message = (
                    f"Отсутствующие данные для запроса: {missing_fields_string}.\n"
                    "Пожалуйста, предоставьте эти данные в следующем формате:\n"
                    + '\n'.join(examples)
            )
            await message.answer(response_message)
            await state.update_data(**data)
            await state.set_state(CalculateProject.waiting_for_basic_results)
        else:
            await state.update_data(**data)
            await create_basic_report(session_local, state, message='-', user_id=message.from_user.id)

    except ValueError:
        print("Error creating")
        error_message = traceback.format_exc()
        await message.answer(f"{phrase_by_user('error_not_valid_input_data', message.from_user.id)}\n{error_message}")


@calculate_router.message(CalculateProject.waiting_for_data)
async def receive_data(message: types.Message, state: FSMContext):
    user_coin_name = message.text.upper().replace(" ", "")
    investors = None
    price = None
    total_supply = None
    fundraise = None
    calculation_record = None

    if await validate_user_input(user_coin_name, message, state):
        return
    else:
        # Сообщаем пользователю, что будут производиться расчеты
        await message.answer(phrase_by_user("wait_for_calculations", message.from_user.id))

    data = await state.get_data()
    selected_format = data.get("file_format")

    twitter_name, description, lower_name = await get_twitter_link_by_symbol(user_coin_name)
    coin_description = await get_coin_description(lower_name)
    if description:
        coin_description += description

    category_answer = agent_handler("category", topic=coin_description)
    overall_category = extract_overall_category(category_answer)
    chosen_project = standardize_category(overall_category)

    if chosen_project == 'Unknown Category':
        await message.answer(phrase_by_user("error_project_inappropriate_category", message.from_user.id))

    project_info = await get_user_project_info(session_local, user_coin_name)
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

    if selected_format == 'excel':
        try:
            header_params = get_header_params(coin_name=user_coin_name)

            if not tokenomics_data or not tokenomics_data.circ_supply or not tokenomics_data.total_supply or not tokenomics_data.capitalization or not tokenomics_data.fdv or not basic_metrics.market_price:
                coinmarketcap_data = await fetch_coinmarketcap_data(message, user_coin_name, **header_params)
                if coinmarketcap_data:
                    circulating_supply = coinmarketcap_data['circulating_supply']
                    total_supply = coinmarketcap_data['total_supply']
                    price = coinmarketcap_data['price']
                    capitalization = coinmarketcap_data['capitalization']
                    coin_fdv = coinmarketcap_data['coin_fdv']

                    await update_or_create(
                        session_local, Tokenomics,
                        project_id=base_project.id,
                        defaults={
                            'capitalization': capitalization,
                            'total_supply': total_supply,
                            'circ_supply': circulating_supply,
                            'fdv': coin_fdv
                        },
                    )

                else:
                    # Сообщаем пользователю, что такой токен не найден. Предлагаем ввести новый
                    await message.answer(phrase_by_user("error_input_token_from_user", message.from_user.id))
            else:
                total_supply = tokenomics_data.total_supply
                price = basic_metrics.market_price

        except Exception as e:
            if 'get_header_params' in str(e):
                logging.error(f"Ошибка при получении параметров заголовка: {e}")
            elif 'fetch_coinmarketcap_data' in str(e):
                logging.error(f"Ошибка при получении данных с CoinMarketCap: {e}")
            elif 'update_or_create' in str(e):
                logging.error(f"Ошибка при обновлении или создании данных в базе: {e}")
            elif 'commit' in str(e):
                logging.error(f"Ошибка при сохранении изменений в базе: {e}")
            else:
                logging.error(f"Общая ошибка при обработке данных токеномики: {e}")

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
            session=session_local,
            model_mapping=model_mapping
        )

        if tasks.get("social_metrics", []):
            (twitter_subs, twitter_twitterscore) = tasks.get("social_metrics", [])[0]
            twitter = twitter_subs
            twitterscore = twitter_twitterscore
            if twitter and twitterscore:
                await update_or_create(
                    session_local, SocialMetrics,
                    project_id=base_project.id,
                    defaults={
                        'twitter': twitter,
                        'twitterscore': twitterscore
                    }
                )

        if tasks.get("investing_metrics", []):
            fundraise, investors = tasks.get("investing_metrics", [])[0]
            if user_coin_name not in tickers and fundraise and investors:
                await update_or_create(
                    session_local, InvestingMetrics,
                    project_id=base_project.id,
                    defaults={
                        'fundraise': fundraise,
                        'fund_level': investors
                    },
                )
            elif fundraise:
                await update_or_create(
                    session_local, InvestingMetrics,
                    project_id=base_project.id,
                    defaults={
                        'fundraise': fundraise,
                    },
                )

        if tasks.get("network_metrics", []):
            last_tvl = tasks.get("network_metrics", [])[0]
            if last_tvl and price and total_supply:
                await update_or_create(
                    session_local, NetworkMetrics,
                    project_id=base_project.id,
                    defaults={
                        'tvl': last_tvl if last_tvl else 0,
                        'tvl_fdv': last_tvl / (price * total_supply) if last_tvl and total_supply and price else 0
                    },
                )

        if tasks.get("manipulative_metrics", []):
            top_100_wallets = tasks.get("manipulative_metrics", [])[0]
            await update_or_create(
                session_local, ManipulativeMetrics,
                project_id=base_project.id,
                defaults={
                    'fdv_fundraise': (price * total_supply) / fundraise if fundraise else None,
                    'top_100_wallet': top_100_wallets
                }
            )

        project_info = await get_user_project_info(session_local, user_coin_name)
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

        new_project = await process_metrics(session_local, user_coin_name, base_project, chosen_project, tasks, price, total_supply, fundraise, investors)

        if new_project:
            calculation_record = Calculation(
                user_id=message.from_user.id,
                project_id=new_project.id,
                date=datetime.now()
            )
            session_local.add(calculation_record)

        metrics_data = {
            "circ_supply": tokenomics_data.circ_supply if tokenomics_data else None,
            "total_supply": tokenomics_data.total_supply if tokenomics_data else None,
            "capitalization": tokenomics_data.capitalization if tokenomics_data else None,
            "fdv": tokenomics_data.fdv if tokenomics_data else None,
            "entry_price": basic_metrics.entry_price if basic_metrics else None,
            "market_price": basic_metrics.market_price if basic_metrics else None,
            "sphere": basic_metrics.sphere if basic_metrics else None,
            "fundraise": investing_metrics.fundraise if investing_metrics else None,
            "fund_level": investing_metrics.fund_level if investing_metrics else None,
            "twitter": social_metrics.twitter if social_metrics else None,
            "twitterscore": social_metrics.twitterscore if social_metrics else None,
            "distribution": funds_profit.distribution if funds_profit else None,
            "lower_threshold": top_and_bottom.lower_threshold if top_and_bottom else None,
            "upper_threshold": top_and_bottom.upper_threshold if top_and_bottom else None,
            "fail_high": market_metrics.fail_high if market_metrics else None,
            "growth_low": market_metrics.growth_low if market_metrics else None,
            "top_100_wallet": manipulative_metrics.top_100_wallet if manipulative_metrics else None,
            "tvl": network_metrics.tvl if network_metrics else None
        }
        data = {
            "new_project": project_info,
            "calculation_record": calculation_record.to_dict(),
            "category_answer": category_answer,
            "chosen_project": chosen_project,
            "twitter_name": twitter_name,
            "coin_name": user_coin_name,
            "price": price,
            "total_supply": total_supply,
        }

        missing_fields, examples = check_missing_fields(metrics_data, checking_map)
        missing_fields_string = ', '.join(missing_fields)

        await session_local.commit()

        if missing_fields_string:
            response_message = (
                f"Отсутствующие данные для запроса: {missing_fields_string}.\n"
                "Пожалуйста, предоставьте эти данные в следующем формате:\n"
                + '\n'.join(examples)
            )
            await message.answer(response_message)
            await state.update_data(**data)
            await state.set_state(CalculateProject.waiting_for_excel)
        else:
            await state.update_data(**data)
            await create_excel(session_local, state, message='-', user_id=message.from_user.id)

    elif selected_format == 'pdf':

        header_params = get_header_params(coin_name=user_coin_name)
        twitter_name = await get_twitter_link_by_symbol(user_coin_name)

        try:
            if not tokenomics_data or not tokenomics_data.circ_supply or not tokenomics_data.total_supply or not tokenomics_data.capitalization or not tokenomics_data.fdv or not basic_metrics.market_price:
                coinmarketcap_data = await fetch_coinmarketcap_data(message, user_coin_name, **header_params)
                if coinmarketcap_data:
                    circulating_supply = coinmarketcap_data['circulating_supply']
                    total_supply = coinmarketcap_data['total_supply']
                    price = coinmarketcap_data['price']
                    capitalization = coinmarketcap_data['capitalization']
                    coin_fdv = coinmarketcap_data['coin_fdv']

                    await update_or_create(
                        session_local, Tokenomics,
                        project_id=base_project.id,
                        defaults={
                            'capitalization': capitalization,
                            'total_supply': total_supply,
                            'circ_supply': circulating_supply,
                            'fdv': coin_fdv
                        },
                    )

                    await update_or_create(
                        session_local, BasicMetrics,
                        project_id=base_project.id,
                        defaults={
                            'entry_price': price,
                            'market_price': price
                        },
                    )

                else:
                    # Сообщаем пользователю, что такой токен не найден. Предлагаем ввести новый
                    await message.answer(phrase_by_user("error_input_token_from_user", message.from_user.id))
            else:
                total_supply = tokenomics_data.total_supply
                price = basic_metrics.market_price

        except Exception as e:
            if 'fetch_coinmarketcap_data' in str(e):
                logging.error(f"Ошибка при запросе данных с CoinMarketCap для {user_coin_name}: {e}")
            elif 'KeyError' in str(e):
                logging.error(f"Ошибка при извлечении данных (отсутствуют ключи) из CoinMarketCap: {e}")
            elif 'AttributeError' in str(e):
                logging.error(f"Ошибка при доступе к атрибутам данных токеномики или метрик: {e}")
            else:
                logging.error(f"Общая ошибка при обработке данных токеномики для монеты {user_coin_name}: {e}")

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
            session=session_local,
            model_mapping=model_mapping
        )

        if tasks.get("social_metrics", []):
            (twitter_subs, twitter_twitterscore) = tasks.get("social_metrics", [])[0]
            twitter = twitter_subs
            twitterscore = twitter_twitterscore
            if twitter and twitterscore:
                await update_or_create(
                    session_local, SocialMetrics,
                    project_id=base_project.id,
                    defaults={
                        'twitter': twitter,
                        'twitterscore': twitterscore
                    }
                )

        if tasks.get("investing_metrics", []):
            fundraise, investors = tasks.get("investing_metrics", [])[0]
            if user_coin_name not in tickers and fundraise and investors:
                await update_or_create(
                    session_local, InvestingMetrics,
                    project_id=base_project.id,
                    defaults={
                        'fundraise': fundraise,
                        'fund_level': investors
                    },
                )
            elif fundraise:
                await update_or_create(
                    session_local, InvestingMetrics,
                    project_id=base_project.id,
                    defaults={
                        'fundraise': fundraise,
                    },
                )

        if tasks.get("network_metrics", []):
            last_tvl = tasks.get("network_metrics", [])[0]
            if last_tvl and price and total_supply:
                await update_or_create(
                    session_local, NetworkMetrics,
                    project_id=base_project.id,
                    defaults={
                        'tvl': last_tvl if last_tvl else 0,
                        'tvl_fdv': last_tvl / (price * total_supply) if last_tvl and total_supply and price else 0
                    },
                )

        if tasks.get("manipulative_metrics", []):
            top_100_wallets = tasks.get("manipulative_metrics", [])[0]
            await update_or_create(
                session_local, ManipulativeMetrics,
                project_id=base_project.id,
                defaults={
                    'fdv_fundraise': (price * total_supply) / fundraise if fundraise else None,
                    'top_100_wallet': top_100_wallets
                }
            )

        project_info = await get_user_project_info(session_local, user_coin_name)
        project = project_info.get("project")
        tokenomics_data = project_info.get("tokenomics_data")
        basic_metrics = project_info.get("basic_metrics")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        top_and_bottom = project_info.get("top_and_bottom")
        market_metrics = project_info.get("market_metrics")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")

        new_project = await process_metrics(session_local, user_coin_name, project, chosen_project, tasks, price, total_supply, fundraise, investors)

        if new_project:
            calculation_record = Calculation(
                user_id=message.from_user.id,
                project_id=new_project.id,
                date=datetime.now()
            )
            session_local.add(calculation_record)

        metrics_data = {
            "circ_supply": tokenomics_data.circ_supply if tokenomics_data else None,
            "total_supply": tokenomics_data.total_supply if tokenomics_data else None,
            "capitalization": tokenomics_data.capitalization if tokenomics_data else None,
            "fdv": tokenomics_data.fdv if tokenomics_data else None,
            "entry_price": basic_metrics.entry_price if basic_metrics else None,
            "market_price": basic_metrics.market_price if basic_metrics else None,
            "sphere": basic_metrics.sphere if basic_metrics else None,
            "fundraise": investing_metrics.fundraise if investing_metrics else None,
            "fund_level": investing_metrics.fund_level if investing_metrics else None,
            "twitter": social_metrics.twitter if social_metrics else None,
            "twitterscore": social_metrics.twitterscore if social_metrics else None,
            "distribution": funds_profit.distribution if funds_profit else None,
            "lower_threshold": top_and_bottom.lower_threshold if top_and_bottom else None,
            "upper_threshold": top_and_bottom.upper_threshold if top_and_bottom else None,
            "fail_high": market_metrics.fail_high if market_metrics else None,
            "growth_low": market_metrics.growth_low if market_metrics else None,
            "top_100_wallet": manipulative_metrics.top_100_wallet if manipulative_metrics else None,
            "tvl": network_metrics.tvl if network_metrics else None
        }
        data = {
            "new_project": new_project,
            "calculation_record": calculation_record.to_dict(),
            "category_answer": category_answer,
            "chosen_project": chosen_project,
            "twitter_name": twitter_name,
            "coin_name": user_coin_name,
            "price": price,
            "total_supply": total_supply
        }

        missing_fields, examples = check_missing_fields(metrics_data, checking_map)
        missing_fields_string = ', '.join(missing_fields)

        await session_local.commit()

        if missing_fields_string:
            response_message = (
                f"Отсутствующие данные для запроса: {missing_fields_string}.\n"
                "Пожалуйста, предоставьте эти данные в следующем формате:\n"
                + '\n'.join(examples)
            )
            await message.answer(response_message)
            await state.update_data(**data)
            await state.set_state(CalculateProject.waiting_for_pdf)
        else:
            await state.update_data(**data)
            await create_pdf(session_local, state, message='-', user_id=message.from_user.id)


@save_execute
async def create_basic_report(session, state: FSMContext, message: Optional[Union[Message, str]] = None, user_id: Optional[int] = None):
    state_data = await state.get_data()
    user_coin_name = state_data.get("user_coin_name")
    category_answer = state_data.get("category_answer")
    results = state_data.get("results")
    new_project = state_data.get("new_project")
    agents_info = state_data.get("agents_info")
    twitter_link = state_data.get("twitter_name")
    calculation_record = state_data.get("calculation_record")
    chosen_project_obj = await find_record(Project, session, coin_name=user_coin_name)
    user_input = message.text if isinstance(message, Message) else message
    input_lines = user_input.split('\n')
    language = 'RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'

    if user_input != '-':
        process_and_update_models(input_lines, field_mapping, model_mapping, session, new_project, chosen_project_obj)

    try:
        project_info = await get_user_project_info(session, user_coin_name)
        project = project_info.get("project")
        basic_metrics = project_info.get("basic_metrics")
        tokenomics_data = project_info.get("tokenomics_data")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        market_metrics = project_info.get("market_metrics")
        top_and_bottom = project_info.get("top_and_bottom")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")

        existing_answer = await find_record(AgentAnswer, session, project_id=project.id, language=('RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'))

        comparison_results = ""
        result_index = 1
        for index, coin_name, project_coin, expected_x, fair_price in agents_info:
            if project_coin != user_coin_name:
                if project.coin_name in tickers:
                    # Добавляем проверки типов перед форматированием строки
                    try:
                        # Проверка и приведение переменной growth к float
                        if isinstance(expected_x, str):
                            growth = float(expected_x)
                        elif not isinstance(expected_x, (float, int)):
                            raise ValueError(f"Unexpected type for growth: {type(expected_x)}")

                        # Проверка fair_price, чтобы убедиться, что это строка или число
                        if not isinstance(fair_price, (str, int, float)):
                            raise ValueError(f"Unexpected type for fair_price: {type(fair_price)}")

                        # Проверяем типы других переменных
                        if not isinstance(index, int):
                            raise ValueError(f"Unexpected type for index: {type(index)}")
                        if not isinstance(user_coin_name, str):
                            raise ValueError(f"Unexpected type for user_coin_name: {type(user_coin_name)}")
                        if not isinstance(project_coin, str):
                            raise ValueError(f"Unexpected type for project_coin: {type(project_coin)}")

                        # Форматируем строку
                        comparison_results += calculations_choices[language].format(
                            index=index,
                            user_coin_name=user_coin_name,
                            project_coin_name=project_coin,
                            growth=expected_x,
                            fair_price=fair_price
                        )
                        result_index += 1

                    except ValueError as e:
                        # Логируем и выводим ошибку
                        print(f"Error: {e}")
                        print(f"index: {index}, type: {type(index)}")
                        print(f"user_coin_name: {user_coin_name}, type: {type(user_coin_name)}")
                        print(f"project_coin: {project_coin}, type: {type(project_coin)}")
                        print(f"growth: {expected_x}, type: {type(expected_x)}")
                        print(f"fair_price: {fair_price}, type: {type(fair_price)}")
                        raise

        if existing_answer is None:
            tier_answer = determine_project_tier(
                capitalization=tokenomics_data.capitalization if tokenomics_data else 'N/A',
                fundraising=investing_metrics.fundraise if investing_metrics else 'N/A',
                twitter_followers=social_metrics.twitter if social_metrics else 'N/A',
                twitter_score=social_metrics.twitterscore if social_metrics else 'N/A',
                category=project.category if project else 'N/A',
                investors=investing_metrics.fund_level if investing_metrics else 'N/A',
            )

            data_for_tokenomics = []
            for index, coin_name, project_coin, expected_x, fair_price in agents_info:
                ticker = project_coin
                growth_percent = expected_x
                data_for_tokenomics.append({ticker: {"growth_percent": growth_percent}})
            tokemonic_answer, tokemonic_score = calculate_tokenomics_score(project.coin_name, data_for_tokenomics)

            all_data_string_for_funds_agent = (
                f"Распределение токенов: {funds_profit.distribution if funds_profit else 'N/A'}\n"
            )
            funds_agent_answer = agent_handler("funds_agent", topic=all_data_string_for_funds_agent)

            funds_answer, funds_scores = analyze_project_metrics(
                funds_agent_answer,
                investing_metrics.fundraise if investing_metrics and investing_metrics.fundraise else 'N/A',
                tokenomics_data.total_supply if tokenomics_data and tokenomics_data.total_supply else 'N/A',
                basic_metrics.market_price if basic_metrics and basic_metrics.market_price else 'N/A',
                round((market_metrics.growth_low - 100) * 100, 2) if market_metrics else 'N/A',
                round(market_metrics.fail_high * 100, 2) if market_metrics else 'N/A',
                manipulative_metrics.top_100_wallet * 100 if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A',
                (
                            network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'
            )

            project_rating_result = calculate_project_score(
                investing_metrics.fundraise if investing_metrics else 'N/A',
                tier_answer,
                social_metrics.twitter if social_metrics else 'N/A',
                social_metrics.twitterscore if social_metrics else 'N/A',
                tokemonic_score if tokemonic_answer else 'N/A',
                funds_scores if funds_answer else 'N/A'
            )

            project_rating_answer = project_rating_result["calculations_summary"]

            all_data_string_for_flags_agent = (
                f"Проект: {project.category}\n"
                f"Category agent answer: {category_answer}\n",
                f"Tier agent: {tier_answer}\n",
                f"Tokemonic agent: {tokemonic_answer}\n",
                f"Funds agent: {funds_answer}\n",
                f"Project rating agent: {project_rating_answer}\n"
                f"Социальные метрики: Количество подписчиков - {social_metrics.twitter} (twitter link: {twitter_link}), Twitter Score - {social_metrics.twitterscore}"
            )

            flags_answer = await generate_flags_answer(message.from_user.id if isinstance(message, Message) else user_id, async_session, all_data_string_for_flags_agent, user_languages, project, tokenomics_data, investing_metrics, social_metrics,
                                        funds_profit, market_metrics, manipulative_metrics, network_metrics,
                                        funds_answer, tokemonic_answer, comparison_results, category_answer, twitter_link, top_and_bottom, tier_answer)

            agent_answer_record = AgentAnswer(
                project_id=project.id,
                answer=flags_answer,
                language='RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'
            )
            session.add(agent_answer_record)

        else:
            flags_answer = existing_answer.answer

        existing_calculation = await find_record(Calculation, session, id=calculation_record["id"])
        existing_calculation.agent_answer = flags_answer
        session.add(existing_calculation)

        answer = comparison_results + "\n"
        answer += flags_answer
        answer = answer.replace('**', '')

        if isinstance(message, Message):
            await send_long_message(bot_or_message=message, text=f"{answer}\n")
            await message.answer(phrase_by_user("input_next_token_for_basic_report", message.from_user.id), reply_markup=ReplyKeyboardRemove())
        else:
            async with AiohttpSession() as session:
                bot = Bot(token=API_TOKEN, session=session)
                await send_long_message(bot_or_message=bot, text=f"{answer}\n", chat_id=user_id)
                await bot.send_message(chat_id=user_id, text=phrase_by_user("input_next_token_for_basic_report", user_id), reply_markup=ReplyKeyboardRemove())

    except ValueError:
        error_message = traceback.format_exc()
        # return phrase_by_user("error_not_valid_input_data", message.from_user.id if isinstance(message, Message) else user_id), error_message

        if isinstance(message, Message):
            await message.answer(f"{phrase_by_user('error_not_valid_input_data', message.from_user.id)}\n{error_message}")
        elif user_id is not None:
            await bot.send_message(chat_id=user_id, text=f"{phrase_by_user('error_not_valid_input_data', message.from_user.id)}\n{error_message}")


@save_execute
async def create_excel(session, state: FSMContext, message: Optional[Union[Message, str]] = None, user_id: Optional[int] = None):
    state_data = await state.get_data()
    chosen_project = state_data.get("chosen_project")
    category_answer = state_data.get("category_answer")
    new_project = state_data.get("new_project")
    coin_name = state_data.get("coin_name")
    price = state_data.get("price")
    twitter_link = state_data.get("twitter_name")
    total_supply = state_data.get("total_supply")
    calculation_record = state_data.get("calculation_record")
    chosen_project_obj = await find_record(Project, session, coin_name=coin_name)
    user_input = message.text if isinstance(message, Message) else message
    input_lines = user_input.split('\n')
    language = 'RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'

    if user_input != '-':
        process_and_update_models(input_lines, field_mapping, model_mapping, session, new_project, chosen_project_obj)

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
    data_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})

    worksheet.set_column(0, 0, 17, data_format)
    worksheet.set_column(1, 1, 17, data_format)
    worksheet.set_column(2, 2, 27, data_format)
    worksheet.set_column(3, 3, 20, data_format)
    worksheet.set_column(4, 4, 20, data_format)
    worksheet.set_column(5, 5, 25, data_format)
    worksheet.set_column(6, 6, 18, data_format)
    worksheet.set_column(7, 7, 20, data_format)
    worksheet.set_column(8, 8, 19, data_format)
    worksheet.set_column(9, 9, 25, data_format)
    worksheet.set_column(10, 10, 20, data_format)
    worksheet.set_column(11, 11, 15, data_format)
    worksheet.set_column(12, 12, 15, data_format)
    worksheet.set_column(13, 13, 15, data_format)
    worksheet.set_column(14, 14, 15, data_format)
    worksheet.set_column(15, 15, 15, data_format)
    worksheet.set_column(16, 16, 15, data_format)
    worksheet.set_column(17, 17, 17, data_format)
    worksheet.set_column(18, 18, 17, data_format)
    worksheet.set_column(19, 19, 15, data_format)
    worksheet.set_column(20, 20, 15, data_format)
    worksheet.set_column(21, 21, 15, data_format)
    worksheet.set_column(22, 22, 15, data_format)

    if isinstance(message, Message):
        headers = calculation_header_by_user(message.from_user.id)
    else:
        headers = calculation_header_by_user(user_id)

    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header, header_format)

    try:
        projects, tokenomics_data_list = await get_project_and_tokenomics(session, chosen_project, coin_name)
        row_data = []

        if "error" in projects:
            raise ValueError(projects["error"])

        result_index = 1
        for index, (project, tokenomics_data) in enumerate(tokenomics_data_list, start=1):
            for tokenomics in tokenomics_data:
                if coin_name != project.coin_name:
                    fdv = tokenomics.fdv if tokenomics.fdv is not None else 0

                    calculation_result = calculate_expected_x(
                        entry_price=price,
                        total_supply=total_supply,
                        fdv=fdv,
                    )

                    if "error" in calculation_result:
                        raise ValueError(calculation_result["error"])

                    fair_price = f"{calculation_result['fair_price']:.5f}" if isinstance(calculation_result['fair_price'], (int, float)) else "Ошибка в расчетах"
                    expected_x = f"{calculation_result['expected_x']:.5f}"

                    row_data.append([
                        result_index,
                        coin_name,
                        project.coin_name,
                        round((float(expected_x) - 1.0) * 100, 2),
                        fair_price
                    ])
                    result_index += 1

        for row_num, row in enumerate(row_data, start=1):
            for col_num, value in enumerate(row):
                worksheet.write(row_num, col_num, value, data_format)

        last_coin_name = None
        last_entry_price = None
        last_market_cap = None

        start_row_coin_name = 1
        start_row_entry_price = 1
        start_row_market_cap = 1

        fund_distribution_list = []
        fund_distribution_dict = {}

        for row_num in range(1, len(row_data) + 1):
            current_coin_name = row_data[row_num - 1][1]
            if last_coin_name is None:
                last_coin_name = current_coin_name
                start_row_coin_name = row_num
            elif current_coin_name == last_coin_name:
                continue
            else:
                if start_row_coin_name < row_num - 1:
                    worksheet.merge_range(start_row_coin_name, 1, row_num - 1, 1, last_coin_name, data_format)
                last_coin_name = current_coin_name
                start_row_coin_name = row_num

            current_entry_price = row_data[row_num - 1][3]
            if last_entry_price is None:
                last_entry_price = current_entry_price
                start_row_entry_price = row_num
            elif current_entry_price == last_entry_price:
                continue
            else:
                if start_row_entry_price < row_num - 1:
                    worksheet.merge_range(start_row_entry_price, 3, row_num - 1, 3, last_entry_price, data_format)
                last_entry_price = current_entry_price
                start_row_entry_price = row_num

            current_market_cap = row_data[row_num - 1][4]
            if last_market_cap is None:
                last_market_cap = current_market_cap
                start_row_market_cap = row_num
            elif current_market_cap == last_market_cap:
                continue
            else:
                if start_row_market_cap < row_num - 1:
                    worksheet.merge_range(start_row_market_cap, 4, row_num - 1, 4, last_market_cap, data_format)
                last_market_cap = current_market_cap
                start_row_market_cap = row_num

        if start_row_coin_name < len(row_data) + 1:
            worksheet.merge_range(start_row_coin_name, 1, len(row_data), 1, last_coin_name, data_format)
        if start_row_entry_price < len(row_data) + 1:
            worksheet.merge_range(start_row_entry_price, 3, len(row_data), 3, last_entry_price, data_format)

        for row_num, row in enumerate(row_data, start=1):
            for col_num, value in enumerate(row):
                worksheet.write(row_num, col_num, value, data_format)

        empty_row = len(row_data) + 3
        funds_diagrams = empty_row
        worksheet.write(empty_row, 0, '', data_format)

        default_data = []
        additional_headers = ru_additional_headers if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else eng_additional_headers

        for col_num, header in enumerate(additional_headers):
            worksheet.write(empty_row + 1, col_num, header, header_format)

        (
         projects,
         tokenomics_data_list,
         basic_metrics_data_list,
         invested_metrics_data_list,
         social_metrics_data_list,
         funds_profit_data_list,
         top_and_bottom_data_list,
         market_metrics_data_list,
         manipulative_metrics_data_list,
         network_metrics_data_list
        ) = await get_full_info(session, chosen_project, coin_name)

        project_info = await get_user_project_info(session, coin_name)
        project = project_info.get("project")
        basic_metrics = project_info.get("basic_metrics")
        tokenomics_data = project_info.get("tokenomics_data")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        market_metrics = project_info.get("market_metrics")
        top_and_bottom = project_info.get("top_and_bottom")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")

        existing_answer = await find_record(AgentAnswer, session_local, project_id=project.id, language=('RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'))
        # existing_answer = session.query(AgentAnswer).filter(AgentAnswer.project_id == project.id, AgentAnswer.language == ('RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG')).first()

        comparison_results = ""
        result_index = 1
        for index, coin_name, project_coin, expected_x, fair_price in row_data:
            if project_coin != coin_name:
                if project.coin_name in tickers:
                    try:
                        if isinstance(expected_x, str):
                            growth = float(expected_x)
                        elif not isinstance(expected_x, (float, int)):
                            raise ValueError(f"Unexpected type for expected_x: {type(expected_x)}")

                        # Проверка fair_price, чтобы убедиться, что это строка или число
                        if not isinstance(fair_price, (str, int, float)):
                            raise ValueError(f"Unexpected type for fair_price: {type(fair_price)}")

                        # Проверяем типы других переменных
                        if not isinstance(index, int):
                            raise ValueError(f"Unexpected type for index: {type(index)}")
                        if not isinstance(coin_name, str):
                            raise ValueError(f"Unexpected type for user_coin_name: {type(coin_name)}")
                        if not isinstance(project_coin, str):
                            raise ValueError(f"Unexpected type for project_coin: {type(project_coin)}")

                        # Форматируем строку
                        comparison_results += calculations_choices[language].format(
                            index=index,
                            user_coin_name=coin_name,
                            project_coin_name=project_coin,
                            growth=expected_x,
                            fair_price=fair_price
                        )
                        result_index += 1

                    except ValueError as e:
                        # Логируем и выводим ошибку
                        print(f"Error: {e}")
                        print(f"index: {index}, type: {type(index)}")
                        print(f"user_coin_name: {coin_name}, type: {type(coin_name)}")
                        print(f"project_coin: {project_coin}, type: {type(project_coin)}")
                        print(f"growth: {expected_x}, type: {type(expected_x)}")
                        print(f"fair_price: {fair_price}, type: {type(fair_price)}")
                        raise

        if existing_answer is None:
            tier_answer = determine_project_tier(
                capitalization=tokenomics_data.capitalization if tokenomics_data else 'N/A',
                fundraising=investing_metrics.fundraise if investing_metrics else 'N/A',
                twitter_followers=social_metrics.twitter if social_metrics else 'N/A',
                twitter_score=social_metrics.twitterscore if social_metrics else 'N/A',
                category=project.category if project else 'N/A',
                investors=investing_metrics.fund_level if investing_metrics else 'N/A',
            )

            data_for_tokenomics = []
            for index, coin_name, project_coin, expected_x, fair_price in row_data:
                ticker = project_coin
                growth_percent = expected_x
                data_for_tokenomics.append({ticker: {"growth_percent": growth_percent}})
            tokemonic_answer, tokemonic_score = calculate_tokenomics_score(project.coin_name, data_for_tokenomics)

            all_data_string_for_funds_agent = (
                f"Распределение токенов: {funds_profit.distribution if funds_profit else 'N/A'}\n"
            )
            funds_agent_answer = agent_handler("funds_agent", topic=all_data_string_for_funds_agent)

            funds_answer, funds_scores = analyze_project_metrics(
                funds_agent_answer,
                investing_metrics.fundraise if investing_metrics and investing_metrics.fundraise else 'N/A',
                tokenomics_data.total_supply if tokenomics_data and tokenomics_data.total_supply else 'N/A',
                basic_metrics.market_price if basic_metrics and basic_metrics.market_price else 'N/A',
                round((market_metrics.growth_low - 100) * 100, 2) if market_metrics else 'N/A',
                round(market_metrics.fail_high * 100, 2) if market_metrics else 'N/A',
                manipulative_metrics.top_100_wallet * 100 if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A',
                (
                            network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'
            )

            project_rating_result = calculate_project_score(
                investing_metrics.fundraise if investing_metrics else 'N/A',
                tier_answer,
                social_metrics.twitter if social_metrics else 'N/A',
                social_metrics.twitterscore if social_metrics else 'N/A',
                tokemonic_score if tokemonic_answer else 'N/A',
                funds_scores if funds_answer else 'N/A'
            )

            project_rating_answer = project_rating_result["calculations_summary"]

            all_data_string_for_flags_agent = (
                f"Проект: {project.category}\n"
                f"Category agent answer: {category_answer}\n",
                f"Tier agent: {tier_answer}\n",
                f"Tokemonic agent: {tokemonic_answer}\n",
                f"Funds agent: {funds_answer}\n",
                f"Project rating agent: {project_rating_answer}\n"
                f"Социальные метрики: Количество подписчиков - {social_metrics.twitter} (twitter link: {twitter_link}), Twitter Score - {social_metrics.twitterscore}"
            )
            flags_answer = await generate_flags_answer(message.from_user.id if isinstance(message, Message) else user_id, session, all_data_string_for_flags_agent, user_languages, project, tokenomics_data, investing_metrics, social_metrics,
                                        funds_profit, market_metrics, manipulative_metrics, network_metrics, tier_answer,
                                        funds_answer, tokemonic_answer, comparison_results, category_answer, twitter_link, top_and_bottom)

            agent_answer_record = AgentAnswer(
                project_id=project.id,
                answer=flags_answer,
                language='RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'
            )
            session.add(agent_answer_record)
        else:
            flags_answer = existing_answer.answer

        answer = comparison_results + "\n"
        answer += flags_answer
        answer = answer.replace('**', '')

        existing_calculation = await find_record(Calculation, session, id=calculation_record["id"])
        existing_calculation.agent_answer = flags_answer
        session.add(existing_calculation)

        for index, (project, tokenomics_data) in enumerate(tokenomics_data_list, start=1):
            for tokenomics in tokenomics_data:
                basic_metrics = next((bm for bm in basic_metrics_data_list if bm[0] == project), None)
                investing_metrics = next((im for im in invested_metrics_data_list if im[0] == project), None)
                social_metrics = next((sm for sm in social_metrics_data_list if sm[0] == project), None)
                funds_profit = next((fp for fp in funds_profit_data_list if fp[0] == project), None)
                market_metrics = next((mm for mm in market_metrics_data_list if mm[0] == project), None)
                manipulative_metrics = next((man for man in manipulative_metrics_data_list if man[0] == project), None)
                network_metrics = next((nm for nm in network_metrics_data_list if nm[0] == project), None)
                top_and_bottom = next((km for km in top_and_bottom_data_list if km[0] == project), None)

                default_data.append(create_project_data_row(
                    project,
                    tokenomics,
                    basic_metrics,
                    investing_metrics,
                    social_metrics,
                    market_metrics,
                    manipulative_metrics,
                    network_metrics,
                    top_and_bottom
                ))
                fund_distribution_list.append((project.coin_name, str(funds_profit[1][0].distribution) if funds_profit and funds_profit[1] else "-"))

        for row_num, row in enumerate(default_data, start=empty_row + 2):
            for col_num, value in enumerate(row):
                worksheet.write(row_num, col_num, value, data_format)
            funds_diagrams += 1

        for item in fund_distribution_list:
            coin_name = item[0]
            distribution_str = item[1]

            if coin_name not in fund_distribution_dict:
                fund_distribution_dict[coin_name] = []

            fund_distribution_dict[coin_name].append(distribution_str)

        start_row = funds_diagrams + 5
        spacing = 2
        max_charts_in_row = 3
        chart_width = 3
        chart_height = 15
        current_chart_index = 0
        data_row_start = 60

        x_scale = 0.9
        y_scale = 1.2

        for coin_name, distributions in fund_distribution_dict.items():
            chart_data = {
                "labels": [],
                "values": []
            }

            for distribution in distributions:
                parts = distribution.split(')')
                if parts:
                    for part in parts:
                        if part:
                            tokemonics_parts = part.split('(')
                            if len(tokemonics_parts) > 1:
                                label = tokemonics_parts[0].strip()
                                value_str = tokemonics_parts[1].replace('%', '').strip()

                                try:
                                    value = float(value_str)
                                    chart_data["labels"].append(label)
                                    chart_data["values"].append(value)
                                except ValueError:
                                    logging.error(f"Ошибка преобразования значения '{value_str}' в float.")
                                    logging.warning(f"Пропущено значение: '{value_str}' из-за недопустимого формата.")

            if chart_data["values"]:
                chart = workbook.add_chart({'type': 'pie'})
                data_start_row = data_row_start
                data_end_row = data_row_start + len(chart_data["values"]) - 1

                for i, value in enumerate(chart_data["values"]):
                    worksheet.write(data_row_start + i, 1, value)
                    worksheet.write(data_row_start + i, 0, chart_data["labels"][i])

                percentage_labels = [f"{label} ({value}%)" for label, value in zip(chart_data["labels"], chart_data["values"])]

                for i, label in enumerate(percentage_labels):
                    worksheet.write(data_row_start + i, 0, label)

                chart.add_series({
                    'name': f'Allocation {coin_name}',
                    'categories': f'={worksheet.get_name()}!$A${data_start_row + 1}:$A${data_end_row + 1}',
                    'values': f'={worksheet.get_name()}!$B${data_start_row + 1}:$B${data_end_row + 1}',
                    'data_labels': {'value': False},
                    'points': [{'fill': {'color': color_palette[i % len(color_palette)]}} for i in range(len(chart_data["values"]))],
                })

                chart.set_legend({
                    'position': 'right',
                    'layout': {'overlay': True},
                    'font': {'size': 8},
                    'margin': {'top': 0, 'right': 0, 'bottom': 0, 'left': 0},
                })

                chart.set_title({
                    'name': f'Distribution of Funds for {coin_name}',
                    'name_font': {'size': 13}
                })
                chart.set_style(10)

                row_position = start_row + (current_chart_index // max_charts_in_row) * (chart_height + spacing)
                col_position = (current_chart_index % max_charts_in_row) * chart_width

                worksheet.insert_chart(row_position, col_position, chart, {'x_scale': x_scale, 'y_scale': y_scale})
                current_chart_index += 1
                data_row_start = data_end_row + spacing

            else:
                logging.info(f"No data to create chart for {coin_name}.")

        workbook.close()
        output.seek(0)

        await session.commit()

        if isinstance(message, Message):
            # Отправляем файл с расчетами
            await message.answer_document(BufferedInputFile(output.read(), filename="results.xlsx"))
            await state.set_state(None)
            await state.set_state(CalculateProject.waiting_for_data)

            # Отправляем сообщение с рейтингом проекта
            await send_long_message(message, f"{phrase_by_user('overal_project_rating', user_id)} \n{answer}\n")
            await message.send_message(chat_id=user_id, text=phrase_by_user("input_next_token_for_analysis", user_id), reply_markup=ReplyKeyboardRemove())

            # Очищаем состояние и устанавливаем новое состояние на ожидание ввода нового токена
            await state.set_state(None)
            await state.set_state(CalculateProject.waiting_for_data)
        elif user_id is not None:
            async with AiohttpSession() as session:
                bot = Bot(token=API_TOKEN, session=session)

                # Отправляем файл с расчетами
                await bot.send_document(chat_id=user_id, document=BufferedInputFile(output.read(), filename="results.xlsx"))

                # Отправляем сообщение с рейтингом проекта
                await send_long_message(bot, f"{phrase_by_user('overal_project_rating', user_id)} \n{answer}\n", chat_id=user_id)
                await bot.send_message(chat_id=user_id, text=phrase_by_user("input_next_token_for_analysis", user_id), reply_markup=ReplyKeyboardRemove())

                # Очищаем состояние и устанавливаем новое состояние на ожидание ввода нового токена
                await state.set_state(None)
                await state.set_state(CalculateProject.waiting_for_data)
        else:
            logging.error("Не указан ни объект Message, ни user_id для отправки документа.")

    except ValueError:
        error_message = traceback.format_exc()
        if isinstance(message, Message):
            await message.answer(f"{phrase_by_user('error_not_valid_input_data', message.from_user.id)}\n{error_message}")
        elif user_id is not None:
            await bot.send_message(chat_id=user_id, text=f"{phrase_by_user('error_not_valid_input_data', message.from_user.id)}\n{error_message}")


@save_execute
async def create_pdf(session, state: FSMContext, message: Optional[Union[Message, str]] = None, user_id: Optional[int] = None):
    state_data = await state.get_data()
    logging.info(f"state data {state_data}")
    chosen_project = state_data.get("chosen_project")
    category_answer = state_data.get("category_answer")
    new_project = state_data.get("new_project")
    coin_name = state_data.get("coin_name")
    twitter_link = state_data.get("twitter_name")
    price = state_data.get("price")
    total_supply = state_data.get("total_supply")
    calculation_record = state_data.get("calculation_record")
    chosen_project_obj = await find_record(Project, session, coin_name=coin_name)
    user_input = message.text if isinstance(message, Message) else message
    row_data = []
    cells_content = None
    language = 'RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'

    input_lines = user_input.split('\n')
    if user_input != '-':
        process_and_update_models(input_lines, field_mapping, model_mapping, session, new_project, chosen_project_obj)

    if isinstance(message, Message):
        headers = calculation_header_by_user(message.from_user.id)
    else:
        headers = calculation_header_by_user(user_id)

    try:
        result = await get_project_and_tokenomics(session, chosen_project, get_project_and_tokenomics)

        if isinstance(result, tuple) and len(result) == 2:
            projects, tokenomics_data_list = result
        else:
            raise ValueError("Функция get_project_and_tokenomics вернула неожиданный результат.")

        if "error" in projects:
            raise ValueError(projects["error"])

        for index, (project, tokenomics_data) in enumerate(tokenomics_data_list, start=1):
            for tokenomics in tokenomics_data:
                fdv = tokenomics.fdv if tokenomics.fdv is not None else 0
                calculation_result = calculate_expected_x(
                    entry_price=price,
                    total_supply=total_supply,
                    fdv=fdv,
                )

                if "error" in calculation_result:
                    raise ValueError(calculation_result["error"])

                fair_price = f"{calculation_result['fair_price']:.5f}" if isinstance(calculation_result['fair_price'], (int, float)) else "Ошибка в расчетах"
                expected_x = f"{calculation_result['expected_x']:.5f}"

                row_data.append([
                    index,
                    coin_name,
                    project.coin_name,
                    round((float(expected_x) - 1.0) * 100, 2),
                    fair_price
                ])

        pdf = PDF(logo_path=logo_path, orientation='L')
        pdf.add_page()
        pdf.add_font("DejaVu", '', dejavu_path, uni=True)
        pdf.set_font("DejaVu", size=8)

        for header in headers:
            if header == 'Вариант' or header == 'Option':
                pdf.cell(30, 10, header, 1)
            else:
                pdf.cell(45, 10, header, 1)
        pdf.ln()

        for row in row_data:
            for col_num, value in enumerate(row):
                if headers[col_num] == 'Вариант' or headers[col_num] == 'Option':
                    pdf.cell(30, 10, str(value), 1)
                else:
                    pdf.cell(45, 10, str(value), 1)
            pdf.ln()
        pdf.ln()

        (
            projects,
            tokenomics_data_list,
            basic_metrics_data_list,
            invested_metrics_data_list,
            social_metrics_data_list,
            funds_profit_data_list,
            top_and_bottom_data_list,
            market_metrics_data_list,
            manipulative_metrics_data_list,
            network_metrics_data_list
        ) = await get_full_info(session, chosen_project, coin_name)

        project_info = await get_user_project_info(session, new_project.coin_name)
        project = project_info.get("project")
        basic_metrics = project_info.get("basic_metrics")
        tokenomics_data = project_info.get("tokenomics_data")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        market_metrics = project_info.get("market_metrics")
        manipulative_metrics = project_info.get("manipulative_metrics")
        top_and_bottom = project_info.get("top_and_bottom")
        network_metrics = project_info.get("network_metrics")

        print(new_project.coin_name, project.coin_name, manipulative_metrics.top_100_wallet)

        existing_answer = await find_record(AgentAnswer, session, project_id=project.id, language=('RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'))

        comparison_results = ""
        result_index = 1
        for index, coin_name, project_coin, expected_x, fair_price in row_data:
            if project_coin != coin_name:
                if project.coin_name in tickers:
                    try:
                        if isinstance(expected_x, str):
                            growth = float(expected_x)
                        elif not isinstance(expected_x, (float, int)):
                            raise ValueError(f"Unexpected type for growth: {type(expected_x)}")

                        # Проверка fair_price, чтобы убедиться, что это строка или число
                        if not isinstance(fair_price, (str, int, float)):
                            raise ValueError(f"Unexpected type for fair_price: {type(fair_price)}")

                        # Проверяем типы других переменных
                        if not isinstance(index, int):
                            raise ValueError(f"Unexpected type for index: {type(index)}")
                        if not isinstance(coin_name, str):
                            raise ValueError(f"Unexpected type for user_coin_name: {type(coin_name)}")
                        if not isinstance(project_coin, str):
                            raise ValueError(f"Unexpected type for project_coin_name: {type(project_coin)}")

                        # Форматируем строку
                        comparison_results += calculations_choices[language].format(
                            index=index,
                            user_coin_name=coin_name,
                            project_coin_name=project_coin,
                            growth=expected_x,
                            fair_price=fair_price
                        )
                        result_index += 1

                    except ValueError as e:
                        # Логируем и выводим ошибку
                        print(f"Error: {e}")
                        print(f"index: {index}, type: {type(index)}")
                        print(f"coin_name: {coin_name}, type: {type(coin_name)}")
                        print(f"project_coin_name: {project_coin}, type: {type(project_coin)}")
                        print(f"growth: {expected_x}, type: {type(expected_x)}")
                        print(f"fair_price: {fair_price}, type: {type(fair_price)}")
                        raise

        if existing_answer is None:
            tier_answer = determine_project_tier(
                capitalization=tokenomics_data.capitalization if tokenomics_data else 'N/A',
                fundraising=investing_metrics.fundraise if investing_metrics else 'N/A',
                twitter_followers=social_metrics.twitter if social_metrics else 'N/A',
                twitter_score=social_metrics.twitterscore if social_metrics else 'N/A',
                category=project.category if project else 'N/A',
                investors=investing_metrics.fund_level if investing_metrics else 'N/A',
            )

            data_for_tokenomics = []
            for index, coin_name, project_coin, expected_x, fair_price in row_data:
                ticker = project_coin
                growth_percent = expected_x
                data_for_tokenomics.append({ticker: {"growth_percent": growth_percent}})
            tokemonic_answer, tokemonic_score = calculate_tokenomics_score(project.coin_name, data_for_tokenomics)

            all_data_string_for_funds_agent = (
                f"Распределение токенов: {funds_profit.distribution if funds_profit else 'N/A'}\n"
            )
            funds_agent_answer = agent_handler("funds_agent", topic=all_data_string_for_funds_agent)

            funds_answer, funds_scores = analyze_project_metrics(
                funds_agent_answer,
                investing_metrics.fundraise if investing_metrics and investing_metrics.fundraise else 'N/A',
                tokenomics_data.total_supply if tokenomics_data and tokenomics_data.total_supply else 'N/A',
                basic_metrics.market_price if basic_metrics and basic_metrics.market_price else 'N/A',
                round((market_metrics.growth_low - 100) * 100, 2) if market_metrics else 'N/A',
                round(market_metrics.fail_high * 100, 2) if market_metrics else 'N/A',
                manipulative_metrics.top_100_wallet * 100 if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A',
                (network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'
            )

            project_rating_result = calculate_project_score(
                investing_metrics.fundraise if investing_metrics else 'N/A',
                tier_answer,
                social_metrics.twitter if social_metrics else 'N/A',
                social_metrics.twitterscore if social_metrics else 'N/A',
                tokemonic_score if tokemonic_answer else 'N/A',
                funds_scores if funds_answer else 'N/A'
            )

            project_rating_answer = project_rating_result["calculations_summary"]

            all_data_string_for_flags_agent = (
                f"Проект: {project.category}\n"
                f"Category agent answer: {category_answer}\n",
                f"Tier agent: {tier_answer}\n",
                f"Tokemonic agent: {tokemonic_answer}\n",
                f"Funds agent: {funds_answer}\n",
                f"Project rating agent: {project_rating_answer}\n"
                f"Социальные метрики: Количество подписчиков - {social_metrics.twitter} (twitter link: {twitter_link}), Twitter Score - {social_metrics.twitterscore}"
            )
            flags_answer = await generate_flags_answer(message.from_user.id if isinstance(message, Message) else user_id,
                                        session, all_data_string_for_flags_agent, user_languages, project, tokenomics_data,
                                        investing_metrics, social_metrics, funds_profit, market_metrics, manipulative_metrics,
                                        network_metrics, tier_answer, funds_answer, tokemonic_answer, comparison_results,
                                        category_answer, twitter_link, top_and_bottom)
            agent_answer_record = AgentAnswer(
                project_id=project.id,
                answer=flags_answer,
                language='RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'
            )
            session.add(agent_answer_record)

        else:
            flags_answer = existing_answer.answer

        existing_calculation = await find_record(Calculation, session, id=calculation_record.id)
        existing_calculation.agent_answer = flags_answer
        session.add(existing_calculation)

        answer = comparison_results + "\n"
        answer += flags_answer
        answer = answer.replace('**', '')

        investor_data_list = []
        headers_mapping = results_header_by_user(user_id)
        for header_set in headers_mapping:
            for header in header_set:
                if header == 'Тир фондов' or header == 'Fund Tier':
                    pdf.cell(230, 10, header, 1)
                elif header == 'Сфера' or header == 'Sphere':
                    pdf.cell(50, 10, header, 1)
                elif header == 'FDV':
                    pdf.cell(70, 10, header, 1)
                else:
                    pdf.cell(40, 10, header, 1)
            pdf.ln()

            for index, (project, tokenomics_data) in enumerate(tokenomics_data_list, start=1):
                for tokenomics in tokenomics_data:
                    funds_profit = next((fp for fp in funds_profit_data_list if fp[0] == project), None)
                    cells_content = generate_cells_content(
                        basic_metrics_data_list,
                        invested_metrics_data_list,
                        social_metrics_data_list,
                        market_metrics_data_list,
                        manipulative_metrics_data_list,
                        network_metrics_data_list,
                        top_and_bottom_data_list,
                        project,
                        header_set,
                        headers_mapping,
                        tokenomics,
                        cells_content
                    )

                    if len(cells_content) != len(header_set):
                        print(f"Ошибка: количество значений {len(cells_content)} не соответствует заголовкам {len(header_set)}.")
                        continue

                    cell_widths = []
                    for i, content in enumerate(cells_content):
                        if i < len(header_set) and (header_set[i] == 'Тир фондов' or header_set[i] == 'Fund Tier'):
                            cell_widths.append(230)
                        elif i < len(header_set) and (header_set[i] == 'Сфера' or header_set[i] == 'Sphere'):
                            cell_widths.append(50)
                        elif i < len(header_set) and header_set[i] == 'FDV':
                            cell_widths.append(70)
                        else:
                            cell_widths.append(40)

                    max_lines = 1
                    for i, content in enumerate(cells_content):
                        content_width = pdf.get_string_width(content)
                        lines = (content_width // cell_widths[i]) + 1
                        if lines > max_lines:
                            max_lines = lines

                    cell_height = max_lines * 10
                    for i, content in enumerate(cells_content):
                        if pdf.get_string_width(content) > cell_widths[i]:
                            pdf.multi_cell(cell_widths[i], 10, content, 1)
                            current_y = pdf.get_y()
                            pdf.set_xy(pdf.get_x(), current_y - 10)
                        else:
                            pdf.cell(cell_widths[i], cell_height, content, 1)
                pdf.ln()

                if funds_profit and funds_profit[1] and funds_profit[1][0].distribution and (project.coin_name, funds_profit[1][0].distribution) not in investor_data_list:
                    investor_data_list.append((project.coin_name, funds_profit[1][0].distribution))

            pdf.ln()

        pdf.add_page()
        page_width = pdf.w
        diagram_per_page = 4
        diagrams_on_page = 0
        chart_width = 110
        x_pos_left = (page_width / 4) - (chart_width / 2)
        x_pos_right = (3 * page_width / 4) - (chart_width / 2)

        for i, (coin_name, distribution_data) in enumerate(investor_data_list):
            if diagrams_on_page == diagram_per_page:
                pdf.add_page()
                diagrams_on_page = 0

            y_pos = 30 + (diagrams_on_page // 2) * 90

            if i % 2 == 0:
                x_pos = x_pos_left
            else:
                x_pos = x_pos_right

            pdf.set_font("DejaVu", size=12)
            pdf.set_xy(x_pos, y_pos - 10)
            pdf.cell(90, 10, f"Распределение токенов для {coin_name}", 0, 1, 'C')

            pie_chart_img = generate_pie_chart(distribution_data)
            pdf.image(pie_chart_img, x=x_pos, y=y_pos, w=chart_width, h=85)

            diagrams_on_page += 1

        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        await session.commit()

        if isinstance(message, Message):
            # Отправляем файл с расчетами
            await message.answer_document(BufferedInputFile(pdf_output.read(), filename="results.pdf"))

            # Отправляем сообщение с рейтингом проекта
            await send_long_message(message, f"{phrase_by_user('overal_project_rating', user_id)} \n{answer}\n")
            await message.send_message(chat_id=user_id, text=phrase_by_user("input_next_token_for_analysis", user_id), reply_markup=ReplyKeyboardRemove())

            # Очищаем состояние и устанавливаем новое состояние на ожидание ввода нового токена
            await state.set_state(None)
            await state.set_state(CalculateProject.waiting_for_data)

        elif user_id is not None:
            async with AiohttpSession() as session:
                bot = Bot(token=API_TOKEN, session=session)

                # Отправляем файл с расчетами
                await bot.send_document(chat_id=user_id, document=BufferedInputFile(pdf_output.read(), filename="results.pdf"))

                # Отправляем сообщение с рейтингом проекта
                await send_long_message(bot, f"{phrase_by_user('overal_project_rating', user_id)} \n{answer}\n", chat_id=user_id)
                await bot.send_message(chat_id=user_id, text=phrase_by_user("input_next_token_for_analysis", user_id), reply_markup=ReplyKeyboardRemove())

                # Очищаем состояние и устанавливаем новое состояние на ожидание ввода нового токена
                await state.set_state(None)
                await state.set_state(CalculateProject.waiting_for_data)

        else:
            logging.error("Не указан ни объект Message, ни user_id для отправки документа.")

    except ValueError:
        async with AiohttpSession() as session:
            bot = Bot(token=API_TOKEN, session=session)
            error_message = traceback.format_exc()
            if isinstance(message, Message):
                await message.answer(f"{phrase_by_user('error_not_valid_input_data', message.from_user.id)}\n{error_message}")
            else:
                await bot.send_message(chat_id=user_id, text=f"{phrase_by_user('error_not_valid_input_data', user_id)}\n{error_message}")

