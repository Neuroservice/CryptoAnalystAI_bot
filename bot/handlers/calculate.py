import logging
import traceback
from datetime import datetime
from io import BytesIO
from typing import Optional, Union

import xlsxwriter
from aiogram import Router, types, Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    BufferedInputFile, Message
)
from fpdf import FPDF

from bot.config import API_KEY, API_TOKEN
from bot.data_update import update_or_create
from bot.database.db_setup import SessionLocal
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
    AgentAnswer
)
from bot.handlers.start import user_languages
from bot.utils.consts import tickers, field_mapping, model_mapping, checking_map, ru_additional_headers, \
    eng_additional_headers, headers_mapping
from bot.utils.gpt import (
    category_agent,
    tier_agent,
    tokemonic_agent,
    funds_agent,
    project_rating_agent,
    flags_agent
)
from bot.utils.metrics import process_metrics, check_missing_fields, generate_cells_content, create_project_data_row
from bot.utils.pdf_worker import generate_pie_chart
from bot.utils.project_data import (
    get_project_and_tokenomics,
    get_full_info,
    get_twitter_link_by_symbol,
    fetch_coinmarketcap_data,
    get_user_project_info,
    get_coin_description,
    extract_overall_category,
    standardize_category,
    get_lower_name, check_and_run_tasks, calculate_expected_x
)

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
    if 'RU' in user_languages.values():
        await message.answer(
            "Выберите формат файла: PDF или Excel?",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="PDF"), types.KeyboardButton(text="Excel")],
                ],
                resize_keyboard=True
            )
        )
    else:
        await message.answer(
            "Choose the file format: PDF or Excel?",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="PDF"), types.KeyboardButton(text="Excel")],
                ],
                resize_keyboard=True
            )
        )


def projects_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Layer 1')],
            [KeyboardButton(text='Layer 2 (ETH)')],
            [KeyboardButton(text='Layer 1 (OLD)')],
            [KeyboardButton(text='GameFi / Metaverse')],
            [KeyboardButton(text='TON')],
            [KeyboardButton(text='NFT Platforms / Marketplaces')],
            [KeyboardButton(text='Infrastructure')],
            [KeyboardButton(text='AI')],
            [KeyboardButton(text='RWA')],
            [KeyboardButton(text='Digital Identity')],
            [KeyboardButton(text='Blockchain Service')],
            [KeyboardButton(text='Financial sector')],
            [KeyboardButton(text='SocialFi')],
            [KeyboardButton(text='DeFi')],
            [KeyboardButton(text='Modular Blockchain')],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def analysis_type_keyboard():
    if 'RU' in user_languages.values():
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Блок ребалансировки портфеля')],
                [KeyboardButton(text='Блок анализа и оценки проектов')],
                [KeyboardButton(text='Блок анализа цены на листинге (бета)')],
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Block of portfolio rebalancing')],
                [KeyboardButton(text='Block of projects analysis and evaluation')],
                [KeyboardButton(text='Block of price analysis on the listing (beta)')],
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    return keyboard


@calculate_router.message(lambda message: message.text == 'Расчет и анализ проектов' or message.text == 'Project Calculation & Analysis' or message.text == "Пожалуйста, выберите новый проект для расчета.")
async def project_chosen(message: types.Message, state: FSMContext):

    if 'RU' in user_languages.values():
        await message.answer(
            "Если вы хотите просто рассчитать цену токена, на основании похожих проектов, выберите кнопку 'Блок ребалансировки портфеля'.\n\n"
            "Если хотите полную сравнительную характеристику по токенам и ребалансировку портфеля, выберите кнопку 'Блок анализа и оценки проектов'.",
            reply_markup=analysis_type_keyboard()
        )
    else:
        await message.answer(
            "If you want to simply calculate the token price based on similar projects, choose the 'Block of portfolio rebalancing' button.\n\n"
            "If you want a full comparison of token characteristics, choose the 'Block of projects analysis and evaluation' button.",
            reply_markup=analysis_type_keyboard()
        )

    await state.set_state(CalculateProject.choosing_analysis_type)


@calculate_router.message(CalculateProject.choosing_analysis_type)
async def analysis_type_chosen(message: types.Message, state: FSMContext):
    analysis_type = message.text.lower()

    if analysis_type in ['блок ребалансировки портфеля', 'block of portfolio rebalancing']:
        if 'RU' in user_languages.values():
            await message.answer(
                "Введите название монеты (например SOL, SUI):",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.set_state(CalculateProject.waiting_for_basic_data)
        else:
            await message.answer(
                "Enter the coin name (for example SOL, SUI):",
                reply_markup=ReplyKeyboardRemove()
            )
            await state.set_state(CalculateProject.waiting_for_basic_data)

    elif analysis_type in ['блок анализа и оценки проектов', 'block of projects analysis and evaluation']:
        if 'RU' in user_languages.values():
            await message.answer(
                "Выберите формат файла: PDF или Excel?",
                reply_markup=types.ReplyKeyboardMarkup(
                    keyboard=[
                        [types.KeyboardButton(text="PDF"), types.KeyboardButton(text="Excel")],
                    ],
                    resize_keyboard=True
                )
            )
        else:
            await message.answer(
                "Choose the file format: PDF or Excel?",
                reply_markup=types.ReplyKeyboardMarkup(
                    keyboard=[
                        [types.KeyboardButton(text="PDF"), types.KeyboardButton(text="Excel")],
                    ],
                    resize_keyboard=True
                )
            )
        await state.set_state(CalculateProject.choosing_file_format)


@calculate_router.message(CalculateProject.choosing_file_format)
async def file_format_chosen(message: types.Message, state: FSMContext):
    file_format = message.text.lower()

    if file_format in ['pdf', 'excel']:
        await state.update_data(file_format=file_format)
        await message.answer(
            "Введите тикер токена (например STRK, SUI):" if 'RU' in user_languages.values() else "Enter the token ticker (e.g. STRK, SUI):",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(CalculateProject.waiting_for_data)

    else:
        await message.answer("Пожалуйста, выберите формат файла: PDF или Excel.")


@calculate_router.message(CalculateProject.waiting_for_excel)
async def await_to_create_excel(message: types.Message, state: FSMContext):
    await create_excel(state, message)


@calculate_router.message(CalculateProject.waiting_for_pdf)
async def await_to_create_pdf(message: types.Message, state: FSMContext):
    await create_pdf(state, message)


@calculate_router.message(CalculateProject.waiting_for_basic_results)
async def await_basic_report(message: types.Message, state: FSMContext):
    await create_basic_report(state, message)


@calculate_router.message(CalculateProject.waiting_for_basic_data)
async def receive_basic_data(message: types.Message, state: FSMContext):
    user_coin_name = message.text.upper().replace(" ", "")
    session = SessionLocal()
    new_project = None
    price = None
    total_supply = None
    fundraise = None
    calculation_record = None

    if user_coin_name.lower() == "/exit":
        await message.answer("Завершение расчетов. Чтобы начать снова пользоваться ботом, введите команду /start.")
        await state.clear()
        return

    twitter_name, description, lower_name = await get_twitter_link_by_symbol(user_coin_name)
    if not lower_name:
        lower_name = await get_lower_name(user_coin_name)

    coin_description = await get_coin_description(lower_name)
    if description:
        coin_description += description

    category_answer = category_agent(topic=coin_description)
    overall_category = extract_overall_category(category_answer)
    chosen_project_name = standardize_category(overall_category)

    if chosen_project_name == 'Unknown Category':
        if 'RU' in user_languages.values():
            await message.answer(f"Токен не подошел ни под одну из категорий, попробуйте другой.")
        else:
            await message.answer(f"The token did not fit any of the categories, try another one")

    try:
        projects, tokenomics_data_list = await get_project_and_tokenomics(session, chosen_project_name, user_coin_name)
        filtered_projects = [
            (project, tokenomics_data)
            for project, tokenomics_data in tokenomics_data_list
            if project.coin_name in tickers
        ]

        top_projects = sorted(
            filtered_projects,
            key=lambda item: item[1][0].capitalization if item[1][0].capitalization else 0,
            reverse=True
        )[:5]

        results = []
        agents_info = []
        for index, (project, tokenomics_data) in enumerate(top_projects, start=1):
            for tokenomics in tokenomics_data:
                parameters = {
                    'symbol': user_coin_name,
                    'convert': 'USD'
                }
                headers = {
                    'X-CMC_PRO_API_KEY': API_KEY,
                    'Accepts': 'application/json'
                }

                coin_data = await fetch_coinmarketcap_data(message, user_coin_name, headers, parameters)
                if not coin_data:
                    await message.answer("Ошибка: данные о монете не получены. Проверьте введённый тикер.")
                    return

                coin_name = coin_data["coin_name"]
                circulating_supply = coin_data["circulating_supply"]
                total_supply = coin_data["total_supply"]
                price = coin_data["price"]
                capitalization = coin_data["capitalization"]
                coin_fdv = coin_data["coin_fdv"]
                project = session.query(Project).filter_by(coin_name=project.coin_name).first()

                fdv = tokenomics.fdv if tokenomics.fdv else 0
                calculation_result = calculate_expected_x(
                    entry_price=price,
                    total_supply=total_supply,
                    fdv=fdv,
                )

                existing_project = session.query(Project).filter_by(coin_name=user_coin_name).first()
                if existing_project:
                    new_project = existing_project
                else:
                    new_project = Project(
                        project_name=chosen_project_name,
                        coin_name=user_coin_name
                    )
                    session.add(new_project)
                    session.commit()

                existing_basic_metrics = session.query(BasicMetrics).filter_by(project_id=new_project.id).first()
                if not existing_basic_metrics:
                    basic_metrics = BasicMetrics(
                        project_id=new_project.id,
                        entry_price=price,
                        sphere=chosen_project_name,
                        market_price=price,
                    )
                    session.add(basic_metrics)

                existing_tokenomic = session.query(Tokenomics).filter_by(project_id=new_project.id).first()
                if not existing_tokenomic:
                    tokenomic = Tokenomics(
                        project_id=new_project.id,
                        total_supply=total_supply,
                        circ_supply=circulating_supply,
                        capitalization=capitalization,
                        fdv=coin_fdv
                    )
                    session.add(tokenomic)
                elif existing_tokenomic.capitalization != capitalization:
                    existing_tokenomic.capitalization = capitalization
                    session.add(existing_tokenomic)

                session.commit()

                if "error" in calculation_result:
                    raise ValueError(calculation_result["error"])

                fair_price = calculation_result['fair_price']
                fair_price = f"{fair_price:.5f}" if isinstance(fair_price, (int, float)) else "Ошибка в расчетах" if 'RU' in user_languages.values() else "Error on market"

                if 'RU' in user_languages.values() and project.coin_name in tickers:
                    results.append(
                        f"Вариант {index}\n"
                        f"Результаты расчета для {user_coin_name} в сравнении с {project.coin_name}:\n"
                        f"Возможный прирост токена (в %): {(calculation_result['expected_x'] - 1.0) * 100:.2f}%\n"
                        f"Ожидаемая цена токена: {fair_price}\n"
                    )
                elif 'ENG' in user_languages.values() and project.coin_name in tickers:
                    results.append(
                        f"Variant {index}\n"
                        f"Calculation results for {user_coin_name} compared to {project.coin_name}:\n"
                        f"Possible token growth (in %): {(calculation_result['expected_x'] - 1.0) * 100:.2f}%\n"
                        f"The expected price of the token: {fair_price}\n"
                    )

                agents_info.append([
                    index,
                    user_coin_name,
                    chosen_project_name,
                    price,
                    (calculation_result['expected_x'] - 1.0) * 100,
                    fair_price
                ])

        if new_project:
            calculation_record = Calculation(
                user_id=message.from_user.id,
                project_id=new_project.id,
                date=datetime.now()
            )
            session.add(calculation_record)
            session.commit()

        else:
            existing_calculation = session.query(Calculation).filter_by(user_id=message.from_user.id, project_id=new_project.id).first()
            existing_calculation.date = datetime.now()

        project_info = await get_user_project_info(session, user_coin_name)
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
            lower_name=lower_name
        )

        if user_coin_name not in tickers:
            new_project = update_or_create(
                session, Project,
                defaults={
                    'project_name': chosen_project_name
                },
                coin_name=user_coin_name
            )
        else:
            new_project = session.query(Project).filter_by(coin_name=user_coin_name).first()

        update_or_create(
            session, BasicMetrics,
            defaults={
                'entry_price': price,
                'sphere': chosen_project_name,
                'market_price': price,
            },
            project_id=new_project.id
        )

        if tasks.get("social_metrics", []):
            (twitter_subs, twitter_twitterscore) = tasks.get("social_metrics", [])[0]
            twitter = twitter_subs
            twitterscore = twitter_twitterscore
            if twitter and twitterscore:
                update_or_create(
                    session, SocialMetrics,
                    defaults={
                        'twitter': twitter,
                        'twitterscore': twitterscore
                    },
                    project_id=new_project.id)

        if tasks.get("investing_metrics", []):
            fundraise, investors = tasks.get("investing_metrics", [])[0]
            if user_coin_name not in tickers and fundraise and investors:
                update_or_create(
                    session, InvestingMetrics,
                    defaults={
                        'fundraise': fundraise,
                        'fund_level': investors
                    },
                    project_id=new_project.id
                )
            elif fundraise:
                update_or_create(
                    session, InvestingMetrics,
                    defaults={
                        'fundraise': fundraise,
                    },
                    project_id=new_project.id
                )

        if tasks.get("network_metrics", []):
            last_tvl = tasks.get("network_metrics", [])[0]
            if last_tvl and price and total_supply:
                update_or_create(
                    session, NetworkMetrics,
                    defaults={
                        'tvl': last_tvl if last_tvl else 0,
                        'tvl_fdv': last_tvl / (price * total_supply) if last_tvl and total_supply and price else 0
                    },
                    project_id=new_project.id
                )

        if tasks.get("manipulative_metrics", []):
            top_100_wallets = tasks.get("manipulative_metrics", [])[0]
            update_or_create(
                session, ManipulativeMetrics,
                defaults={
                    'fdv_fundraise': (price * total_supply) / fundraise if fundraise else None,
                    'top_100_wallet': top_100_wallets
                },
                project_id=new_project.id
            )

        funds_profit_data = tasks.get("funds_profit", [])
        output_string = '\n'.join(funds_profit_data[0]) if funds_profit_data and funds_profit_data[0] else ''

        if output_string and output_string != '':
            update_or_create(
                session, FundsProfit,
                defaults={
                    'distribution': output_string,
                },
                project_id=new_project.id)

        if tasks.get("market_metrics", []):
            fail_high, growth_low, max_price, min_price = tasks.get("market_metrics", [])[0]
            if fail_high and growth_low and max_price and min_price:
                update_or_create(
                    session, MarketMetrics,
                    defaults={'fail_high': fail_high, 'growth_low': growth_low},
                    project_id=new_project.id
                )
                update_or_create(
                    session, TopAndBottom,
                    defaults={'lower_threshold': min_price, 'upper_threshold': max_price},
                    project_id=new_project.id
                )

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

        if missing_fields_string:
            response_message = (
                    f"Отсутствующие данные для запроса: {missing_fields_string}.\n"
                    "Пожалуйста, предоставьте эти данные в следующем формате:\n"
                    + '\n'.join(examples)
            )
            await message.answer(response_message)
            data = {
                "user_coin_name": user_coin_name,
                "id": calculation_record.id,
                "category_answer": category_answer,
                "chosen_project": chosen_project_name,
                "new_project": new_project,
                "results": results,
                "agents_info": agents_info,
                "missing_fields": missing_fields,
                "twitter_name": twitter_name,
            }

            await state.update_data(**data)
            await state.set_state(CalculateProject.waiting_for_basic_results)
        else:
            data = {
                "user_coin_name": user_coin_name,
                "id": calculation_record.id,
                "category_answer": category_answer,
                "new_project": new_project,
                "chosen_project": chosen_project_name,
                "results": results,
                "agents_info": agents_info,
                "missing_fields": missing_fields,
                "twitter_name": twitter_name,
            }

            await state.update_data(**data)
            await create_basic_report(state, message='-', user_id=message.from_user.id)

    except ValueError as e:
        error_message = traceback.format_exc()
        if 'RU' in user_languages.values():
            await message.answer(
                f"Ошибка: {str(e)} Подробности ошибки:\n{error_message}\nПожалуйста, убедитесь, что все данные введены корректно.")
        else:
            await message.answer(
                f"Error: {str(e)} Details of error:\n{error_message}\nPlease make sure all data is entered correctly.")


@calculate_router.message(CalculateProject.waiting_for_data)
async def receive_data(message: types.Message, state: FSMContext):
    investors = None
    coin_name = None
    price = None
    total_supply = None
    fundraise = None
    results = None
    calculation_record = None

    user_coin_name = message.text.upper().replace(" ", "")
    if user_coin_name.lower() == "/exit":
        await message.answer("Завершение расчетов. Чтобы начать снова пользоваться ботом, введите команду /start.")
        await state.clear()
        return

    data = await state.get_data()
    selected_format = data.get("file_format")
    session = SessionLocal()
    await message.answer(
        "Делаю расчеты⏳\nЭто может занять некоторое время..." if 'RU' in user_languages.values() else "I'm doing the calculations⏳\nThis may take some time...",
    )

    twitter_name, description, lower_name = await get_twitter_link_by_symbol(user_coin_name)
    coin_description = await get_coin_description(lower_name)
    if description:
        coin_description += description

    category_answer = category_agent(topic=coin_description)
    overall_category = extract_overall_category(category_answer)
    chosen_project = standardize_category(overall_category)

    project_info = await get_user_project_info(session, user_coin_name)
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

    if selected_format == 'excel':
        try:
            parameters = {
                'symbol': user_coin_name,
                'convert': 'USD'
            }
            headers = {
                'X-CMC_PRO_API_KEY': API_KEY,
                'Accepts': 'application/json'
            }

            if not tokenomics_data.circ_supply or tokenomics_data.total_supply or tokenomics_data.capitalization or tokenomics_data.fdv or basic_metrics.market_price:
                coinmarketcap_data = await fetch_coinmarketcap_data(message, user_coin_name, headers, parameters)
                if coinmarketcap_data:
                    coin_name = coinmarketcap_data['coin_name']
                    circulating_supply = coinmarketcap_data['circulating_supply']
                    total_supply = coinmarketcap_data['total_supply']
                    price = coinmarketcap_data['price']
                    capitalization = coinmarketcap_data['market_cap']
                    coin_fdv = coinmarketcap_data['coin_fdv']

                    update_or_create(
                        session, Tokenomics,
                        defaults={
                            'capitalization': capitalization,
                            'total_supply': total_supply,
                            'circ_supply': circulating_supply,
                            'fdv': coin_fdv
                        },
                        project_id=project.id
                    )
                    session.commit()
                else:
                    if 'RU' in user_languages.values():
                        await message.answer(f"Ошибка. Проверьте правильность введенной монеты и попробуйте еще раз.")
                        return
                    else:
                        await message.answer(f"Error. Check that the coin entered is correct and try again.")
                        return
            else:
                coin_name = project.coin_name
                total_supply = tokenomics_data.total_supply
                price = basic_metrics.market_price

            logging.info(f"results {results}")

        except Exception as e:
            logging.error(f"Error in data fetching: {e}")

        results = await check_and_run_tasks(
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
            lower_name=lower_name
        )

        new_project = process_metrics(session, user_coin_name, chosen_project, results, price, total_supply, fundraise, investors)

        if new_project:
            calculation_record = Calculation(
                user_id=message.from_user.id,
                project_id=new_project.id,
                date=datetime.now()
            )
            session.add(calculation_record)
            session.commit()

        else:
            existing_calculation = session.query(Calculation).filter_by(user_id=message.from_user.id,project_id=new_project.id).first()
            existing_calculation.date = datetime.now()
            session.add(existing_calculation)
            session.commit()

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
        if missing_fields_string:
            response_message = (
                    f"Отсутствующие данные для запроса: {missing_fields_string}.\n"
                    "Пожалуйста, предоставьте эти данные в следующем формате:\n"
                    + '\n'.join(examples)
            )
            await message.answer(response_message)
            data = {
                "new_project": new_project,
                "id": calculation_record.id,
                "category_answer": category_answer,
                "chosen_project": chosen_project,
                "twitter_name": twitter_name,
                "coin_name": coin_name,
                "price": price,
                "total_supply": total_supply,
            }

            await state.update_data(**data)
            await state.set_state(CalculateProject.waiting_for_excel)
        else:
            data = {
                "new_project": new_project,
                "id": calculation_record.id,
                "category_answer": category_answer,
                "chosen_project": chosen_project,
                "twitter_name": twitter_name,
                "coin_name": coin_name,
                "price": price,
                "total_supply": total_supply,
            }

            await state.update_data(**data)
            await create_excel(state, message='-', user_id=message.from_user.id)

    elif selected_format == 'pdf':
        parameters = {
            'symbol': user_coin_name,
            'convert': 'USD'
        }

        headers = {
            'X-CMC_PRO_API_KEY': API_KEY,
            'Accepts': 'application/json'
        }

        twitter_name = await get_twitter_link_by_symbol(user_coin_name)

        try:
            if not tokenomics_data.circ_supply or tokenomics_data.total_supply or tokenomics_data.capitalization or tokenomics_data.fdv or basic_metrics.market_price:
                coinmarketcap_data = await fetch_coinmarketcap_data(message, user_coin_name, headers, parameters)
                if coinmarketcap_data:
                    coin_name = coinmarketcap_data['coin_name']
                    total_supply = coinmarketcap_data['total_supply']
                    price = coinmarketcap_data['price']

                else:
                    if 'RU' in user_languages.values():
                        await message.answer(f"Ошибка. Проверьте правильность введенной монеты и попробуйте еще раз.")
                        return
                    else:
                        await message.answer(f"Error. Check that the coin entered is correct and try again.")
                        return
            else:
                coin_name = tokenomics_data.coin_name
                total_supply = tokenomics_data.total_supply
                price = basic_metrics.market_price

        except Exception as e:
            logging.error(f"Error in data fetching: {e}")

        results = await check_and_run_tasks(
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
            lower_name=lower_name
        )
        new_project = process_metrics(session, user_coin_name, chosen_project, results, price, total_supply, fundraise, investors)

        if new_project:
            calculation_record = Calculation(
                user_id=message.from_user.id,
                project_id=new_project.id,
                date=datetime.now()
            )
            session.add(calculation_record)
            session.commit()

        else:
            existing_calculation = session.query(Calculation).filter_by(user_id=message.from_user.id,project_id=new_project.id).first()
            existing_calculation.date = datetime.now()
            session.add(existing_calculation)
            session.commit()

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

        if missing_fields_string:
            response_message = (
                    f"Отсутствующие данные для запроса: {missing_fields_string}.\n"
                    "Пожалуйста, предоставьте эти данные в следующем формате:\n"
                    + '\n'.join(examples)
            )

            await message.answer(response_message)
            data = {
                "new_project": new_project,
                "id": calculation_record.id,
                "category_answer": category_answer,
                "chosen_project": chosen_project,
                "twitter_name": twitter_name,
                "coin_name": coin_name,
                "price": price,
                "total_supply": total_supply
            }

            await state.update_data(**data)
            await state.set_state(CalculateProject.waiting_for_pdf)
        else:
            data = {
                "new_project": new_project,
                "id": calculation_record.id,
                "category_answer": category_answer,
                "chosen_project": chosen_project,
                "twitter_name": twitter_name,
                "coin_name": coin_name,
                "price": price,
                "total_supply": total_supply
            }

            await state.update_data(**data)
            await create_pdf(state, message='-', user_id=message.from_user.id)


async def create_basic_report(state: FSMContext, message: Optional[Union[Message, str]] = None, user_id: Optional[int] = None):
    session = SessionLocal()
    state_data = await state.get_data()
    logging.info(f"state data {state_data}")
    user_coin_name = state_data.get("user_coin_name")
    category_answer = state_data.get("category_answer")
    results = state_data.get("results")
    new_project = state_data.get("new_project")
    agents_info = state_data.get("agents_info")
    twitter_link = state_data.get("twitter_name")
    calc_id = state_data.get("id")
    chosen_project_obj = session.query(Project).filter(Project.coin_name == user_coin_name).first()
    user_input = message.text if isinstance(message, Message) else message
    updates = {}
    input_lines = user_input.split('\n')

    if user_input != '-':
        for line in input_lines:
            if ":" in line:
                field, value = line.split(":", 1)
                field = field.strip()
                value = value.strip()
                if field in field_mapping:
                    updates[field_mapping[field]] = value

        for (model_name, column_name), value in updates.items():
            model_class = model_mapping.get(model_name)
            model_instance = session.query(model_class).filter_by(project_id=new_project.id).first()

            if model_instance is None:
                model_instance = model_class(project_id=chosen_project_obj.id, **{
                    column_name: float(value) if value.replace('.', '', 1).isdigit() else value})
                session.add(model_instance)
                session.commit()
            else:
                if column_name in model_instance.__table__.columns.keys():
                    if value.replace('.', '', 1).isdigit():
                        value = float(value)
                    setattr(model_instance, column_name, value)
                    session.add(model_instance)
                    session.commit()

    try:
        project_info = await get_user_project_info(session, user_coin_name)
        project = project_info.get("project")
        tokenomics_data = project_info.get("tokenomics_data")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        market_metrics = project_info.get("market_metrics")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")

        existing_answer = session.query(AgentAnswer).filter(AgentAnswer.project_id == project.id, AgentAnswer.language == ('RU' if 'RU' in user_languages.values() else 'ENG')).first()

        if existing_answer is None:
            all_data_string_for_tier_agent = (
                f"Название проекта: {project.coin_name if project else 'N/A'}\n"
                f"Категория: {project.project_name if project else 'N/A'}\n"
                f"Капитализация: {tokenomics_data.capitalization if tokenomics_data else 'N/A'}\n"
                f"Сумма сбора средств от инвесторов (Fundraising): {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"Количество подписчиков на Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"Twitter Score: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"Инвесторы: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n"
            )

            comparison_results = ""
            for index, coin_name, project_name, price, expected_x, fair_price in agents_info:
                comparison_results += (
                    f"Вариант {index}\n"
                    f"Результаты расчета для {project.coin_name} в сравнении с {coin_name}:\n"
                    f"Возможный прирост токена (в %): {expected_x}%\n"
                    f"Ожидаемая цена токена: {fair_price}\n\n"
                )
            all_data_string_for_tokemonic_agent = (
                f"Название проекта: {project.coin_name if project else 'N/A'}\n"
                f"**Исходные данные:**\n\n"
                f"{comparison_results}"
            )

            all_data_string_for_funds_agent = (
                f"Название проекта: {project.coin_name if project else 'N/A'}\n"
                f"Доходность фондов (%): {funds_profit.distribution if funds_profit else 'N/A'}\n"
                f"Рост токена с минимальных значений (%): {market_metrics.growth_low if market_metrics else 'N/A'}\n"
                f"Падение токена от максимальных значений (%): {market_metrics.fail_high if market_metrics else 'N/A'}\n"
                f"Процент монет на топ 100 кошельков (%): {manipulative_metrics.top_100_wallet * 100 if manipulative_metrics else 'N/A'}\n"
                f"Процент заблокированных токенов (%): {(network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'}\n\n"
            )

            tier_answer = tier_agent(topic=all_data_string_for_tier_agent)
            tokemonic_answer = tokemonic_agent(topic=all_data_string_for_tokemonic_agent)
            funds_answer = funds_agent(topic=all_data_string_for_funds_agent)

            all_data_string_for_project_rating_agent = (
                f"Сумма сбора средств от инвесторов (Fundraising): {investing_metrics.fundraise if investing_metrics else 'N/A'}\n",
                f"Тир проекта: {tier_answer}\n",
                f"Количество подписчиков на Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"Twitter Score: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"Оценка токемоники (нужна общая оценка проекта в баллах): {tokemonic_answer if tokemonic_answer else 'N/A'}\n"
                f"Оценка прибыльности фондов: {funds_answer if funds_answer else 'N/A'}\n"
            )
            project_rating_answer = project_rating_agent(topic=all_data_string_for_project_rating_agent)

            all_data_string_for_flags_agent = (
                f"Project: {project.project_name}\n"
                f"Category agent answer: {category_answer}\n",
                f"Tier agent: {tier_answer}\n",
                f"Tokemonic agent: {tokemonic_answer}\n",
                f"Funds agent: {funds_answer}\n",
                f"Project rating agent: {project_rating_answer}\n"
                f"Social metrics: Количество подписчиков - {social_metrics.twitter} (twitter link: {twitter_link}), Twitter Score - {social_metrics.twitterscore}"
                f"**Дополнительные данные, использованные для расчетов**\n"
                f"- Project Name: {project.coin_name if project else 'N/A'}\n"
                f"- Category: {project.project_name if project else 'N/A'}\n"
                f"- Capitalization: {tokenomics_data.capitalization if tokenomics_data else 'N/A'}\n"
                f"- Fundraising: {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"- Investors Tier: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n"
                f"- Project Name: {project.coin_name if project else 'N/A'}\n"
                f"**Данные для расчета**\n"
                f"- Распределение токенов: {funds_profit.distribution if funds_profit else 'N/A'}\n"
                f"- Рост стоимости токенов с минимума: x{market_metrics.growth_low if market_metrics else 'N/A'}\n"
                f"- Падение токенов с максимума: {market_metrics.fail_high if market_metrics else 'N/A'}%\n"
                f"- Процент нахождения монет на топ 100 кошельков блокчейна: {manipulative_metrics.top_100_wallet * 100 if manipulative_metrics else 'N/A'}%\n"
                f"- Заблокированные токены (TVL): {(network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'}%\n\n"
                f"- Сумма привлечения средств: {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"- Тир проекта: {tier_answer}\n"
                f"- Подписчики в Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"- Оценка подписчиков твиттера: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"- Оценка токеномики (сравнение с другими проектами): {tokemonic_answer if tokemonic_answer else 'N/A'}\n"
                f"- Оценка доходности фондов: {funds_answer if funds_answer else 'N/A'}\n"
            )
            if 'RU' in user_languages.values():
                flags_answer = flags_agent(topic=all_data_string_for_flags_agent, language='русский')
            else:
                flags_answer = flags_agent(topic=all_data_string_for_flags_agent, language='english')

            existing_answer = session.query(AgentAnswer).filter_by(project_id=project.id, language='RU' if 'RU' in user_languages.values() else 'ENG').first()
            if not existing_answer:
                agent_answer_record = AgentAnswer(
                    project_id=project.id,
                    answer=flags_answer,
                    language='RU' if 'RU' in user_languages.values() else 'ENG'
                )
                session.add(agent_answer_record)
                session.commit()
            else:
                agent_answer_record = existing_answer

            if isinstance(message, Message):
                existing_calculation = session.query(Calculation).filter_by(calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()
            elif user_id is not None:
                existing_calculation = session.query(Calculation).filter_by(calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()

            session.add(agent_answer_record)
            session.commit()

        else:
            flags_answer = existing_answer.answer

            if isinstance(message, Message):
                existing_calculation = session.query(Calculation).filter_by(calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()
            elif user_id is not None:
                existing_calculation = session.query(Calculation).filter_by(calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()

        answer = "\n".join(results)
        answer += "\n" + flags_answer

        if isinstance(message, Message):
            await message.answer(
                f"{answer}\n",
            )
            if 'RU' in user_languages.values():
                await message.answer(
                    "Введите тикер следующего токена (например APT, ZK) или введите /exit для завершения:",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await message.answer(
                    "Enter the ticker of the next token (e.g. APT, ZK) or enter /exit to complete:",
                    reply_markup=ReplyKeyboardRemove()
                )
        elif user_id is not None:
            async with AiohttpSession() as session:
                bot = Bot(token=API_TOKEN, session=session)
                await bot.send_message(chat_id=user_id, text=f"{answer}\n")
                if 'RU' in user_languages.values():
                    await bot.send_message(
                        chat_id=user_id,
                        text="Введите тикер следующего токена (например APT, ZK) или введите /exit для завершения:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text="Enter the ticker of the next token (e.g. APT, ZK) or enter /exit to complete:",
                        reply_markup=ReplyKeyboardRemove()
                    )
        else:
            logging.error("Не указан ни объект Message, ни user_id для отправки документа.")

    except ValueError as e:
        error_message = traceback.format_exc()
        if 'RU' in user_languages.values():
            await message.answer(
                f"Ошибка: {str(e)} Подробности ошибки:\n{error_message}\nПожалуйста, убедитесь, что все данные введены корректно.")
        else:
            await message.answer(
                f"Error: {str(e)} Details of error:\n{error_message}\nPlease make sure all data is entered correctly.")


async def create_excel(state: FSMContext, message: Optional[Union[Message, str]] = None, user_id: Optional[int] = None):
    session = SessionLocal()
    state_data = await state.get_data()
    chosen_project = state_data.get("chosen_project")
    category_answer = state_data.get("category_answer")
    new_project = state_data.get("new_project")
    coin_name = state_data.get("coin_name")
    price = state_data.get("price")
    twitter_link = state_data.get("twitter_name")
    total_supply = state_data.get("total_supply")
    calc_id = state_data.get("id")
    chosen_project_obj = session.query(Project).filter(Project.coin_name == coin_name).first()
    user_input = message.text if isinstance(message, Message) else message
    updates = {}
    input_lines = user_input.split('\n')

    if user_input != '-':
        for line in input_lines:
            if ":" in line:
                field, value = line.split(":", 1)
                field = field.strip()
                value = value.strip()
                if field in field_mapping:
                    updates[field_mapping[field]] = value

        for (model_name, column_name), value in updates.items():
            model_class = model_mapping.get(model_name)
            model_instance = session.query(model_class).filter_by(project_id=new_project.id).first()

            if model_instance is None:
                model_instance = model_class(project_id=chosen_project_obj.id, **{
                    column_name: float(value) if value.replace('.', '', 1).isdigit() else value})
                session.add(model_instance)
                session.commit()
            else:
                if column_name in model_instance.__table__.columns.keys():
                    if value.replace('.', '', 1).isdigit():
                        value = float(value)
                    setattr(model_instance, column_name, value)
                    session.add(model_instance)
                    session.commit()

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

    if 'RU' in user_languages.values():
        headers = [
            "Вариант",
            "Монета",
            "Расчеты относительно монеты",
            "Текущая цена, $",
            "Возможный прирост токена (в %)",
            "Ожидаемая цена токена, $"
        ]
    else:
        headers = [
            "Option",
            "Coin",
            "Calculations relative to coin",
            "Current price, $"
            "Increase in coins (in %)",
            "Possible token growth, $"
        ]

    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header, header_format)

    try:
        projects, tokenomics_data_list = await get_project_and_tokenomics(session, chosen_project, coin_name)
        row_data = []

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
                    price,
                    expected_x,
                    fair_price
                ])

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
        if 'RU' in user_languages.values():
            additional_headers = ru_additional_headers
        else:
            additional_headers = eng_additional_headers

        for col_num, header in enumerate(additional_headers):
            worksheet.write(empty_row + 1, col_num, header, header_format)

        (projects,
         tokenomics_data_list,
         basic_metrics_data_list,
         invested_metrics_data_list,
         social_metrics_data_list,
         funds_profit_data_list,
         top_and_bottom_data_list,
         market_metrics_data_list,
         manipulative_metrics_data_list,
         network_metrics_data_list) = get_full_info(session, chosen_project, coin_name)

        project_info = await get_user_project_info(session, new_project.coin_name)
        project = project_info.get("project")
        tokenomics_data = project_info.get("tokenomics_data")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        market_metrics = project_info.get("market_metrics")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")

        existing_answer = session.query(AgentAnswer).filter(
            AgentAnswer.project_id == project.id,
            AgentAnswer.language == ('RU' if 'RU' in user_languages.values() else 'ENG')
        ).first()

        if existing_answer is None:
            all_data_string_for_tier_agent = (
                f"Название проекта: {project.coin_name if project else 'N/A'}\n"
                f"Категория: {project.project_name if project else 'N/A'}\n"
                f"Капитализация: {tokenomics_data.capitalization if tokenomics_data else 'N/A'}\n"
                f"Сумма сбора средств от инвесторов (Fundraising): {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"Количество подписчиков на Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"Twitter Score: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"Инвесторы: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n"
            )

            comparison_results = ""
            for index, coin_name, project_name, price, expected_x, fair_price in row_data:
                comparison_results += (
                    f"Вариант {index}\n"
                    f"Результаты расчета для {project.coin_name} в сравнении с {coin_name}:\n"
                    f"Возможный прирост токена (в %): {expected_x}%\n"
                    f"Ожидаемая цена токена: {fair_price}\n\n"
                )
            all_data_string_for_tokemonic_agent = (
                f"Название проекта: {project.coin_name if project else 'N/A'}\n"
                f"**Исходные данные:**\n\n"
                f"{comparison_results}"
            )

            all_data_string_for_funds_agent = (
                f"Название проекта: {project.coin_name if project else 'N/A'}\n"
                f"Доходность фондов (%): {funds_profit.distribution if funds_profit else 'N/A'}\n"
                f"Рост токена с минимальных значений (%): {market_metrics.growth_low if market_metrics else 'N/A'}\n"
                f"Падение токена от максимальных значений (%): {market_metrics.fail_high if market_metrics else 'N/A'}\n"
                f"Процент монет на топ 100 кошельков (%): {manipulative_metrics.top_100_wallet * 100 if manipulative_metrics else 'N/A'}\n"
                f"Процент заблокированных токенов (%): {(network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'}\n\n"
            )

            tier_answer = tier_agent(topic=all_data_string_for_tier_agent)
            tokemonic_answer = tokemonic_agent(topic=all_data_string_for_tokemonic_agent)
            funds_answer = funds_agent(topic=all_data_string_for_funds_agent)

            all_data_string_for_project_rating_agent = (
                f"Сумма сбора средств от инвесторов (Fundraising): {investing_metrics.fundraise if investing_metrics else 'N/A'}\n",
                f"Тир проекта: {tier_answer}\n",
                f"Количество подписчиков на Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"Twitter Score: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"Оценка токемоники (нужна общая оценка проекта в баллах): {tokemonic_answer if tokemonic_answer else 'N/A'}\n"
                f"Оценка прибыльности фондов: {funds_answer if funds_answer else 'N/A'}\n"
            )
            project_rating_answer = project_rating_agent(topic=all_data_string_for_project_rating_agent)

            all_data_string_for_flags_agent = (
                f"Project: {project.project_name}\n"
                f"Category agent answer: {category_answer}\n",
                f"Tier agent: {tier_answer}\n",
                f"Tokemonic agent: {tokemonic_answer}\n",
                f"Funds agent: {funds_answer}\n",
                f"Project rating agent: {project_rating_answer}\n"
                f"Social metrics: Количество подписчиков - {social_metrics.twitter} (twitter link: {twitter_link}), Twitter Score - {social_metrics.twitterscore}"
                f"**Дополнительные данные, использованные для расчетов**\n"
                f"- Project Name: {project.coin_name if project else 'N/A'}\n"
                f"- Category: {project.project_name if project else 'N/A'}\n"
                f"- Capitalization: {tokenomics_data.capitalization if tokenomics_data else 'N/A'}\n"
                f"- Fundraising: {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"- Investors Tier: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n"
                f"- Project Name: {project.coin_name if project else 'N/A'}\n"
                f"**Данные для расчета**\n"
                f"- Распределение токенов: {funds_profit.distribution if funds_profit else 'N/A'}\n"
                f"- Рост стоимости токенов с минимума: x{market_metrics.growth_low if market_metrics else 'N/A'}\n"
                f"- Падение токенов с максимума: {market_metrics.fail_high if market_metrics else 'N/A'}%\n"
                f"- Процент нахождения монет на топ 100 кошельков блокчейна: {manipulative_metrics.top_100_wallet * 100 if manipulative_metrics else 'N/A'}%\n"
                f"- Заблокированные токены (TVL): {(network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'}%\n\n"
                f"- Сумма привлечения средств: {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"- Тир проекта: {tier_answer}\n"
                f"- Подписчики в Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"- Оценка подписчиков твиттера: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"- Оценка токеномики (сравнение с другими проектами): {tokemonic_answer if tokemonic_answer else 'N/A'}\n"
                f"- Оценка доходности фондов: {funds_answer if funds_answer else 'N/A'}\n"
            )
            if 'RU' in user_languages.values():
                flags_answer = flags_agent(topic=all_data_string_for_flags_agent, language='русский')
            else:
                flags_answer = flags_agent(topic=all_data_string_for_flags_agent, language='english')

            agent_answer_record = AgentAnswer(
                project_id=project.id,
                answer=flags_answer,
                language='RU' if 'RU' in user_languages.values() else 'ENG'
            )

            if isinstance(message, Message):
                existing_calculation = session.query(Calculation).filter_by(id=calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()
            elif user_id is not None:
                existing_calculation = session.query(Calculation).filter_by(id=calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()

            session.add(agent_answer_record)
            session.commit()
        else:
            flags_answer = existing_answer.answer

            if isinstance(message, Message):
                existing_calculation = session.query(Calculation).filter_by(id=calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()
            elif user_id is not None:
                existing_calculation = session.query(Calculation).filter_by(id=calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()

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

        color_palette = ['#FF6633', '#FF33FF', '#00B3E6', '#E6B333', '#3366E6', '#B34D4D', '#6680B3', '#FF99E6', '#FF1A66', '#B366CC', '#4D8000', '#809900']

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
                    'data_labels': {'value': False},  # Убираем показ процентов в диаграмме
                    'points': [{'fill': {'color': color_palette[i % len(color_palette)]}} for i in
                               range(len(chart_data["values"]))],
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

        if isinstance(message, Message):
            await message.answer_document(BufferedInputFile(output.read(), filename="results.xlsx"))
            await state.set_state(None)
            await state.set_state(CalculateProject.waiting_for_data)
            if 'RU' in user_languages.values():
                await message.answer(
                    f"Общая оценка проекта: {flags_answer}\n",
                )
                await message.answer(
                    "Введите тикер следующего токена (например STRK, SUI) или введите /exit для завершения:",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await message.answer(
                    f"Overall project assessment: {flags_answer}\n",
                )
                await message.answer(
                    "Enter the ticker of the next token (e.g. STRK, SUI) or enter /exit to complete:",
                    reply_markup=ReplyKeyboardRemove()
                )
        elif user_id is not None:
            async with AiohttpSession() as session:
                bot = Bot(token=API_TOKEN, session=session)
                await bot.send_document(chat_id=user_id,
                                        document=BufferedInputFile(output.read(), filename="results.xlsx"))
                await state.set_state(None)
                await state.set_state(CalculateProject.waiting_for_data)
                if 'RU' in user_languages.values():
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"Общая оценка проекта: \n{flags_answer}\n",
                    )
                    await bot.send_message(
                        chat_id=user_id,
                        text="Введите тикер следующего токена (например STRK, SUI) или введите /exit для завершения:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"Overall project assessment: \n{flags_answer}\n",
                    )
                    await bot.send_message(
                        chat_id=user_id,
                        text="Enter the ticker of the next token (e.g. STRK, SUI) or enter /exit to complete:",
                        reply_markup=ReplyKeyboardRemove()
                    )
        else:
            logging.error("Не указан ни объект Message, ни user_id для отправки документа.")

    except ValueError as e:
        error_message = traceback.format_exc()
        if isinstance(message, Message):
            if 'RU' in user_languages.values():
                await message.answer(
                    f"Ошибка: {str(e)} Подробности ошибки:\n{error_message}\nПожалуйста, убедитесь, что все данные введены корректно.")
            else:
                await message.answer(
                    f"Error: {str(e)} Error details:\n{error_message}\nPlease make sure all data is entered correctly.")
        elif user_id is not None:
            async with AiohttpSession() as session:
                bot = Bot(token=API_TOKEN, session=session)
                await bot.send_document(user_id, BufferedInputFile(output.read(), filename="results.xlsx"))
                await state.set_state(None)
                await state.set_state(CalculateProject.waiting_for_data)
                if 'RU' in user_languages.values():
                    await bot.send_message(
                        chat_id=user_id,
                        text="Ошибка: {str(e)} Подробности ошибки:\n{error_message}\nПожалуйста, убедитесь, что все данные введены корректно.",
                    )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text="Error: {str(e)} Error details:\n{error_message}\nPlease make sure all data is entered correctly.",
                    )


async def create_pdf(state: FSMContext, message: Optional[Union[Message, str]] = None, user_id: Optional[int] = None):
    session = SessionLocal()
    state_data = await state.get_data()
    logging.info(f"state data {state_data}")
    chosen_project = state_data.get("chosen_project")
    category_answer = state_data.get("category_answer")
    new_project = state_data.get("new_project")
    coin_name = state_data.get("coin_name")
    twitter_link = state_data.get("twitter_name")
    price = state_data.get("price")
    total_supply = state_data.get("total_supply")
    calc_id = state_data.get("id")
    chosen_project_obj = session.query(Project).filter(Project.coin_name == coin_name).first()
    user_input = message.text if isinstance(message, Message) else message
    row_data = []
    cells_content = None

    updates = {}
    input_lines = user_input.split('\n')
    if user_input != '-':
        for line in input_lines:
            if ":" in line:
                field, value = line.split(":", 1)
                field = field.strip()
                value = value.strip()
                if field in field_mapping:
                    updates[field_mapping[field]] = value

        for (model_name, column_name), value in updates.items():
            model_class = model_mapping.get(model_name)
            model_instance = session.query(model_class).filter_by(project_id=new_project.id).first()

            if model_instance is None:
                model_instance = model_class(project_id=chosen_project_obj.id, **{
                    column_name: float(value) if value.replace('.', '', 1).isdigit() else value})
                session.add(model_instance)
                session.commit()
            else:
                if column_name in model_instance.__table__.columns.keys():
                    logging.info(f"in columns {value}")
                    if value.replace('.', '', 1).isdigit():
                        value = float(value)
                    setattr(model_instance, column_name, value)
                    session.add(model_instance)
                    session.commit()

    if 'RU' in user_languages.values():
        headers = [
            "Вариант",
            "Монета",
            "Расчеты относительно монеты",
            "Прирост монеты (в %)",
            "Ожидаемая цена монеты, $"
        ]
    else:
        headers = [
            "Option",
            "Coin",
            "Calculations relative to coin",
            "Increase in coins (in %)",
            "Expected market price, $"
        ]

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

                fair_price = f"{calculation_result['fair_price']:.5f}" \
                    if isinstance(calculation_result['fair_price'], (int, float)) \
                    else "Ошибка в расчетах"
                expected_x = f"{calculation_result['expected_x']:.5f}"

                row_data.append([
                    index,
                    coin_name,
                    project.coin_name,
                    expected_x,
                    fair_price
                ])

        pdf = FPDF(orientation='L')
        pdf.add_page()
        # pdf.add_font("DejaVu", '', '/app/fonts/DejaVuSansCondensed.ttf', uni=True)
        pdf.add_font("DejaVu", '', 'D:\\dejavu-fonts-ttf-2.37\\ttf\\DejaVuSansCondensed.ttf', uni=True)
        pdf.set_font("DejaVu", size=8)

        for header in headers:
            if header == 'Вариант':
                pdf.cell(30, 10, header, 1)
            else:
                pdf.cell(45, 10, header, 1)
        pdf.ln()

        for row in row_data:
            for col_num, value in enumerate(row):
                if headers[col_num] == 'Вариант':
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
        ) = get_full_info(session, chosen_project, coin_name)

        project_info = await get_user_project_info(session, new_project.coin_name)
        project = project_info.get("project")
        tokenomics_data = project_info.get("tokenomics_data")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        market_metrics = project_info.get("market_metrics")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")
        existing_answer = session.query(AgentAnswer).filter(AgentAnswer.project_id == project.id, AgentAnswer.language == ('RU' if 'RU' in user_languages.values() else 'ENG')).first()

        if existing_answer is None:
            all_data_string_for_tier_agent = (
                f"Название проекта: {project.coin_name if project else 'N/A'}\n"
                f"Категория: {project.project_name if project else 'N/A'}\n"
                f"Капитализация: {tokenomics_data.capitalization if tokenomics_data else 'N/A'}\n"
                f"Сумма сбора средств от инвесторов (Fundraising): {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"Количество подписчиков на Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"Twitter Score: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"Инвесторы: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n"
            )

            comparison_results = ""
            for index, coin_name, project_name, expected_x, fair_price in row_data:
                comparison_results += (
                    f"Вариант {index}\n"
                    f"Результаты расчета для {project.coin_name} в сравнении с {coin_name}:\n"
                    f"Возможный прирост токена (в %): {expected_x}%\n"
                    f"Ожидаемая цена токена: {fair_price}\n\n"
                )
            all_data_string_for_tokemonic_agent = (
                f"Название проекта: {project.coin_name if project else 'N/A'}\n"
                f"**Исходные данные:**\n\n"
                f"{comparison_results}"
            )

            all_data_string_for_funds_agent = (
                f"Название проекта: {project.coin_name if project else 'N/A'}\n"
                f"Доходность фондов (%): {funds_profit.distribution if funds_profit else 'N/A'}\n"
                f"Рост токена с минимальных значений (%): {market_metrics.growth_low if market_metrics else 'N/A'}\n"
                f"Падение токена от максимальных значений (%): {market_metrics.fail_high if market_metrics else 'N/A'}\n"
                f"Процент монет на топ 100 кошельков (%): {manipulative_metrics.top_100_wallet * 100 if manipulative_metrics else 'N/A'}\n"
                f"Процент заблокированных токенов (%): {(network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'}\n\n"
            )

            tier_answer = tier_agent(topic=all_data_string_for_tier_agent)
            tokemonic_answer = tokemonic_agent(topic=all_data_string_for_tokemonic_agent)
            funds_answer = funds_agent(topic=all_data_string_for_funds_agent)

            all_data_string_for_project_rating_agent = (
                f"Сумма сбора средств от инвесторов (Fundraising): {investing_metrics.fundraise if investing_metrics else 'N/A'}\n",
                f"Тир проекта: {tier_answer}\n",
                f"Количество подписчиков на Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"Twitter Score: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"Оценка токемоники (нужна общая оценка проекта в баллах): {tokemonic_answer if tokemonic_answer else 'N/A'}\n"
                f"Оценка прибыльности фондов: {funds_answer if funds_answer else 'N/A'}\n"
            )
            project_rating_answer = project_rating_agent(topic=all_data_string_for_project_rating_agent)

            all_data_string_for_flags_agent = (
                f"Project: {project.project_name}\n"
                f"Category agent answer: {category_answer}\n",
                f"Tier agent: {tier_answer}\n",
                f"Tokemonic agent: {tokemonic_answer}\n",
                f"Funds agent: {funds_answer}\n",
                f"Project rating agent: {project_rating_answer}\n"
                f"Social metrics: Количество подписчиков - {social_metrics.twitter} (twitter link: {twitter_link}), Twitter Score - {social_metrics.twitterscore}"
                f"**Дополнительные данные, использованные для расчетов**\n"
                f"- Project Name: {project.coin_name if project else 'N/A'}\n"
                f"- Category: {project.project_name if project else 'N/A'}\n"
                f"- Capitalization: {tokenomics_data.capitalization if tokenomics_data else 'N/A'}\n"
                f"- Fundraising: {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"- Investors Tier: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n"
                f"- Project Name: {project.coin_name if project else 'N/A'}\n"
                f"**Данные для расчета**\n"
                f"- Распределение токенов: {funds_profit.distribution if funds_profit else 'N/A'}\n"
                f"- Рост стоимости токенов с минимума: x{market_metrics.growth_low if market_metrics else 'N/A'}\n"
                f"- Падение токенов с максимума: {market_metrics.fail_high if market_metrics else 'N/A'}%\n"
                f"- Процент нахождения монет на топ 100 кошельков блокчейна: {manipulative_metrics.top_100_wallet * 100 if manipulative_metrics else 'N/A'}%\n"
                f"- Заблокированные токены (TVL): {(network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'}%\n\n"
                f"- Сумма привлечения средств: {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"- Тир проекта: {tier_answer}\n"
                f"- Подписчики в Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"- Оценка подписчиков твиттера: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"- Оценка токеномики (сравнение с другими проектами): {tokemonic_answer if tokemonic_answer else 'N/A'}\n"
                f"- Оценка доходности фондов: {funds_answer if funds_answer else 'N/A'}\n"
            )
            if 'RU' in user_languages.values():
                flags_answer = flags_agent(topic=all_data_string_for_flags_agent, language='русский')
            else:
                flags_answer = flags_agent(topic=all_data_string_for_flags_agent, language='english')

                agent_answer_record = AgentAnswer(
                    project_id=project.id,
                    answer=flags_answer,
                    language='RU' if 'RU' in user_languages.values() else 'ENG'
                )
                session.add(agent_answer_record)
                session.commit()

                if isinstance(message, Message):
                    existing_calculation = session.query(Calculation).filter_by(id=calc_id).first()
                    existing_calculation.agent_answer = flags_answer
                    session.add(existing_calculation)
                    session.commit()
                elif user_id is not None:
                    existing_calculation = session.query(Calculation).filter_by(id=calc_id).first()
                    existing_calculation.agent_answer = flags_answer
                    session.add(existing_calculation)
                    session.commit()
        else:
            flags_answer = existing_answer.answer

            if isinstance(message, Message):
                existing_calculation = session.query(Calculation).filter_by(id=calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()
            elif user_id is not None:
                existing_calculation = session.query(Calculation).filter_by(id=calc_id).first()
                existing_calculation.agent_answer = flags_answer
                session.add(existing_calculation)
                session.commit()

        investor_data_list = []
        for header_set in headers_mapping:
            for header in header_set:
                if header == 'Тир фондов':
                    pdf.cell(230, 10, header, 1)
                elif header == 'Сфера':
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
                        if i < len(header_set) and header_set[i] == 'Тир фондов':
                            cell_widths.append(230)
                        elif i < len(header_set) and header_set[i] == 'Сфера':
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

        if isinstance(message, Message):
            await message.answer_document(BufferedInputFile(pdf_output.read(), filename="results.pdf"))
            await state.set_state(None)
            await state.set_state(CalculateProject.waiting_for_data)
            if 'RU' in user_languages.values():
                await message.answer(f"Общая оценка проекта: \n{flags_answer}\n")
                await message.answer(
                    "Введите тикер следующего токена (например STRK, SUI) или введите /exit для завершения:",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await message.answer(f"Overall project assessment: \n{flags_answer}\n")
                await message.answer(
                    "Enter the ticker of the next token (e.g. STRK, SUI) or enter /exit to complete:",
                    reply_markup=ReplyKeyboardRemove()
                )
        elif user_id is not None:
            async with AiohttpSession() as session:
                bot = Bot(token=API_TOKEN, session=session)
                await bot.send_document(chat_id=user_id,
                                        document=BufferedInputFile(pdf_output.read(), filename="results.pdf"))
                await state.set_state(None)
                await state.set_state(CalculateProject.waiting_for_data)
                if 'RU' in user_languages.values():
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"Общая оценка проекта: \n{flags_answer}\n",
                    )
                    await bot.send_message(
                        chat_id=user_id,
                        text="Введите тикер следующего токена (например STRK, SUI) или введите /exit для завершения:",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"Overall project assessment: \n{flags_answer}\n",
                    )
                    await bot.send_message(
                        chat_id=user_id,
                        text="Enter the ticker of the next token (e.g. STRK, SUI) or enter /exit to complete:",
                        reply_markup=ReplyKeyboardRemove()
                    )
        else:
            logging.error("Не указан ни объект Message, ни user_id для отправки документа.")
    except ValueError as e:
        async with AiohttpSession() as session:
            bot = Bot(token=API_TOKEN, session=session)
            error_message = traceback.format_exc()
            if isinstance(message, Message):
                if 'RU' in user_languages.values():
                    await message.answer(
                        f"Ошибка: {str(e)} Подробности ошибки:\n{error_message}\nПожалуйста, убедитесь, что все данные введены корректно.")
                else:
                    await message.answer(
                        f"Error: {str(e)} Error details:\n{error_message}\nPlease make sure all data is entered correctly.")
            elif user_id is not None:
                if 'RU' in user_languages.values():
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"Ошибка: {str(e)} Подробности ошибки:\n{error_message}\nПожалуйста, убедитесь, что все данные введены корректно.",
                    )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"Error: {str(e)} Error details:\n{error_message}\nPlease make sure all data is entered correctly.",
                    )
