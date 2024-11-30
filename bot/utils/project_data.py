import asyncio
import logging
import re
from urllib.parse import urljoin

import aiohttp
import httpx
import requests
from aiogram.types import Message
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import API_KEY, COINMARKETCAP_API_URL
from bot.database.db_setup import SessionLocal
from bot.database.models import (
    Project,
    Tokenomics,
    BasicMetrics,
    SocialMetrics,
    FundsProfit,
    TopAndBottom,
    MarketMetrics,
    InvestingMetrics,
    ManipulativeMetrics,
    NetworkMetrics
)
from bot.handlers.start import user_languages
from bot.utils.consts import tickers


def is_async_session(session):
    return isinstance(session, AsyncSession)


def if_exist_instance(instance, field):
    return instance and len(instance) > 1 and isinstance(instance[1], list) and len(instance[1]) > 0 and field is not None


async def get_data(model, project_id, is_async, session):
    if is_async:
        info = select(model).filter(model.project_id == project_id)
        info_result = await session.execute(info)
        result = info_result.scalars().all()
        if result:
            return result[0]
        return None
    else:
        result = session.query(model).filter(model.project_id == project_id).all()
        if result:
            return result[0]
        return None


async def get_user_project_info(session, user_coin_name):
    try:
        is_async = is_async_session(session)
        if is_async:
            project_stmt = select(Project).filter(Project.coin_name == user_coin_name)
            project_result = await session.execute(project_stmt)
            project = project_result.scalars().first()
        else:
            project = session.query(Project).filter(Project.coin_name == user_coin_name).first()
        if not project:
            if 'RU' in user_languages.values():
                raise ValueError(f"Проект с именем {user_coin_name} не найден.")
            else:
                raise ValueError(f"Project '{user_coin_name}' not found.")

        tokenomics_data = await get_data(Tokenomics, project.id, is_async, session)
        basic_metrics = await get_data(BasicMetrics, project.id, is_async, session)
        investing_metrics = await get_data(InvestingMetrics, project.id, is_async, session)
        social_metrics = await get_data(SocialMetrics, project.id, is_async, session)
        funds_profit = await get_data(FundsProfit, project.id, is_async, session)
        top_and_bottom = await get_data(TopAndBottom, project.id, is_async, session)
        market_metrics = await get_data(MarketMetrics, project.id, is_async, session)
        manipulative_metrics = await get_data(ManipulativeMetrics, project.id, is_async, session)
        network_metrics = await get_data(NetworkMetrics, project.id, is_async, session)

        project_info = {
            "project": project,
            "tokenomics_data": tokenomics_data,
            "basic_metrics": basic_metrics,
            "investing_metrics": investing_metrics,
            "social_metrics": social_metrics,
            "funds_profit": funds_profit,
            "top_and_bottom": top_and_bottom,
            "market_metrics": market_metrics,
            "manipulative_metrics": manipulative_metrics,
            "network_metrics": network_metrics
        }

        return project_info

    except Exception as e:
        return {"error": str(e)}


async def get_project_and_tokenomics(session, project_name, user_coin_name):
    try:
        project_name = project_name.strip()
        if is_async_session(session):
            project_stmt = select(Project).filter(Project.category == project_name)
            project_result = await session.execute(project_stmt)
            projects = project_result.scalars().all()
        else:
            print(session, project_name, user_coin_name, project_name)
            projects = session.query(Project).filter(Project.category.like(f"%{project_name}%")).all()
            print(projects)

        tokenomics_data_list = []
        if not projects:
            if 'RU' in user_languages.values():
                raise ValueError(f"Проект с именем {project_name} не найден.")
            else:
                raise ValueError(f"Project '{project_name}' not found.")
        if user_coin_name and user_coin_name not in tickers:
            tickers.insert(0, user_coin_name)

        for project in projects:
            if project.coin_name in tickers:
                if is_async_session(session):
                    project_stmt = select(Tokenomics).filter(Tokenomics.project_id == project.id)
                    project_result = await session.execute(project_stmt)
                    tokenomics_data = project_result.scalars().all()
                else:
                    tokenomics_data = session.query(Tokenomics).filter(Tokenomics.project_id == project.id).all()
                if not tokenomics_data:
                    if 'RU' in user_languages.values():
                        raise ValueError(f"Нет данных по токеномике для проекта {project_name}.")
                    else:
                        raise ValueError(f"No tokenomics data for project '{project_name}'.")
                tokenomics_data_list.append((project, tokenomics_data))

        if not tokenomics_data_list:
            if 'RU' in user_languages.values():
                raise ValueError("Нет доступных проектов для сравнения.")
            else:
                raise ValueError("No available projects for comparison.")

        return projects, tokenomics_data_list

    except Exception as e:
        return {"error": str(e)}


def get_full_info(session, project_name, user_coin_name):
    try:
        projects = session.query(Project).filter(Project.category == project_name).all()
        user_project = session.query(Project).filter(Project.category == project_name).first()

        if user_project and user_project not in projects:
            projects.append(user_project)

        basic_metrics_data_list = []
        tokenomics_data_list = []
        invested_metrics_data_list = []
        social_metrics_data_list = []
        funds_profit_data_list = []
        top_and_bottom_data_list = []
        market_metrics_data_list = []
        manipulative_metrics_data_list = []
        network_metrics_data_list = []

        if not projects:
            if 'RU' in user_languages.values():
                raise ValueError(f"Проект с именем {project_name} не найден.")
            else:
                raise ValueError(f"Project '{project_name}' not found.")

        if user_coin_name not in tickers:
            tickers.insert(0, user_coin_name)

        for project in projects:
            if project.coin_name in tickers:
                tokenomics_data = session.query(Tokenomics).filter(Tokenomics.project_id == project.id).all() or []
                basic_metrics = session.query(BasicMetrics).filter_by(project_id=project.id).all() or []
                invested_metrics = session.query(InvestingMetrics).filter_by(project_id=project.id).all() or []
                social_metrics = session.query(SocialMetrics).filter_by(project_id=project.id).all() or []
                funds_profit = session.query(FundsProfit).filter_by(project_id=project.id).all() or []
                top_and_bottom = session.query(TopAndBottom).filter_by(project_id=project.id).all() or []
                market_metrics = session.query(MarketMetrics).filter_by(project_id=project.id).all() or []
                manipulative_metrics = session.query(ManipulativeMetrics).filter_by(project_id=project.id).all() or []
                network_metrics = session.query(NetworkMetrics).filter_by(project_id=project.id).all() or []

                tokenomics_data_list.append((project, tokenomics_data))
                basic_metrics_data_list.append((project, basic_metrics))
                invested_metrics_data_list.append((project, invested_metrics))
                social_metrics_data_list.append((project, social_metrics))
                funds_profit_data_list.append((project, funds_profit))
                top_and_bottom_data_list.append((project, top_and_bottom))
                market_metrics_data_list.append((project, market_metrics))
                manipulative_metrics_data_list.append((project, manipulative_metrics))
                network_metrics_data_list.append((project, network_metrics))

        return (
            projects,
            tokenomics_data_list,
            basic_metrics_data_list,
            invested_metrics_data_list,
            social_metrics_data_list,
            funds_profit_data_list,
            top_and_bottom_data_list,
            market_metrics_data_list,
            manipulative_metrics_data_list,
            network_metrics_data_list,
        )

    except Exception as e:
        return {"error": str(e)}


async def get_twitter_link_by_symbol(symbol):
    url = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info?symbol={symbol}'

    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': API_KEY,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                # logging.info(f"Data: {data}")
                if symbol in data['data']:
                    description = data['data'][symbol].get('description', None)
                    lower_name = data['data'][symbol].get('name', None)
                    urls = data['data'][symbol].get('urls', {})
                    twitter_links = urls.get('twitter', [])
                    if twitter_links and description:
                        twitter_link = twitter_links[0].lower()
                        return twitter_link, description, lower_name.lower()
                    else:
                        print(f"Twitter link for '{symbol}' not found.")
                        return None, None, None
                else:
                    print(f"Cryptocurrency with symbol '{symbol}' not found.")
                    return None, None, None
            else:
                print(f"Error retrieving data: {response.status}, {await response.text()}")
                return None, None, None


def clean_fundraise_data(fundraise_str):
    try:
        clean_str = fundraise_str.replace('$', '').strip()
        parts = clean_str.split()
        amount = 1

        for part in parts:
            clean_part = part

            if clean_part[-1] in ['B', 'M', 'K']:
                suffix = clean_part[-1]
                if suffix == 'B':
                    amount = float(clean_part[:-1])
                    amount *= 1e9
                elif suffix == 'M':
                    amount = float(clean_part[:-1])
                    amount *= 1e6
                elif suffix == 'K':
                    amount = float(clean_part[:-1])
                    amount *= 1e3

            amount = float(amount)

        return amount
    except Exception as e:
        logging.error(f"Ошибка при обработке данных: {e}")
        return None, None


async def get_twitter(name):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        if type(name) == str:
            coin_name = name
        else:
            coin_name, about, lower_name = name

        await page.route("**/*", lambda route: route.continue_() if "image" not in route.request.resource_type else route.abort())
        coin = coin_name.split('/')[-1]

        try:
            await page.goto(f"https://twitterscore.io/twitter/{coin}/overview/?i=16846")
            await page.wait_for_selector('div.target-element')
        except Exception as e:
            logging.error(f"Error loading page or element: {e}")

        await page.wait_for_selector('span.more-info-data')
        twitter = await page.locator('span.more-info-data').first.inner_text()
        twitterscore = await page.locator("#insideChartCount").inner_text()

        await browser.close()

        return {"twitter": twitter, "twitterscore": twitterscore}


async def get_top_100_wallets(user_coin_name):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            coin = user_coin_name.split('/')[-1]
            logging.info(f"{user_coin_name, coin}")

            try:
                # Переход на страницу с richlist для заданной монеты
                await page.goto(f"https://www.coincarp.com/currencies/{coin}/richlist/")

                # Ожидание, пока страница полностью загрузится
                await page.wait_for_load_state("networkidle")

                # Указание полного пути к элементу с процентом топ-100 холдеров
                await page.wait_for_selector('.overflow-right-box .holder-Statistics #holders_top100', timeout=60000)
                top_100_text = await page.locator('.overflow-right-box .holder-Statistics #holders_top100').inner_text()

                # Вывод значения в лог и преобразование
                logging.info(f"top100 text: {top_100_text}")
                top_100_percentage = float(top_100_text.replace('%', '').strip())
                return round(top_100_percentage / 100, 2)

            except Exception as e:
                logging.error(f"Error loading page or selector: {e}")
                return None

            finally:
                await browser.close()

    except Exception as e:
        logging.error(f"Top_100_wallets error: {e}")
        return None


def extract_tokenomics(data):
    tokenomics_data = []
    clean_data = data.replace('\n', '').replace('\r', '').strip()
    entries = re.split(r'\)\s*', clean_data)

    for entry in entries:
        if entry:
            tokenomics_data.append(entry.strip() + ")")

    return tokenomics_data


async def get_percantage_data(lower_name, user_coin_name):
    session = SessionLocal()
    tokenomics_data = []

    try:
        project = session.query(Project).filter_by(coin_name=user_coin_name).first()
        if project:
            user_tokenomics = session.query(FundsProfit).filter(FundsProfit.project_id == project.id).first()
            if user_tokenomics and user_tokenomics.distribution != '':
                tokenomics_data = extract_tokenomics(user_tokenomics.distribution) if user_tokenomics else []

            else:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()

                    try:
                        await page.goto(f"https://cryptorank.io/price/{lower_name}/vesting", wait_until='networkidle')
                        await page.wait_for_selector('table', timeout=60000)

                        # Получение HTML-страницы
                        content = await page.content()

                        soup = BeautifulSoup(content, 'html.parser')

                        # Поиск нужной таблицы с заголовками
                        target_table = None
                        tables = soup.find_all('table')

                        for table in tables:
                            header = table.find('thead')
                            if header:
                                headers = [th.get_text(strip=True) for th in header.find_all('th')]
                                if headers == ["Name", "Total", "Unlocked", "Locked"]:
                                    target_table = table
                                    break

                        if target_table:
                            rows = target_table.find_all('tr')[1:]
                            for row in rows:
                                columns = row.find_all('td')
                                if len(columns) >= 2:
                                    name = columns[0].get_text(strip=True)
                                    percentage = columns[1].get_text(strip=True)
                                    tokenomics_data.append(f"{name} ({percentage})")
                        else:
                            logging.warning("Не удалось найти таблицу с заданными заголовками.")

                        return tokenomics_data
                    except Exception as e:
                        logging.error(f"Error loading tokenomics data: {e}")
                        return
                    finally:
                        # Закрытие браузера
                        await browser.close()

            return tokenomics_data

        else:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                try:
                    # Переход на страницу проекта и ожидание загрузки
                    await page.goto(f"https://cryptorank.io/price/{lower_name}/vesting", wait_until='networkidle')

                    # Получение HTML-страницы
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')

                    # Поиск нужной таблицы
                    table = soup.find('table', class_='sc-5f77eb9d-0')
                    rows = table.find_all('tr')[1:]  # Пропустить заголовок

                    # Извлечение названий и первых процентов
                    for row in rows:
                        columns = row.find_all('td')
                        if len(columns) >= 2:  # Проверка, что есть как минимум 2 столбца
                            name = columns[0].get_text(strip=True)
                            percentage = columns[1].get_text(strip=True)
                            tokenomics_data.append(f"{name} ({percentage})")

                    return tokenomics_data
                except Exception as e:
                    logging.error(f"Error loading tokenomics data: {e}")
                    return
                finally:
                    # Закрытие браузера
                    await browser.close()

    except Exception as e:
        logging.error(f"Tokenomics error: {e}")
        return None


async def get_coin_description(coin_name: str):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_name}"
    description = ""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            if 'description' in data and 'en' in data['description']:
                description = data['description']['en']
            else:
                logging.warning(f"No description found for {coin_name}.")
        else:
            logging.error(f"Failed to fetch data: {response.status_code} - {response.text}")

    except Exception as e:
        logging.error(f"Error fetching coin description: {e}")

    return description


async def get_fundraise(user_coin_name, message: Message = None):
    try:
        url = f"https://cryptorank.io/ico/{user_coin_name}"
        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            link = soup.select_one('a.sc-1f2a5732-0.jwxUWV')
            if link:
                new_url = urljoin(url, link['href'])
                response = requests.get(new_url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Получение информации о фандрайзинге
                    fundraising_elements = soup.select('p.sc-56567222-0.fzulHc')
                    if len(fundraising_elements) > 1:
                        fundraising_data = fundraising_elements[1].text
                        # logging.info("Фандрейзинг (сырые данные): %s", fundraising_data)

                        clean_data = clean_fundraise_data(fundraising_data)
                        # logging.info("Фандрейзинг (очищенные данные): %s", clean_data)
                    else:
                        clean_data = None

                    # Инициализация переменной investors_data пустым списком
                    investors_data = ''

                    # Получение инвесторов и их тиров
                    investors_elements = soup.select('div.sc-2ff0cdb7-0.bNrhHj table tbody tr')
                    for i, investor in enumerate(investors_elements[:5]):  # Ограничение до 5 элементов
                        name = investor.select_one('p.sc-56567222-0.ktClAm').text
                        tier = investor.select_one('td:nth-child(2) p.sc-56567222-0').text
                        investors_data += f"{name} (Tier: {tier}); "

                    logging.info(f"Инвесторы, fundraise: {investors_data, clean_data}")
                    return clean_data, investors_data

            logging.error("Элемент для клика не найден")
            return None, []
        else:
            if message:
                await message.answer(f"Ошибка получения данных для монеты '{user_coin_name}'")
            # logging.error(f"Ошибка при получении данных: {response.status_code, response.text}")
            logging.error(f"Ошибка при получении данных: {response.status_code}")
            return None, []
    except Exception as e:
        logging.error(f"Error fetching fundraise data: {e}")
        return None, []


async def fetch_coinmarketcap_data(message, user_coin_name, headers, parameters):
    try:
        data = requests.get(COINMARKETCAP_API_URL, headers=headers, params=parameters)
        data = data.json()
        if "data" in data:
            coin_name = data['data'][user_coin_name]['name'].lower()
            # logging.info(f"{coin_name, data['data'][user_coin_name]['name']}")

            crypto_data = data['data'][user_coin_name]['quote']['USD']
            circulating_supply = data['data'][user_coin_name]['circulating_supply']
            total_supply = data['data'][user_coin_name]['total_supply']
            price = crypto_data['price']
            market_cap = crypto_data['market_cap']
            coin_fdv = total_supply * price if price > 0 else None

            return {
                "coin_name": coin_name,
                "circulating_supply": circulating_supply,
                "total_supply": total_supply,
                "price": price,
                "capitalization": market_cap,
                "coin_fdv": coin_fdv
            }

        else:
            if 'RU' in user_languages.values():
                await message.answer(f"Ошибка. Проверьте правильность введенной монеты и попробуйте еще раз.")
                return
            else:
                await message.answer(f"Error. Check that the coin entered is correct and try again.")
                return
    except Exception as e:
        logging.error(f"Error fetching data for {user_coin_name}: {e}")
        return None


async def fetch_cryptocompare_data(cryptocompare_params, price):
    try:
        response = requests.get("https://min-api.cryptocompare.com/data/v2/histoday", params=cryptocompare_params)
        data = response.json()
        if 'Data' in data and 'Data' in data['Data']:
            daily_data = data['Data']['Data']
            highs = [day['high'] for day in daily_data]
            lows = [day['low'] for day in daily_data]
            max_price = max(highs)
            min_price = min(lows)

            fail_high = (price / max_price) - 1
            growth_low = price / min_price

            return fail_high, growth_low, max_price, min_price
        else:
            print("No data found.")

    except Exception as e:
        logging.error(f"Error fetching historical data: {e}")
    return None


async def fetch_twitter_data(name):
    try:
        twitter_response = await get_twitter(name)
        return twitter_response['twitter'], twitter_response['twitterscore']
    except Exception as e:
        logging.error(f"Twitter error: {e}")
        return None, None


async def fetch_top_100_wallets(coin_name):
    try:
        return await get_top_100_wallets(coin_name)
    except Exception as e:
        logging.error(f"Top_100_wallets error: {e}")
        return None


async def fetch_fundraise_data(user_coin_name):
    try:
        clean_data, investors = await get_fundraise(user_coin_name)
        return clean_data, investors
    except Exception as e:
        logging.error(f"Fundraise error: {e}")
        return None


async def fetch_tvl_data(coin_name):
    base_url = "https://api.llama.fi/v2/historicalChainTvl/"
    url = f"{base_url}{coin_name.lower()}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    if data:
                        last_tvl = data[-1]['tvl']
                        return last_tvl
                    else:
                        logging.error(f"No TVL data found for {coin_name}.")
                        return None
                else:
                    logging.error(f"Failed to fetch TVL data. Status code: {response.status}")
                    return None
        except Exception as e:
            logging.error(f"Error fetching TVL data for {coin_name}: {e}")
            return None


def extract_overall_category(category_answer: str) -> str:
    """
    Функция для извлечения общей категории проекта из строки ответа.
    Находит текст в кавычках после "Общая категория проекта:".
    """

    match = re.search(r'Общая категория проекта:\s*"([^"]+)"', category_answer)
    return match.group(1) if match else "Неизвестная категория"


def standardize_category(overall_category: str) -> str:
    """ Преобразование общей категории в соответствующее английское название. """
    category_map = {
        "Новые блокчейны 1 уровня": "Layer 1",
        "Новые блокчейны 1 уровня (после 2022 года)": "Layer 1",
        "Решения 2 уровня на базе Ethereum (ETH)": "Layer 2 (ETH)",
        "Решения 2 уровня на базе Ethereum": "Layer 2 (ETH)",
        "Старые блокчейны 1 уровня (до 2022 года)": "Layer 1 (OLD)",
        "Старые блокчейны 1 уровня": "Layer 1 (OLD)",
        "Игры на блокчейне и метавселенные": "GameFi / Metaverse",
        "Игры на блокчейне и метавселенные (GameFi / Metaverse)": "GameFi / Metaverse",
        "Токены экосистемы TON": "TON",
        "NFT платформы / маркетплейсы": "NFT Platforms / Marketplaces",
        "Инфраструктурные проекты": "Infrastructure",
        "Искусственный интеллект (AI)": "AI",
        "Искусственный интеллект": "AI",
        "NFT платформы / маркетплейсы (расширенные функции)": "NFT Platforms / Marketplaces",
        "NFT платформы / маркетплейсы": "NFT Platforms / Marketplaces",
        "Реальные активы (Real World Assets)": "RWA",
        "Реальные активы": "RWA",
        "Цифровая идентификация, сервисы": "Digital Identity",
        "Блокчейн сервисы": "Blockchain Service",
        "Финансовый сектор": "Financial sector",
        "Социальные сети на блокчейне (SocialFi)": "SocialFi",
        "Социальные сети на блокчейне": "SocialFi",
        "Децентрализованные финансы (DeFi)": "DeFi",
        "Децентрализованные финансы": "DeFi",
        "Модульные блокчейны": "Modular Blockchain"
    }
    return category_map.get(overall_category, "Unknown Category")


async def get_lower_name(user_coin_name):
    url = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info?symbol={user_coin_name.upper()}'

    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': API_KEY,
    }
    async with aiohttp.ClientSession() as session_local:
        async with session_local.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                logging.info(f"{data['data']}")
                if user_coin_name.upper() in data['data']:
                    lower_name = data['data'][user_coin_name.upper()].get('name', None).lower()

                    return lower_name


async def check_and_run_tasks(
        price,
        lower_name,
        top_and_bottom,
        investing_metrics,
        funds_profit,
        social_metrics,
        market_metrics,
        manipulative_metrics,
        network_metrics,
        twitter_name,
        user_coin_name
):
    tasks = []
    results = {}

    cryptocompare_params = {
        'fsym': user_coin_name,
        'tsym': 'USD',
        'limit': 90
    }

    if investing_metrics:
        if not all([
            investing_metrics.fundraise,
            investing_metrics.fund_level,
        ]):
            tasks.append((fetch_fundraise_data(lower_name), "investing_metrics"))

    if social_metrics:
        if not all([
            social_metrics.twitter or social_metrics.twitter == '',
            social_metrics.twitterscore or social_metrics.twitterscore == '',
        ]):
            tasks.append((fetch_twitter_data(twitter_name), "social_metrics"))

    if funds_profit:
        if not funds_profit.distribution or funds_profit.distribution == '':
            tasks.append((get_percantage_data(lower_name, user_coin_name), "funds_profit"))

    if top_and_bottom and market_metrics and price:
        if not all([
            top_and_bottom.lower_threshold,
            top_and_bottom.upper_threshold,
            market_metrics.fail_high,
            market_metrics.growth_low
        ]):
            tasks.append((fetch_cryptocompare_data(cryptocompare_params, price), "market_metrics"))

    if manipulative_metrics:
        if not manipulative_metrics.top_100_wallet:
            tasks.append((fetch_top_100_wallets(lower_name), "manipulative_metrics"))

    if network_metrics:
        if not network_metrics.tvl:
            tasks.append((fetch_tvl_data(lower_name), "network_metrics"))

    if tasks:
        task_results = await asyncio.gather(*(task for task, _ in tasks))
        for (result, (_, model_name)) in zip(task_results, tasks):
            if model_name not in results:
                results[model_name] = []
            results[model_name].append(result)

    return results


def calculate_expected_x(entry_price, total_supply, fdv):
    try:
        expected_x = fdv / (entry_price * total_supply)
        fair_price = entry_price * expected_x if total_supply else 0

        return {
            "expected_x": expected_x,
            "fair_price": fair_price,
        }

    except Exception as e:
        return {"error": str(e)}


async def send_long_message(bot_or_message, text, chat_id=None, reply_markup=None):
    """
    Отправляет длинные сообщения, разбивая их на части, если они превышают лимит.
    """
    MAX_MESSAGE_LENGTH = 4096

    if isinstance(bot_or_message, Message):
        sender = bot_or_message.answer
    else:
        sender = lambda text, reply_markup=None: bot_or_message.send_message(chat_id=chat_id, text=text,
                                                                             reply_markup=reply_markup)

    while text:
        part = text[:MAX_MESSAGE_LENGTH]
        await sender(part, reply_markup=reply_markup if len(text) <= MAX_MESSAGE_LENGTH else None)
        text = text[MAX_MESSAGE_LENGTH:]
