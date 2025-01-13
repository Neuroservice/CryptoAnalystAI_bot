import logging
import re
import textwrap
import traceback
from datetime import datetime
from io import BytesIO
from typing import Optional, Union

import fitz
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
    AgentAnswer
)
from bot.utils.consts import (
    tickers,
    field_mapping,
    model_mapping,
    checking_map,
    dejavu_path,
    logo_path, get_header_params, calculations_choices, async_session, session_local, dejavu_bold_path,
    dejavu_italic_path, patterns, ai_help_ru, ai_help_en, ai_link, ai_help_en_split, ai_help_ru_split,
    times_new_roman_path, times_new_roman_bold_path, times_new_roman_italic_path
)
from bot.utils.consts import user_languages
from bot.utils.gpt import (
    agent_handler
)
from bot.utils.keyboards.calculate_keyboards import analysis_type_keyboard
from bot.utils.metrics import (
    process_metrics,
    check_missing_fields
)
from bot.utils.metrics_evaluation import determine_project_tier, calculate_tokenomics_score, analyze_project_metrics, \
    calculate_project_score, project_investors_level
from bot.utils.project_data import (
    get_project_and_tokenomics,
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
    process_and_update_models, fetch_coingecko_data, generate_flags_answer, find_record, update_or_create,
    extract_text_with_formatting, extract_project_score
)
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user, phrase_by_language
from bot.utils.resources.files_worker.pdf_worker import PDF
from bot.utils.validations import validate_user_input, extract_overall_category, save_execute, extract_description, \
    extract_red_green_flags, extract_calculations, extract_old_calculations

calculate_router = Router()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CalculateProject(StatesGroup):
    choosing_analysis_type = State()
    choosing_file_format = State()
    waiting_for_data = State()
    waiting_for_basic_data = State()
    waiting_for_basic_results = State()
    waiting_for_excel = State()
    waiting_for_pdf = State()


@calculate_router.message(CalculateProject.waiting_for_pdf)
async def await_to_create_pdf(message: types.Message, state: FSMContext):
    await create_pdf(session_local, state, message)


@calculate_router.message(CalculateProject.waiting_for_basic_results)
async def await_basic_report(message: types.Message, state: FSMContext):
    await create_basic_report(session_local, state, message)


@calculate_router.message(lambda message: message.text == 'Анализ проектов' or message.text == 'Project analysis' or message.text == "Пожалуйста, выберите новый проект для расчета.")
async def project_chosen(message: types.Message, state: FSMContext):
    await message.answer(phrase_by_user("calculation_type_choice", message.from_user.id), reply_markup=analysis_type_keyboard(message.from_user.id))
    await state.set_state(CalculateProject.choosing_analysis_type)


@calculate_router.message(lambda message: message.text == 'Блок анализа цены на листинге (бета)' or message.text == 'Block of price analysis on the listing (beta)')
async def project_chosen(message: types.Message, state: FSMContext):
    await message.answer(phrase_by_user("beta_block", message.from_user.id), reply_markup=analysis_type_keyboard(message.from_user.id))


@calculate_router.message(CalculateProject.choosing_analysis_type)
async def analysis_type_chosen(message: types.Message, state: FSMContext):
    analysis_type = message.text.lower()

    if analysis_type in ['блок ребалансировки портфеля', 'block of portfolio rebalancing']:
        await message.answer(phrase_by_user("rebalancing_input_token", message.from_user.id))
        await state.set_state(CalculateProject.waiting_for_basic_data)

    elif analysis_type in ['блок анализа и оценки проектов', 'block of projects analysis and evaluation']:
        await message.answer(phrase_by_user("analysis_input_token", message.from_user.id))
        await state.set_state(CalculateProject.waiting_for_data)


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
    else:
        # Сообщаем пользователю, что будут производиться расчеты
        await message.answer(phrase_by_user("wait_for_calculations", message.from_user.id))

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
            await session_local.commit()
            session_local.refresh(calculation_record)

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

        data = {
            "user_coin_name": user_coin_name,
            "calculation_record": calculation_record.to_dict(),
            "category_answer": category_answer,
            "chosen_project": chosen_project_name,
            "new_project": new_project.to_dict(),
            "results": results,
            "agents_info": agents_info,
            "twitter_name": twitter_name,
        }
        await session_local.commit()

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
    language = 'RU' if user_languages.get(message.from_user.id) == 'RU' else 'ENG'

    if await validate_user_input(user_coin_name, message, state):
        return
    else:
        # Сообщаем пользователю, что будут производиться расчеты
        await message.answer(phrase_by_user("wait_for_calculations", message.from_user.id))

    twitter_name, description, lower_name = await get_twitter_link_by_symbol(user_coin_name)
    coin_description = await get_coin_description(lower_name)
    if description:
        coin_description += description

    category_answer = agent_handler("category", topic=coin_description, language=language)
    logging.info(f"category_answer: {category_answer}")
    overall_category = extract_overall_category(category_answer)
    token_description = extract_description(category_answer)
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

    print(network_metrics)

    if not base_project:
        await update_or_create(
            session_local, Project,
            defaults={
                'category': chosen_project,
                'coin_name': user_coin_name
            },
        )

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
        print("last_tvl: ", last_tvl)
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

    new_project = await process_metrics(session_local, user_coin_name, project, chosen_project, tasks, price,
                                        total_supply, fundraise, investors)

    if new_project:
        calculation_record = Calculation(
            user_id=message.from_user.id,
            project_id=new_project.id,
            date=datetime.now()
        )
        session_local.add(calculation_record)
        await session_local.commit()
        await session_local.refresh(calculation_record)

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
        "new_project": new_project.to_dict(),
        "calculation_record": calculation_record.to_dict(),
        "category_answer": category_answer,
        "project_category": overall_category,
        "token_description": token_description,
        "chosen_project": chosen_project,
        "twitter_name": twitter_name,
        "coin_name": user_coin_name,
        "price": price,
        "total_supply": total_supply
    }

    missing_fields, examples = check_missing_fields(metrics_data, checking_map)
    missing_fields_string = ', '.join(missing_fields)

    await session_local.commit()

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
            if investing_metrics and investing_metrics.fund_level:
                project_investors_level_result = project_investors_level(investors=investing_metrics.fund_level)
                investors_level = project_investors_level_result["level"]
                investors_level_score = project_investors_level_result["score"]
            else:
                investors_level = '-'
                investors_level_score = '-'

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
                round((market_metrics.growth_low - 100) * 100, 2) if market_metrics and market_metrics.growth_low else 'N/A',
                round(market_metrics.fail_high * 100, 2) if market_metrics and market_metrics.fail_high else 'N/A',
                manipulative_metrics.top_100_wallet * 100 if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A',
                (network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'
            )

            project_rating_result = calculate_project_score(
                investing_metrics.fundraise if investing_metrics and investing_metrics.fundraise else 'N/A',
                tier_answer,
                social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A',
                social_metrics.twitterscore if social_metrics and social_metrics.twitterscore else 'N/A',
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
                f"Социальные метрики: Количество подписчиков - {social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A'} (twitter link: {twitter_link}), Twitter Score - {social_metrics.twitterscore if social_metrics and social_metrics.twitterscore else 'N/A'}"
            )
            flags_answer = await generate_flags_answer(message.from_user.id if isinstance(message, Message) else user_id, async_session,
                                        all_data_string_for_flags_agent, user_languages, project, tokenomics_data, investing_metrics, social_metrics,
                                        funds_profit, market_metrics, manipulative_metrics, network_metrics, tier_answer, funds_answer, tokemonic_answer,
                                        comparison_results, category_answer, twitter_link, top_and_bottom, language)

            agent_answer_record = AgentAnswer(
                project_id=project.id,
                answer=flags_answer,
                language=language
            )
            session.add(agent_answer_record)

        else:
            flags_answer = existing_answer.answer

        existing_calculation = await find_record(Calculation, session, id=calculation_record["id"])
        existing_calculation.agent_answer = flags_answer
        session.add(existing_calculation)

        answer = comparison_results + "\n"
        answer += flags_answer
        answer = answer.replace('**', '').strip()

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
            async with AiohttpSession() as session:
                bot = Bot(token=API_TOKEN, session=session)
                await bot.send_message(chat_id=user_id, text=f"{phrase_by_user('error_not_valid_input_data', user_id)}\n{error_message}")


@save_execute
async def create_pdf(session, state: FSMContext, message: Optional[Union[Message, str]] = None, user_id: Optional[int] = None):
    state_data = await state.get_data()
    chosen_project = state_data.get("chosen_project")
    category_answer = state_data.get("category_answer")
    new_project = state_data.get("new_project")
    coin_name = state_data.get("coin_name")
    twitter_link = state_data.get("twitter_name")
    token_description = state_data.get("token_description")
    price = state_data.get("price")
    total_supply = state_data.get("total_supply")
    calculation_record = state_data.get("calculation_record")
    project_category = state_data.get("project_category")
    chosen_project_obj = await find_record(Project, session, coin_name=coin_name)
    user_input = message.text if isinstance(message, Message) else message
    row_data = []
    cells_content = None
    language = 'RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'
    coin_twitter, about, lower_name = twitter_link
    current_date = datetime.now().strftime("%d.%m.%Y")

    input_lines = user_input.split('\n')
    if user_input != '-':
        process_and_update_models(input_lines, field_mapping, model_mapping, session, new_project, chosen_project_obj)

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

        pdf = PDF(logo_path=logo_path, orientation='P')
        pdf.set_margins(left=20, top=10, right=20)
        pdf.add_page()
        pdf.add_font("TimesNewRoman", '', times_new_roman_path, uni=True)  # Обычный
        pdf.add_font("TimesNewRoman", 'B', times_new_roman_bold_path, uni=True)  # Жирный
        pdf.add_font("TimesNewRoman", 'I', times_new_roman_italic_path, uni=True)  # Курсив
        pdf.set_font("TimesNewRoman", size=8)

        project_info = await get_user_project_info(session, new_project["coin_name"])
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

        existing_answer = await find_record(AgentAnswer, session, project_id=project.id, language=('RU' if user_languages.get(user_id if not isinstance(message, Message) else message.from_user.id) == 'RU' else 'ENG'))

        comparison_results = ""
        result_index = 1


        for index, coin_name, project_coin, expected_x, fair_price in row_data:
            if project_coin != coin_name:
                if project_coin in tickers:
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

        all_data_string_for_funds_agent = (
            f"Распределение токенов: {funds_profit.distribution if funds_profit else 'N/A'}\n"
        )
        funds_agent_answer = agent_handler("funds_agent", topic=all_data_string_for_funds_agent)

        logging.info(f"funds_agent_answer: {funds_agent_answer, tokenomics_data.capitalization}")

        funds_answer, funds_scores, funds_score, growth_and_fall_score, top_100_score, tvl_score = analyze_project_metrics(
            funds_agent_answer,
            investing_metrics.fundraise if investing_metrics and investing_metrics.fundraise else 'N/A',
            tokenomics_data.total_supply if tokenomics_data and tokenomics_data.total_supply else 'N/A',
            basic_metrics.market_price if basic_metrics and basic_metrics.market_price else 'N/A',
            round((market_metrics.growth_low - 100) * 100, 2) if market_metrics and market_metrics.growth_low else 'N/A',
            round(market_metrics.fail_high * 100, 2) if market_metrics and market_metrics.fail_high else 'N/A',
            manipulative_metrics.top_100_wallet * 100 if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A',
            (network_metrics.tvl / tokenomics_data.capitalization) * 100 if network_metrics and tokenomics_data and tokenomics_data.capitalization and tokenomics_data.capitalization != 0 and network_metrics.tvl else 'N/A'
        )

        if investing_metrics and investing_metrics.fund_level:
            project_investors_level_result = project_investors_level(investors=investing_metrics.fund_level)
            investors_level = project_investors_level_result["level"]
            investors_level_score = project_investors_level_result["score"]
        else:
            investors_level = '-'
            investors_level_score = 0

        tier_answer = determine_project_tier(
            capitalization=tokenomics_data.capitalization if tokenomics_data else 'N/A',
            fundraising=investing_metrics.fundraise if investing_metrics else 'N/A',
            twitter_followers=social_metrics.twitter if social_metrics else 'N/A',
            twitter_score=social_metrics.twitterscore if social_metrics else 'N/A',
            category=project.category if project else 'N/A',
            investors=investing_metrics.fund_level if investing_metrics and investing_metrics.fund_level else 'N/A',
        )

        if existing_answer is None:
            data_for_tokenomics = []
            for index, coin_name, project_coin, expected_x, fair_price in row_data:
                ticker = project_coin
                growth_percent = expected_x
                data_for_tokenomics.append({ticker: {"growth_percent": growth_percent}})

            logging.info(f"data_for_tokenomics: {data_for_tokenomics}")
            tokemonic_answer, tokemonic_score = calculate_tokenomics_score(project.coin_name, data_for_tokenomics)

            project_rating_result = calculate_project_score(
                investing_metrics.fundraise if investing_metrics and investing_metrics.fundraise else 'N/A',
                f"Tier {investors_level}",
                social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A',
                social_metrics.twitterscore if social_metrics and social_metrics.twitterscore else 'N/A',
                tokemonic_score if tokemonic_answer else 'N/A',
                funds_scores if funds_scores else 'N/A'
            )

            project_rating_answer = project_rating_result["calculations_summary"]
            fundraising_score = project_rating_result["fundraising_score"]
            tier_score = project_rating_result["tier_score"]
            followers_score = project_rating_result["followers_score"]
            twitter_engagement_score = project_rating_result["twitter_engagement_score"]
            tokenomics_score = project_rating_result["tokenomics_score"]
            profitability_score = project_rating_result["profitability_score"]
            preliminary_score = project_rating_result["preliminary_score"]
            tier_coefficient = project_rating_result["tier_coefficient"]
            overal_final_score = project_rating_result["final_score"]
            project_rating_text = project_rating_result["project_rating"]
            project_score = overal_final_score
            project_rating = project_rating_text


            all_data_string_for_flags_agent = (
                f"Проект: {project.category}\n"
                f"Category agent answer: {category_answer}\n",
                f"Tier agent: {tier_answer}\n",
                f"Tokemonic agent: {tokemonic_answer}\n",
                f"Funds agent: {funds_answer}\n",
                f"Project rating agent: {project_rating_answer}\n"
                f"Социальные метрики: Количество подписчиков - {social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A'} (twitter link: {twitter_link}), Twitter Score - {social_metrics.twitterscore if social_metrics and social_metrics.twitterscore else 'N/A'}"
            )
            flags_answer = await generate_flags_answer(message.from_user.id if isinstance(message, Message) else user_id, async_session,
                                        all_data_string_for_flags_agent, user_languages, project, tokenomics_data, investing_metrics, social_metrics,
                                        funds_profit, market_metrics, manipulative_metrics, network_metrics, tier_answer, funds_answer, tokemonic_answer,
                                        comparison_results, category_answer, twitter_link, top_and_bottom, language)
            answer = f"Итоговое общее количество баллов проекта: {project_rating_result['final_score']} ()"
            answer += flags_answer
            answer = answer.replace('**', '')
            answer += "**Данные для анализа токеномики**:\n" + comparison_results
            answer = re.sub(r'\n\s*\n', '\n', answer)

            flags_answer = answer

            red_green_flags = extract_red_green_flags(answer, language)
            calculations = extract_calculations(answer, language)

            if top_and_bottom and top_and_bottom.lower_threshold and top_and_bottom.upper_threshold:
                top_and_bottom_answer = phrase_by_user(
                    'top_bottom_values',
                    message.from_user.id if isinstance(message, Message) else user_id,
                    current_value=round(basic_metrics.market_price, 4),
                    min_value=round(top_and_bottom.lower_threshold, 4),
                    max_value=round(top_and_bottom.upper_threshold, 4)
                )
            else:
                top_and_bottom_answer = phrase_by_user(
                    'top_bottom_values',
                    message.from_user.id if isinstance(message, Message) else user_id,
                    current_value=round(basic_metrics.market_price, 4),
                    min_value="Нет данных",
                    max_value="Нет данных"
                )

            capitalization = float(tokenomics_data.capitalization) if tokenomics_data and tokenomics_data.capitalization else ('Нет данных' if language == 'RU' else 'No info')
            fundraising_amount = float(investing_metrics.fundraise) if investing_metrics and investing_metrics.fundraise else ('Нет данных' if language == 'RU' else 'No info')
            investors_percent = float(funds_agent_answer.strip('%')) / 100

            if isinstance(capitalization, float) and isinstance(fundraising_amount, float):
                result_ratio = (capitalization * investors_percent) / fundraising_amount
                final_score = f"{result_ratio:.2%}"
            else:
                result_ratio = 'Нет данных' if language == 'RU' else 'No info'
                final_score = result_ratio

            profit_text = phrase_by_user(
                "investor_profit_text",
                user_id=message.from_user.id if isinstance(message, Message) else user_id,
                capitalization=f"{capitalization:,.2f}" if isinstance(capitalization, float) else capitalization,
                investors_percent=f"{investors_percent:.0%}" if isinstance(investors_percent, float) else investors_percent,
                fundraising_amount=f"{fundraising_amount:,.2f}" if isinstance(fundraising_amount, float) else fundraising_amount,
                result_ratio=f"{result_ratio:.4f}" if isinstance(result_ratio, float) else result_ratio,
                final_score=final_score
            )

            if funds_profit and funds_profit.distribution:
                distribution_items = funds_profit.distribution.split('\n')
                formatted_distribution = "\n".join([f"- {item}" for item in distribution_items])
            else:
                formatted_distribution = 'Нет данных по распределению токенов' if language == 'RU' else 'No token distribution data'

            formatted_metrics = [
                f"- {'Капитализация проекта' if language == 'RU' else 'Project capitalization'}: ${round(tokenomics_data.capitalization, 0)}"
                if tokenomics_data and tokenomics_data.capitalization else (
                    "- Капитализация проекта: Нет данных" if language == 'RU' else "- Project capitalization: No info"
                ),
                f"- {'Полная капитализация проекта (FDV)' if language == 'RU' else 'Fully Diluted Valuation (FDV)'}: ${round(tokenomics_data.fdv, 0)}"
                if tokenomics_data and tokenomics_data.fdv else (
                    "- Полная капитализация проекта (FDV): Нет данных" if language == 'RU' else "- Fully Diluted Valuation (FDV): No info"
                ),
                f"- {'Общее количество токенов (Total Supply)' if language == 'RU' else 'Total Supply'}: {round(tokenomics_data.total_supply, 0)}"
                if tokenomics_data and tokenomics_data.total_supply else (
                    "- Общее количество токенов (Total Supply): Нет данных" if language == 'RU' else "- Total Supply: No info"
                ),
                f"- {'Сумма сбора средств от инвесторов (Fundraising)' if language == 'RU' else 'Fundraising'}: ${round(investing_metrics.fundraise, 0)}"
                if investing_metrics and investing_metrics.fundraise else (
                    "- Сумма сбора средств от инвесторов (Fundraising): Нет данных" if language == 'RU' else "- Fundraising: No info"
                ),
                f"- {'Количество подписчиков на Twitter' if language == 'RU' else 'Twitter followers'} ({twitter_link[0]}): {social_metrics.twitter}"
                if social_metrics and social_metrics.twitter else (
                    "- Количество подписчиков на Twitter: Нет данных" if language == 'RU' else "- Twitter followers: No info"
                ),
                f"- {'Twitter Score'}: {social_metrics.twitterscore}"
                if social_metrics and social_metrics.twitterscore else (
                    "- Twitter Score: Нет данных" if language == 'RU' else "- Twitter Score: No info"
                ),
                f"- {'Общая стоимость заблокированных активов (TVL)' if language == 'RU' else 'Total Value Locked (TVL)'}: ${round(network_metrics.tvl, 0)}"
                if network_metrics and network_metrics.tvl else (
                    "- Общая стоимость заблокированных активов (TVL): Нет данных" if language == 'RU' else "- Total Value Locked (TVL): No info"
                ),
                f"- {'Процент нахождения токенов на топ 100 кошельков блокчейна' if language == 'RU' else 'Percentage of tokens on top 100 wallets'}: {round(manipulative_metrics.top_100_wallet * 100, 2)}%"
                if manipulative_metrics and manipulative_metrics.top_100_wallet else (
                    "- Процент нахождения токенов на топ 100 кошельков блокчейна: Нет данных" if language == 'RU' else "- Percentage of tokens on top 100 wallets: No info"
                ),
                f"- {'Инвесторы' if language == 'RU' else 'Investors'}: {investing_metrics.fund_level}"
                if investing_metrics and investing_metrics.fund_level else (
                    "- Инвесторы: Нет данных" if language == 'RU' else "- Investors: No info"
                ),
            ]

            formatted_metrics_text = "\n".join(formatted_metrics)
            project_evaluation = phrase_by_user(
      "project_rating_details",
                user_id,
                fundraising_score=int(fundraising_score),
                tier=investors_level,
                tier_score=investors_level_score,
                followers_score=int(followers_score),
                twitter_engagement_score=int(twitter_engagement_score),
                tokenomics_score=tokenomics_score,
                profitability_score=round(funds_score, 2),
                preliminary_score=int(growth_and_fall_score),
                top_100_percent=round(manipulative_metrics.top_100_wallet * 100, 2) if manipulative_metrics and manipulative_metrics.top_100_wallet else 0,
                tvl_percent=int((network_metrics.tvl / tokenomics_data.capitalization) * 100) if network_metrics.tvl and tokenomics_data.total_supply else 0,
                tier_coefficient=tier_coefficient,
            )

            pdf.set_font("TimesNewRoman", size=12)
            pdf.cell(0, 6,
                     f"{'Анализ проекта' if language == 'RU' else 'Project analysis'} {lower_name.capitalize()} (${coin_name.upper()})",
                     0, 1, 'L')
            pdf.cell(0, 6, f"{current_date}", 0, 1, 'L')

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.cell(0, 6, f"{'Описание проекта' if language == 'RU' else 'Project description'}:", 0, 1, 'L')
            pdf.set_font("TimesNewRoman", size=12)
            pdf.ln(0.1)
            pdf.multi_cell(0, 6, token_description, 0)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.cell(0, 6,
                     f"{'Проект относится к категории' if language == 'RU' else 'The project is categorized as'}:", 0,
                     1, 'L')
            pdf.set_font("TimesNewRoman", size=12)
            pdf.multi_cell(0, 6, chosen_project, 0)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.multi_cell(0, 6,
                           f"{f'Метрики проекта (уровень {tier_answer})' if language == 'RU' else f'Project metrics (level {tier_answer})'}:",
                           0)
            pdf.set_font("TimesNewRoman", size=12)
            pdf.ln(0.1)
            pdf.multi_cell(0, 6, formatted_metrics_text, 0)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.multi_cell(0, 6, f"{'Распределение токенов' if language == 'RU' else 'Token distribution'}:", 0)
            pdf.set_font("TimesNewRoman", size=12)
            pdf.ln(0.1)
            pdf.multi_cell(0, 6, formatted_distribution, 0)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.multi_cell(0, 6,
                           f"{phrase_by_user('funds_profit_scores', message.from_user.id if isinstance(message, Message) else user_id)}:",0)
            pdf.set_font("TimesNewRoman", size=12)
            pdf.ln(0.1)
            pdf.multi_cell(0, 6, profit_text, 0)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.multi_cell(0, 6,
                           f"{phrase_by_user('top_bottom_2_years', message.from_user.id if isinstance(message, Message) else user_id)}",
                           0)
            pdf.set_font("TimesNewRoman", size=12)
            pdf.ln(0.1)
            pdf.multi_cell(0, 6, top_and_bottom_answer, 0)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.cell(0, 6,
                     f"{phrase_by_user('comparing_calculations', message.from_user.id if isinstance(message, Message) else user_id)}",
                     0, 1, 'L')
            pdf.set_font("TimesNewRoman", size=12)
            pdf.ln(0.1)
            pdf.multi_cell(0, 6, calculations, 0)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.cell(0, 6, f"{f'Оценка проекта:' if language == 'RU' else f'Overall evaluation:'}",0, 0, 'L')
            pdf.set_font("TimesNewRoman", size=12)
            pdf.ln(0.1)
            pdf.multi_cell(0, 6, project_evaluation, 0)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.cell(0, 6,
                     f"{f'Общая оценка проекта {overal_final_score} баллов ({project_rating_text})' if language == 'RU' else f'Overall project evaluation {overal_final_score} points ({project_rating_text})'}",0, 1, 'L')
            pdf.set_font("TimesNewRoman", size=12)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='B', size=12)
            pdf.cell(0, 6, f"{'«Ред» флаги и «грин» флаги' if language == 'RU' else '«Red» flags and «green» flags'}:",
                     0, 1, 'L')
            pdf.set_font("TimesNewRoman", size=12)
            pdf.multi_cell(0, 6, red_green_flags, 0)

            pdf.ln(6)

            pdf.set_font("TimesNewRoman", style='I', size=12)
            pdf.multi_cell(0, 6,
                           f"***{phrase_by_user('ai_help', message.from_user.id if isinstance(message, Message) else user_id)}",
                           0)
            pdf.ln(0.1)
            pdf.set_font("TimesNewRoman", size=12, style='IU')
            pdf.set_text_color(0, 0, 255)  # Синий цвет для ссылки
            pdf.cell(0, 6, "https://t.me/FasolkaAI_bot", 0, 1, 'L', link="https://t.me/FasolkaAI_bot")
            pdf.set_font("TimesNewRoman", size=12)

        else:
            flags_answer = existing_answer.answer

            if language == "RU":
                match = re.search(r"Общая оценка проекта\s*([\d.]+)\s*баллов?\s*\((.+?)\)", flags_answer)
            else:
                match = re.search(r"Overall project evaluation\s*([\d.]+)\s*points\s*\((.+?)\)", flags_answer)

            if match:
                project_score = float(match.group(1))  # Извлекаем баллы
                project_rating = match.group(2)  # Извлекаем оценку
                print(f"Итоговые баллы: {project_score}")
                print(f"Оценка проекта: {project_rating}")
            else:
                project_score = "Данных по баллам не поступило" if language == "RU" else "No data on scores were received"
                project_rating = "Нет данных по оценке баллов проекта" if language == "RU" else "No data available on project scoring"
                print("Не удалось найти итоговые баллы и/или оценку.")

            selected_patterns = patterns["RU"] if language == "RU" else patterns["EN"]

            # Обработка текста для PDF
            text_to_parse = flags_answer  # Исходный текст для обработки

            # Добавление в PDF
            pdf.set_font("TimesNewRoman", size=12)
            pdf.cell(0, 6, f"{'Анализ проекта' if language == 'RU' else 'Project analysis'}", 0, 1, 'L')
            pdf.cell(0, 6, current_date, 0, 1, 'L')
            pdf.ln(6)

            for pattern in selected_patterns:
                match = re.search(pattern, text_to_parse, re.IGNORECASE | re.DOTALL)

                if match:
                    # Проверка извлеченных данных
                    start, end = match.span()
                    header = match.group(1)

                    # Извлекаем содержимое под заголовком
                    content_start = end
                    next_header_match = None
                    for next_pattern in selected_patterns:
                        next_header_match = re.search(next_pattern, text_to_parse[end:], re.IGNORECASE)
                        if next_header_match:
                            break

                    content_end = next_header_match.start() + end if next_header_match else len(text_to_parse)
                    content = text_to_parse[content_start:content_end].strip()

                    if re.search(ai_help_ru, content, re.DOTALL):
                        parts = re.split(ai_help_ru_split, content, maxsplit=1)
                        before_text = parts[0].strip()

                        # Добавляем заголовок жирным
                        pdf.set_font("TimesNewRoman", style="B", size=12)
                        pdf.multi_cell(0, 6, header, 0)

                        pdf.ln(0.1)

                        # Обычный текст до фразы
                        pdf.set_font("TimesNewRoman", size=12)
                        if header == "«Ред» флаги и «грин» флаги:":
                            lines = before_text.splitlines()
                            cleaned_lines = []
                            for line in lines:
                                stripped_line = " ".join(line.split())  # Убираем лишние пробелы внутри строки
                                if stripped_line.startswith("-"):  # Если строка начинается с пункта списка
                                    cleaned_lines.append(stripped_line)
                                elif cleaned_lines and not cleaned_lines[-1].endswith(
                                        ":"):  # Присоединяем к предыдущей строке
                                    cleaned_lines[-1] += f" {stripped_line}"
                                else:
                                    cleaned_lines.append(stripped_line)
                            before_text = "\n".join(cleaned_lines)

                        if "Отрицательные характеристики:" in before_text:
                            before_text = before_text.replace("Отрицательные характеристики:","\nОтрицательные характеристики:")

                        pdf.multi_cell(0, 6, before_text, 0)

                        pdf.ln(0.1)

                        # Текст с курсивом (фраза и ссылка)
                        pdf.set_font("TimesNewRoman", style="I", size=12)
                        pdf.multi_cell(0, 6,f"\n\n***Если Вам не понятна терминология, изложенная в отчете, Вы можете воспользоваться нашим ИИ консультантом.",0)
                        pdf.ln(0.1)
                        # Устанавливаем цвет для ссылки (синий)
                        pdf.set_text_color(0, 0, 255)
                        pdf.multi_cell(0, 6, "https://t.me/FasolkaAI_bot", 0)

                        # Возвращаем цвет текста к обычному черному
                    elif re.search(ai_help_en, content, re.DOTALL):
                        parts = re.split(ai_help_en_split, content, maxsplit=1)
                        before_text = parts[0].strip()

                        pdf.set_font("DejaVu", style="B", size=12)
                        pdf.multi_cell(0, 6, header, 0)

                        pdf.ln(0.1)

                        # Обычный текст до фразы
                        pdf.set_font("TimesNewRoman", size=12)
                        if header == "«Red» flags and «green» flags:":
                            lines = before_text.splitlines()
                            cleaned_lines = []
                            for line in lines:
                                stripped_line = " ".join(line.split())  # Убираем лишние пробелы внутри строки
                                print("stripped_line: ", stripped_line)
                                if stripped_line.startswith("-"):  # Если строка начинается с пункта списка
                                    cleaned_lines.append(stripped_line)
                                elif cleaned_lines and not cleaned_lines[-1].endswith(
                                        ":"):  # Присоединяем к предыдущей строке
                                    cleaned_lines[-1] += f" {stripped_line}"
                                else:
                                    cleaned_lines.append(stripped_line)
                            before_text = "\n".join(cleaned_lines)

                        if "Negative Characteristics:" in before_text:
                            before_text = before_text.replace("Negative Characteristics:","\nNegative Characteristics:")

                        pdf.multi_cell(0, 6, before_text, 0)

                        pdf.ln(0.1)

                        # Текст с курсивом (фраза и ссылка)
                        pdf.set_font("TimesNewRoman", style="I", size=12)
                        # Сначала выводим обычный текст
                        pdf.multi_cell(0, 6,f"\n\n***If you do not understand the terminology in the report, you can use our AI consultant.",0)
                        pdf.ln(0.1)
                        # Устанавливаем цвет для ссылки (синий)
                        pdf.set_text_color(0, 0, 255)
                        pdf.multi_cell(0, 6, "https://t.me/FasolkaAI_bot", 0)

                        # Возвращаем цвет текста к обычному черному
                        pdf.set_text_color(0, 0, 0)
                    else:
                        # Добавляем заголовок жирным
                        pdf.set_font("TimesNewRoman", style="B", size=12)
                        pdf.multi_cell(0, 6, header, 0)

                        pdf.ln(0.1)

                        # Добавляем основной текст
                        pdf.set_font("TimesNewRoman", size=12)
                        content_cleaned = content
                        if header in ["Описание проекта:", "Оценка прибыльности инвесторов:", "Project description:", "Evaluating investor profitability:", ]:
                            content_cleaned = " ".join(content.split())

                        content_cleaned = extract_old_calculations(content_cleaned, language)
                        pdf.multi_cell(0, 6, content_cleaned, 0)

                        pdf.ln(6)

        pdf_output = BytesIO()
        pdf.output(pdf_output)

        # Сбросим указатель на начало
        pdf_output.seek(0)

        pdf_data = pdf_output.read()

        pdf_output.seek(0)

        if not existing_answer or (existing_answer and not existing_answer.answer):
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            extracted_text = "".join([page.get_text("text") for page in doc])

            new_answer = AgentAnswer(
                project_id=project.id,
                answer=extracted_text,
                language=language
            )
            session.add(new_answer)

        existing_calculation = await find_record(Calculation, session, id=calculation_record["id"])
        existing_calculation.agent_answer = flags_answer
        session.add(existing_calculation)

        await session.commit()

        if isinstance(message, Message):
            await message.send_message(
                chat_id=user_id,
                text=phrase_by_language("project_analysis_result", language).format(
                    lower_name=lower_name.capitalize(),
                    project_score=project_score,
                    project_rating=project_rating
                ),
                reply_markup=ReplyKeyboardRemove()
            )

            await message.answer_document(BufferedInputFile(pdf_output.read(), filename="results.pdf"))
            await message.send_message(chat_id=user_id, text=phrase_by_user("input_next_token_for_analysis", message.from_user.id), reply_markup=ReplyKeyboardRemove())

            # Очищаем состояние и устанавливаем новое состояние на ожидание ввода нового токена
            await state.set_state(None)
            await state.set_state(CalculateProject.waiting_for_data)

        elif user_id is not None:
            async with AiohttpSession() as session:
                bot = Bot(token=API_TOKEN, session=session)

                await bot.send_message(
                    chat_id=user_id,
                    text=phrase_by_language("project_analysis_result", language).format(
                        lower_name=lower_name.capitalize(),
                        project_score=project_score,
                        project_rating=project_rating
                    ),
                    reply_markup=ReplyKeyboardRemove()
                )
                await bot.send_document(chat_id=user_id, document=BufferedInputFile(pdf_output.read(), filename="results.pdf"))
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

