import asyncio
import json
import logging
import time
import datetime

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from bot.database.models import (
    Project,
    Tokenomics,
    BasicMetrics,
    TopAndBottom,
    MarketMetrics,
    SocialMetrics,
    InvestingMetrics,
    ManipulativeMetrics,
    NetworkMetrics,
    FundsProfit,
    AgentAnswer
)
from bot.config import API_KEY, COINMARKETCAP_API_URL
from bot.utils.consts import tickers, project_types
from bot.utils.gpt import flags_agent, project_rating_agent, funds_agent, tokemonic_agent, tier_agent
from bot.utils.project_data import (
    get_twitter_link_by_symbol,
    fetch_twitter_data,
    fetch_top_100_wallets,
    fetch_tvl_data,
    get_percantage_data,
    get_user_project_info,
    get_project_and_tokenomics,
    calculate_expected_x
)

DATABASE_URL = 'sqlite:///./crypto_analysis.db'  # Для локалки
# DATABASE_URL = 'sqlite:///bot/crypto_analysis.db'  # Для прода

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
logging.basicConfig(level=logging.INFO)
update_days = {1, 4, 7, 10, 13, 16, 19, 22, 25, 28}
current_day = datetime.datetime.utcnow().day


def get_top_projects_by_capitalization(session, project_type, tickers, top_n_tickers=5, top_n_other=10):
    top_ticker_projects = (
        session.query(Project)
        .join(Tokenomics, Project.id == Tokenomics.project_id)
        .filter(Project.category == project_type, Project.coin_name.in_(tickers))
        .order_by(Tokenomics.capitalization.desc())
        .limit(top_n_tickers)
        .all()
    )

    top_other_projects = (
        session.query(Project)
        .join(Tokenomics, Project.id == Tokenomics.project_id)
        .filter(Project.category == project_type, ~Project.coin_name.in_(tickers))
        .order_by(Tokenomics.capitalization.desc())
        .limit(top_n_other)
        .all()
    )

    return [project.coin_name for project in top_ticker_projects + top_other_projects]


async def fetch_crypto_data():
    """
    Главная функция динамического парсинга
    """
    for project_type in project_types:
        symbols = get_top_projects_by_capitalization(session, project_type, tickers)

        if not symbols:
            logging.info(f"No projects found for type: {project_type}")
            continue

        for symbol in symbols:
            try:
                # --- ШАГ 1. Получение данных с CoinMarketCap ---
                parameters = {'symbol': symbol, 'convert': 'USD'}
                headers = {'X-CMC_PRO_API_KEY': API_KEY, 'Accepts': 'application/json'}
                response = requests.get(COINMARKETCAP_API_URL, headers=headers, params=parameters)
                response.raise_for_status()
                data = response.json()

                if "data" not in data or symbol not in data["data"]:
                    logging.warning(f"No CoinMarketCap data for {symbol}")
                    continue

                coin_data = data['data'][symbol]
                circulating_supply = coin_data.get('circulating_supply')
                total_supply = coin_data.get('total_supply')
                price = coin_data['quote']['USD']['price']
                market_cap = coin_data['quote']['USD']['market_cap']
                fdv = total_supply * price if price else None

                # --- ШАГ 2. Обновление данных проекта ---
                try:
                    project = session.query(Project).filter_by(coin_name=symbol).first()
                    if not project:
                        logging.error(f"Project not found for {symbol}")
                        continue

                    # Обновление Tokenomics
                    tokenomics = session.query(Tokenomics).filter_by(project_id=project.id).first()
                    if not tokenomics:
                        tokenomics = Tokenomics(
                            project_id=project.id,
                            circ_supply=circulating_supply,
                            total_supply=total_supply,
                            capitalization=market_cap,
                            fdv=fdv
                        )
                        session.add(tokenomics)
                    else:
                        tokenomics.circ_supply = circulating_supply
                        tokenomics.total_supply = total_supply
                        tokenomics.capitalization = market_cap
                        tokenomics.fdv = fdv
                    session.commit()
                except Exception as db_error:
                    logging.error(f"Error saving tokenomics data for {symbol}: {db_error}")

                # --- ШАГ 3. Обновление BasicMetrics ---
                try:
                    basic_metrics = session.query(BasicMetrics).filter_by(project_id=project.id).first()
                    if not basic_metrics:
                        basic_metrics = BasicMetrics(project_id=project.id, market_price=round(float(price), 4))
                        session.add(basic_metrics)
                    else:
                        basic_metrics.market_price = round(float(price), 4)
                    session.commit()
                except Exception as db_error:
                    logging.error(f"Error saving basic metrics for {symbol}: {db_error}")

                # --- ШАГ 4. Обновление ManipulativeMetrics ---
                try:
                    manipulative_metrics = session.query(ManipulativeMetrics).filter_by(project_id=project.id).first()
                    investing_metrics = session.query(InvestingMetrics).filter_by(project_id=project.id).first()
                    if manipulative_metrics and investing_metrics:
                        fundraise = investing_metrics.fundraise
                        top_100_wallets = await fetch_top_100_wallets(symbol.lower())
                        if top_100_wallets and fdv and fundraise:
                            update_or_create(
                                session, ManipulativeMetrics,
                                defaults={
                                    'fdv_fundraise': fdv / fundraise,
                                    'top_100_wallet': top_100_wallets
                                },
                                project_id=project.id
                            )
                        session.commit()
                except Exception as db_error:
                    logging.error(f"Error updating manipulative metrics for {symbol}: {db_error}")

                # --- ШАГ 5. Обновление NetworkMetrics (TVL) ---
                try:
                    tvl = await fetch_tvl_data(symbol.lower())
                    if tvl and fdv:
                        update_or_create(
                            session, NetworkMetrics,
                            defaults={
                                'tvl': tvl,
                                'tvl_fdv': tvl / fdv
                            },
                            project_id=project.id
                        )
                        session.commit()
                except Exception as db_error:
                    logging.error(f"Error updating TVL for {symbol}: {db_error}")

                # --- ШАГ 6. Обновление FundsProfit ---
                try:
                    funds_profit = session.query(FundsProfit).filter_by(project_id=project.id).first()
                    if not funds_profit or not funds_profit.distribution or funds_profit.distribution == '-':
                        twitter_link, description = await get_twitter_link_by_symbol(symbol)
                        tokenomics_percentage_data = await get_percantage_data(twitter_link, symbol)
                        output_string = '\n'.join(tokenomics_percentage_data) if tokenomics_percentage_data else '-'
                        update_or_create(
                            session, FundsProfit,
                            defaults={
                                'distribution': output_string,
                            },
                            project_id=project.id
                        )
                        session.commit()
                except Exception as db_error:
                    logging.error(f"Error updating funds profit for {symbol}: {db_error}")

                # --- ШАГ 7. Исторические данные и рыночные метрики ---
                try:
                    cryptocompare_params = {'fsym': symbol, 'tsym': 'USD', 'limit': 90}
                    response = requests.get("https://min-api.cryptocompare.com/data/v2/histoday", params=cryptocompare_params)
                    response.raise_for_status()
                    historical_data = response.json()
                    if 'Data' in historical_data and 'Data' in historical_data['Data']:
                        daily_data = historical_data['Data']['Data']
                        highs = [day['high'] for day in daily_data]
                        lows = [day['low'] for day in daily_data]
                        max_price = max(highs)
                        min_price = min(lows)
                        fail_high = (price / max_price) - 1
                        growth_low = price / min_price

                        update_or_create(
                            session, TopAndBottom,
                            defaults={
                                'lower_threshold': min_price,
                                'upper_threshold': max_price,
                            },
                            project_id=project.id
                        )
                        update_or_create(
                            session, MarketMetrics,
                            defaults={
                                'fail_high': fail_high,
                                'growth_low': growth_low,
                            },
                            project_id=project.id
                        )
                        session.commit()
                except Exception as e:
                    logging.error(f"Error fetching historical data for {symbol}: {e}")

                # --- ШАГ 8. Социальные метрики ---
                try:
                    twitter_name, description, _ = await get_twitter_link_by_symbol(symbol)
                    twitter, twitterscore = await fetch_twitter_data(twitter_name) if twitter_name else (None, None)
                    update_or_create(
                        session, SocialMetrics,
                        defaults={
                            'twitter': twitter,
                            'twitterscore': twitterscore
                        },
                        project_id=project.id
                    )
                    session.commit()
                except Exception as e:
                    logging.error(f"Error updating social metrics for {symbol}: {e}")

            except Exception as e:
                logging.error(f"General error processing {symbol}: {e}")

            time.sleep(5)


async def update_agent_answers(session):
    current_time = datetime.datetime.utcnow()
    three_days_ago = current_time - datetime.timedelta(days=3)
    agents_info = []

    stmt = select(AgentAnswer).where(AgentAnswer.updated_at <= three_days_ago)
    result = await session.execute(stmt)
    outdated_answers = result.scalars().all()

    for answer in outdated_answers:
        project_stmt = select(Project).filter(Project.id == answer.project_id)
        project_result = await session.execute(project_stmt)
        project = project_result.scalars().first()

        if not project:
            continue

        project_info = await get_user_project_info(session, project.coin_name)
        twitter_link = await get_twitter_link_by_symbol(project.coin_name)
        tokenomics_data = project_info.get("tokenomics_data")
        basic_metrics = project_info.get("basic_metrics")
        investing_metrics = project_info.get("investing_metrics")
        social_metrics = project_info.get("social_metrics")
        funds_profit = project_info.get("funds_profit")
        market_metrics = project_info.get("market_metrics")
        manipulative_metrics = project_info.get("manipulative_metrics")
        network_metrics = project_info.get("network_metrics")
        projects, tokenomics_data_list = await get_project_and_tokenomics(session, project.category, project.coin_name)
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
                fair_price = f"{fair_price:.5f}" if isinstance(fair_price, (int, float)) else "Ошибка в расчетах" if answer.language == 'RU' else "Error on market"

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
        if answer.language == 'RU':
            flags_answer = flags_agent(topic=all_data_string_for_flags_agent, language='русский')
        else:
            flags_answer = flags_agent(topic=all_data_string_for_flags_agent, language='english')

        answer.answer = flags_answer
        answer.updated_at = current_time
        session.add(answer)
        await session.commit()


def update_or_create(session, model, defaults=None, **kwargs):
    """ Вспомогательная функция для обновления или создания записи. """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        for key, value in defaults.items():
            setattr(instance, key, value)
    else:
        params = {**kwargs, **defaults}
        instance = model(**params)
        session.add(instance)
    session.commit()
    return instance
