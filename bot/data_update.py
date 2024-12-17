import datetime
import logging
import traceback
from typing import Type, Any

from itypes import Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Project,
    Tokenomics,
    BasicMetrics,
    InvestingMetrics,
    ManipulativeMetrics,
    NetworkMetrics,
    FundsProfit,
    AgentAnswer
)
from bot.utils.consts import tickers, project_types, get_header_params, SessionLocal, sync_session
from bot.utils.gpt import agent_handler
from bot.utils.project_data import (
    get_twitter_link_by_symbol,
    fetch_top_100_wallets,
    fetch_tvl_data,
    get_percantage_data,
    get_user_project_info,
    get_project_and_tokenomics,
    calculate_expected_x,
    get_top_projects_by_capitalization, fetch_coinmarketcap_data, fetch_coingecko_data
)

logging.basicConfig(level=logging.INFO)
current_day = datetime.datetime.utcnow().day


async def fetch_project(symbol: str, async_session: AsyncSession):
    async with async_session.begin():
        result = await async_session.execute(
            select(Project).filter_by(coin_name=symbol)
        )
        project = result.scalars().first()
        return project


async def fetch_crypto_data():
    """
    Асинхронный эндпоинт для получения данных о криптопроектах.
    """
    try:
        for project_type in project_types:
            # Получение топовых проектов
            symbols = await get_top_projects_by_capitalization(project_type, tickers)

            if not symbols:
                logging.info(f"No projects found for type: {project_type}")
                continue

            print("0")
            for symbol in symbols:
                async with SessionLocal() as async_session:
                    try:
                        # ШАГ 1: Получение данных проекта
                        print("1")
                        project = await fetch_project(symbol, async_session)

                        if not project:
                            logging.error(f"Project not found for {symbol}")
                            continue
                        header_params = get_header_params(symbol)

                        # ШАГ 2: Получение данных с CoinMarketCap
                        print("2")
                        data = await fetch_coinmarketcap_data(user_coin_name=symbol, **header_params)

                        if not data:
                            # Если данные с CoinMarketCap не получены, пробуем получить данные с CoinGecko
                            logging.info(f"Trying to fetch data from CoinGecko for {symbol}")
                            data = await fetch_coingecko_data(symbol)

                        print("2.1")
                        if not data or not isinstance(data, dict):
                            logging.error(f"Invalid data returned for {symbol}: {data}")
                            continue

                        # Проверка формата данных
                        expected_keys = {'coin_name', 'circulating_supply', 'total_supply', 'price', 'capitalization', 'coin_fdv'}
                        if not all(key in data for key in expected_keys):
                            logging.warning(f"Missing required keys in data for {symbol}: {data}")
                            continue

                        print("2.3")
                        coin_data = data
                        circulating_supply = coin_data.get('circulating_supply')
                        total_supply = coin_data.get('total_supply')
                        price = coin_data.get('price')
                        market_cap = coin_data.get('capitalization')
                        fdv = coin_data.get('coin_fdv')

                        # ШАГ 3: Обновление Tokenomics
                        print("3")
                        tokenomics = await async_session.execute(
                            select(Tokenomics).filter_by(project_id=project.id)
                        )
                        tokenomics = tokenomics.scalars().first()

                        if not tokenomics:
                            tokenomics = Tokenomics(
                                project_id=project.id,
                                circ_supply=circulating_supply,
                                total_supply=total_supply,
                                capitalization=market_cap,
                                fdv=fdv,
                            )
                        else:
                            tokenomics.circ_supply = circulating_supply
                            tokenomics.total_supply = total_supply
                            tokenomics.capitalization = market_cap
                            tokenomics.fdv = fdv

                        async_session.add(tokenomics)

                        # ШАГ 4: Обновление BasicMetrics
                        print("4")
                        basic_metrics = await async_session.execute(
                            select(BasicMetrics).filter_by(project_id=project.id)
                        )
                        basic_metrics = basic_metrics.scalars().first()

                        if not basic_metrics:
                            basic_metrics = BasicMetrics(
                                project_id=project.id,
                                market_price=round(float(price), 4)
                            )
                        else:
                            basic_metrics.market_price = round(float(price), 4)

                        async_session.add(basic_metrics)

                        # ШАГ 5: Обновление ManipulativeMetrics и других метрик
                        print("5")
                        investing_metrics = await async_session.execute(
                            select(InvestingMetrics).filter_by(project_id=project.id)
                        )
                        investing_metrics = investing_metrics.scalars().first()

                        manipulative_metrics = await async_session.execute(
                            select(ManipulativeMetrics).filter_by(project_id=project.id)
                        )
                        manipulative_metrics = manipulative_metrics.scalars().first()

                        if manipulative_metrics and investing_metrics:
                            fundraise = investing_metrics.fundraise
                            top_100_wallets = await fetch_top_100_wallets(symbol.lower())
                            if top_100_wallets and fdv and fundraise:
                                await update_or_create(
                                    async_session, ManipulativeMetrics,
                                    project_id=project.id,
                                    defaults={
                                        'fdv_fundraise': fdv / fundraise,
                                        'top_100_wallet': top_100_wallets,
                                    },
                                )

                        # ШАГ 6: Обновление NetworkMetrics (TVL)
                        print("6")
                        twitter_name, description, lower_name = await get_twitter_link_by_symbol(symbol)
                        tvl = await fetch_tvl_data(lower_name)
                        if tvl and fdv:
                            await update_or_create(
                                async_session, NetworkMetrics,
                                project_id=project.id,
                                defaults={
                                    'tvl': tvl,
                                    'tvl_fdv': tvl / fdv,
                                },
                            )

                        # ШАГ 7: Обновление FundsProfit
                        print("7")
                        funds_profit = await async_session.execute(
                            select(FundsProfit).filter_by(project_id=project.id).limit(1)
                        )
                        funds_profit = funds_profit.scalars().first()

                        if not funds_profit or not funds_profit.distribution or funds_profit.distribution == '-':
                            print("7.1")
                            twitter_link, description, lower_name = await get_twitter_link_by_symbol(symbol)
                            print(twitter_link, description, lower_name)
                            tokenomics_percentage_data = await get_percantage_data(twitter_link, symbol)
                            print(tokenomics_percentage_data)
                            output_string = '\n'.join(tokenomics_percentage_data) if tokenomics_percentage_data else '-'
                            print("output_string: ", output_string)
                            await update_or_create(
                                async_session, FundsProfit,
                                project_id=project.id,
                                defaults={'distribution': output_string},
                            )

                        # Сохранение изменений
                        print("8")
                        await async_session.commit()

                    except Exception as error:
                        logging.error(f"Error processing {symbol}: {error}")
                        await async_session.rollback()  # Откат транзакции при ошибке

        return {"status": "Data fetching completed"}
    except Exception as e:
        logging.error(f"Critical error in fetch_crypto_data: {e}")
        logging.error(f"Exception type: {type(e).__name__}")
        logging.error("Traceback:")
        logging.error(traceback.format_exc())  # Логирует весь стек вызовов
        return {"status": "Error", "message": str(e)}


async def update_agent_answers():
    async with SessionLocal() as async_session:
        current_time = datetime.datetime.utcnow()
        three_days_ago = current_time - datetime.timedelta(days=3)
        agents_info = []

        stmt = select(AgentAnswer).where(AgentAnswer.updated_at <= three_days_ago)
        result = await async_session.execute(stmt)
        outdated_answers = result.scalars().all()

        for answer in outdated_answers:
            project_stmt = select(Project).filter(Project.id == answer.project_id)
            project_result = await async_session.execute(project_stmt)
            project = project_result.scalars().first()

            if not project:
                continue

            project_info = await get_user_project_info(async_session, project.coin_name)
            twitter_link = await get_twitter_link_by_symbol(project.coin_name)
            tokenomics_data = project_info.get("tokenomics_data")
            basic_metrics = project_info.get("basic_metrics")
            investing_metrics = project_info.get("investing_metrics")
            social_metrics = project_info.get("social_metrics")
            funds_profit = project_info.get("funds_profit")
            market_metrics = project_info.get("market_metrics")
            manipulative_metrics = project_info.get("manipulative_metrics")
            network_metrics = project_info.get("network_metrics")
            projects, tokenomics_data_list = await get_project_and_tokenomics(async_session, project.category, project.coin_name)
            top_projects = sorted(
                tokenomics_data_list,
                key=lambda item: item[1][0].capitalization if item[1][0].capitalization else 0,
                reverse=True
            )[:5]

            for index, (top_projects, tokenomics_data) in enumerate(top_projects, start=1):
                for tokenomics in tokenomics_data:
                    calculation_result = calculate_expected_x(
                        entry_price=basic_metrics.market_price,
                        total_supply=tokenomics_data[0].total_supply,
                        fdv=tokenomics.fdv,
                    )

                    fair_price = calculation_result['fair_price']
                    fair_price = f"{fair_price:.5f}" if isinstance(fair_price, (
                    int, float)) else "Ошибка в расчетах" if answer.language == 'RU' else "Error on market"

                    agents_info.append([
                        index,
                        project.coin_name,
                        project.category,
                        (calculation_result['expected_x'] - 1.0) * 100,
                        fair_price
                    ])

            all_data_string_for_tier_agent = (
                f"Тикер монеты: {project.coin_name if project else 'N/A'}\n"
                f"Категория: {project.category if project else 'N/A'}\n"
                f"Капитализация: {tokenomics_data[0].capitalization if tokenomics_data else 'N/A'}\n"
                f"Сумма сбора средств от инвесторов (Fundraising): {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"Количество подписчиков на Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"Twitter Score: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"Инвесторы: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n"
            )

            comparison_results = ""
            for index, coin_name, project_name, expected_x, fair_price in agents_info:
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
                f"Тикер монеты: {project.coin_name if project else 'N/A'}\n"
                f"Доходность фондов (%): {funds_profit.distribution if funds_profit else 'N/A'}\n"
                f"Рост токена с минимальных значений (%): {market_metrics.growth_low if market_metrics else 'N/A'}\n"
                f"Падение токена от максимальных значений (%): {market_metrics.fail_high if market_metrics else 'N/A'}\n"
                f"Процент монет на топ 100 кошельков (%): {manipulative_metrics.top_100_wallet * 100 if manipulative_metrics else 'N/A'}\n"
                f"Процент заблокированных токенов (%): {(network_metrics.tvl / tokenomics_data[0].capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'}\n\n"
            )

            tier_answer = agent_handler("tier_agent", topic=all_data_string_for_tier_agent)
            tokemonic_answer = agent_handler("tokemonic_agent", topic=all_data_string_for_tokemonic_agent)
            funds_answer = agent_handler("funds_agent", topic=all_data_string_for_funds_agent)

            all_data_string_for_project_rating_agent = (
                f"Сумма сбора средств от инвесторов (Fundraising): {investing_metrics.fundraise if investing_metrics else 'N/A'}\n",
                f"Тир проекта: {tier_answer}\n",
                f"Количество подписчиков на Twitter: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"Twitter Score: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"Оценка токемоники (нужна общая оценка проекта в баллах): {tokemonic_answer if tokemonic_answer else 'N/A'}\n"
                f"Оценка прибыльности фондов: {funds_answer if funds_answer else 'N/A'}\n"
            )
            project_rating_answer = agent_handler("rating", topic=all_data_string_for_project_rating_agent)

            all_data_string_for_flags_agent = (
                f"Project: {project.category}\n"
                f"Ticker: {project.coin_name}\n"
                f"Tier agent: {tier_answer}\n",
                f"Tokemonic agent: {tokemonic_answer}\n",
                f"Funds agent: {funds_answer}\n",
                f"Project rating agent: {project_rating_answer}\n"
                f"Social metrics: Количество подписчиков - {social_metrics.twitter} (twitter link: {twitter_link}), Twitter Score - {social_metrics.twitterscore}"
                f"Данные для расчета: {project_rating_answer}\n"
                f"**Additional Data Used for Calculations**\n"
                f"- Project Name: {project.coin_name if project else 'N/A'}\n"
                f"- Category: {project.category if project else 'N/A'}\n"
                f"- Capitalization: {tokenomics_data[0].capitalization if tokenomics_data else 'N/A'}\n"
                f"- Fundraising: {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"- Investors Tier: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n"
                f"- Project Name: {project.coin_name if project else 'N/A'}\n"
                f"- **Calculation Inputs**\n"
                f"  - Profitability of Funds (%): {funds_profit.distribution if funds_profit else 'N/A'}\n"
                f"  - Token Growth from Low (%): {market_metrics.growth_low if market_metrics else 'N/A'}\n"
                f"  - Token Drop from High (%): {market_metrics.fail_high if market_metrics else 'N/A'}\n"
                f"  - Top 100 Wallets (%): {manipulative_metrics.top_100_wallet * 100 if manipulative_metrics else 'N/A'}\n"
                f"  - Locked Tokens (%): {(network_metrics.tvl / tokenomics_data[0].capitalization) * 100 if network_metrics and tokenomics_data else 'N/A'}\n\n"
                f"- Fundraising Amount: {investing_metrics.fundraise if investing_metrics else 'N/A'}\n"
                f"- Project Tier: {tier_answer}\n"
                f"- Twitter Followers: {social_metrics.twitter if social_metrics else 'N/A'}\n"
                f"- Twitter Score: {social_metrics.twitterscore if social_metrics else 'N/A'}\n"
                f"- Tokemomic Assessment (Overall Project Score): {tokemonic_answer if tokemonic_answer else 'N/A'}\n"
                f"- Funds Profitability Assessment: {funds_answer if funds_answer else 'N/A'}\n"
            )
            flags_answer = agent_handler("flags", topic=all_data_string_for_flags_agent,
                                         language=f"{'русский' if answer.language == 'RU' else 'english'}")

            answer.answer = flags_answer
            answer.updated_at = current_time
            async_session.add(answer)
            await async_session.commit()


async def find_record(model, session: AsyncSession, **filters):
    query = select(model).filter_by(**filters)
    result = await session.execute(query)
    record = result.scalars().first()

    if record is None:
        return None
    return record


async def find_records(model, session: AsyncSession, **filters):
    query = select(model).filter_by(**filters)
    result = await session.execute(query)
    records = result.scalars().all()

    if records is None:
        return None
    return records


def map_data_to_model_fields(model_name, data):
    """
    Сопоставляет данные из results полям модели.

    :param model_name: Название модели.
    :param data: Кортеж или список данных из results.
    :return: Словарь с данными для записи в модель.
    """
    if model_name == "market_metrics":
        return {
            "fail_high": data[0],
            "growth_low": data[1]
        }
    elif model_name == "top_and_bottom":
        return {
            "upper_threshold": data[0],
            "lower_threshold": data[1]
        }
    elif model_name == "investing_metrics":
        return {
            "fundraise": data[0],
            "fund_level": data[1]
        }
    elif model_name == "social_metrics":
        return {
            "twitter": data[0],
            "twitterscore": data[1]
        }
    elif model_name == "funds_profit":
        return {
            "distribution": data[0]
        }
    elif model_name == "manipulative_metrics":
        return {
            "top_100_wallet": data[0]
        }
    elif model_name == "network_metrics":
        return {
            "tvl": data[0]
        }
    logging.warning(f"Не задано сопоставление для модели {model_name}")
    return None


async def update_or_create(session, model, project_id=None, id=None, defaults=None, **kwargs):
    """ Вспомогательная функция для обновления или создания записи. """
    instance = None

    if id:
        result = await session.execute(select(model).filter_by(id=id))
        instance = result.scalars().first()
    else:
        result = await session.execute(select(model).filter_by(project_id=project_id))
        instance = result.scalars().first()

    if instance:
        for key, value in defaults.items():
            setattr(instance, key, value)
    else:
        if id:
            params = {**kwargs, **defaults}
            instance = model(id=id, **params)
            session.add(instance)
        else:
            params = {**kwargs, **defaults}
            instance = model(project_id=project_id, **params)
            session.add(instance)

    await session.commit()
    return instance


def get_object_by_filter(model: Type, filter_conditions: Dict[str, Any]):
    return sync_session.query(model).filter_by(**filter_conditions).first()

