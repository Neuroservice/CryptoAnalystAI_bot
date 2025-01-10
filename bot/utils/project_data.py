import asyncio
import logging
import re
import textwrap
import fitz

import aiohttp
import httpx
import requests

from urllib.parse import urljoin
from aiogram.types import Message
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import COINMARKETCAP_API_URL
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
    NetworkMetrics, AgentAnswer
)
from bot.utils.consts import tickers, MAX_MESSAGE_LENGTH, get_header_params, SessionLocal, get_cryptocompare_params, \
    replaced_project_twitter
from bot.utils.gpt import agent_handler
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.validations import is_async_session, save_execute

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@save_execute
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


@save_execute
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

    except AttributeError as attr_error:
        return {"error": f"Ошибка доступа к атрибутам одного из объектов (например, {attr_error})"}
    except KeyError as key_error:
        return {"error": f"Ошибка при извлечении данных из словаря: отсутствует ключ {key_error}"}
    except TypeError as type_error:
        return {"error": f"Ошибка типов данных при обработке: {type_error}"}
    except Exception as e:
        return {"error": f"Общая ошибка при обработке данных проекта: {e}"}


@save_execute
async def get_project_and_tokenomics(session, project_name, user_coin_name):
    try:
        logger.info(f"Поиск проектов для категории: {project_name}")
        project_name = project_name.strip()

        # Проверка на асинхронную сессию
        if isinstance(session, AsyncSession):
            project_stmt = select(Project).filter(Project.category == project_name)
            project_result = await session.execute(project_stmt)
            projects = project_result.scalars().all()
        else:
            projects = session.query(Project).filter(Project.category.like(f"%{project_name}%")).all()

        tokenomics_data_list = []
        if not projects:
            logger.warning(f"Проект с именем {project_name} не найден.")
            raise ValueError(f"Project '{project_name}' not found.")

        if user_coin_name and user_coin_name not in tickers:
            logger.info(f"Добавление монеты {user_coin_name} в список тикеров.")
            tickers.insert(0, user_coin_name)

        for project in projects:
            if project.coin_name in tickers:
                logger.info(f"Получение данных токеномики для проекта: {project.coin_name}")

                # Для асинхронной сессии
                if isinstance(session, AsyncSession):
                    project_stmt = select(Tokenomics).filter(Tokenomics.project_id == project.id)
                    project_result = await session.execute(project_stmt)
                    tokenomics_data = project_result.scalars().all()
                else:
                    tokenomics_data = session.query(Tokenomics).filter(Tokenomics.project_id == project.id).all()

                if not tokenomics_data:
                    tokenomics_data = Tokenomics(project_id=project.id)
                    session.add(tokenomics_data)
                    await session.commit()

                tokenomics_data_list.append((project, tokenomics_data))

        if not tokenomics_data_list:
            if not tokenomics_data:
                tokenomics_data = Tokenomics(project_id=project.id)
                session.add(tokenomics_data)
                await session.commit()
            logger.warning("Нет доступных проектов для сравнения.")

        logger.info(f"Проекты и токеномика успешно получены для категории {project_name}.")
        return projects, tokenomics_data_list

    except AttributeError as attr_error:
        logger.error(f"Ошибка доступа к атрибутам: {attr_error}")
        return [], {"error": f"Ошибка доступа к атрибутам одного из объектов (например, {attr_error})"}
    except KeyError as key_error:
        logger.error(f"Ошибка при извлечении данных из словаря: {key_error}")
        return [], {"error": f"Ошибка при извлечении данных из словаря: отсутствует ключ {key_error}"}
    except TypeError as type_error:
        logger.error(f"Ошибка типов данных: {type_error}")
        return [], {"error": f"Ошибка типов данных при обработке: {type_error}"}
    except Exception as e:
        logger.error(f"Общая ошибка при обработке данных проекта: {e}")
        return [], {"error": f"Общая ошибка при обработке данных проекта: {e}"}


@save_execute
async def get_project_data(calc, session):
    project = await find_record(Project, session, id=calc.project_id)
    basic_metrics = await find_record(BasicMetrics, session, project_id=project.id)
    projects, similar_projects = await get_project_and_tokenomics(session, project.category,
                                                                  user_coin_name=project.coin_name)
    base_tokenomics = await find_record(Tokenomics, session, project_id=project.id)

    return project, basic_metrics, similar_projects, base_tokenomics


@save_execute
async def get_full_info(session, project_name, user_coin_name):
    try:
        query = select(Project).filter_by(category=project_name)
        result = await session.execute(query)
        projects = result.scalars().all()

        user_project = await find_record(Project, session, category=project_name)

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
            raise ValueError(f"Project '{project_name}' not found.")

        if user_coin_name not in tickers:
            tickers.insert(0, user_coin_name)

        for project in projects:
            if project.coin_name in tickers:
                tokenomics_data = await find_records(Tokenomics, session, project_id=project.id) or []
                basic_metrics = await find_records(BasicMetrics, session, project_id=project.id) or []
                invested_metrics = await find_records(InvestingMetrics, session, project_id=project.id) or []
                social_metrics = await find_records(SocialMetrics, session, project_id=project.id) or []
                funds_profit = await find_records(FundsProfit, session, project_id=project.id) or []
                top_and_bottom = await find_records(TopAndBottom, session, project_id=project.id) or []
                market_metrics = await find_records(MarketMetrics, session, project_id=project.id) or []
                manipulative_metrics = await find_records(ManipulativeMetrics, session, project_id=project.id) or []
                network_metrics = await find_records(NetworkMetrics, session, project_id=project.id) or []

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

    except AttributeError as attr_error:
        logging.error(f"Ошибка доступа к атрибутам одного из объектов: {attr_error}")
        return None, None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных из словаря: отсутствует ключ {key_error}")
        return None, None
    except TypeError as type_error:
        logging.error(f"Ошибка типов данных при обработке: {type_error}")
        return None, None
    except Exception as e:
        logging.error(f"Общая ошибка при обработке данных проекта: {e}")
        return None, None


async def get_twitter_link_by_symbol(symbol):
    url = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info?symbol={symbol}'

    header_params = get_header_params(coin_name=None)

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=header_params["headers"]) as response:
            if response.status == 200:
                data = await response.json()
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

    except AttributeError as attr_error:
        logging.error(f"Ошибка доступа к атрибутам одного из объектов: {attr_error}")
        return None, None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных из словаря: отсутствует ключ {key_error}")
        return None, None
    except TypeError as type_error:
        logging.error(f"Ошибка типов данных при обработке: {type_error}")
        return None, None
    except Exception as e:
        logging.error(f"Общая ошибка при обработке данных проекта: {e}")
        return None, None


def clean_twitter_subs(twitter_subs):
    try:
        # Если входное значение уже является числом, возвращаем его
        if isinstance(twitter_subs, (int, float)):
            return float(twitter_subs)

        # Удаляем символы и обрабатываем строку
        clean_str = twitter_subs.strip()
        parts = clean_str.split()
        amount = 1

        for part in parts:
            clean_part = part

            if clean_part[-1] in ['B', 'M', 'K']:
                suffix = clean_part[-1]
                if suffix == 'B':
                    amount = float(clean_part[:-1]) * 1e9
                elif suffix == 'M':
                    amount = float(clean_part[:-1]) * 1e6
                elif suffix == 'K':
                    amount = float(clean_part[:-1]) * 1e3
            else:
                amount = float(clean_part)

        return amount

    except AttributeError as attr_error:
        logging.error(f"Ошибка доступа к атрибутам одного из объектов: {attr_error}")
        return None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных из словаря: отсутствует ключ {key_error}")
        return None
    except TypeError as type_error:
        logging.error(f"Ошибка типов данных при обработке: {type_error}")
        return None
    except ValueError as value_error:
        logging.error(f"Ошибка преобразования данных в число: {value_error}")
        return None
    except Exception as e:
        logging.error(f"Общая ошибка при обработке данных проекта: {e}")
        return None


async def get_twitter(name):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        if type(name) == str:
            coin_name = name
        else:
            coin_name, about, lower_name = name

        await page.route("**/*", lambda
            route: route.continue_() if "image" not in route.request.resource_type else route.abort())
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
                selector = '.overflow-right-box .holder-Statistics #holders_top100'
                await page.wait_for_selector(selector, timeout=60000)
                top_100_text = await page.locator('.overflow-right-box .holder-Statistics #holders_top100').inner_text()

                # Вывод значения в лог и преобразование
                logging.info(f"top100 text: {top_100_text}")
                top_100_percentage = float(top_100_text.replace('%', '').strip())
                return round(top_100_percentage / 100, 2)

            except TimeoutError:
                logging.error(f"Timeout while waiting for the selector: {selector}")
                return None

            except ValueError as ve:
                logging.error(f"Failed to parse percentage value: {top_100_text}. Error: {ve}")
                return None

            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                return None

            finally:
                await browser.close()

    except AttributeError as attr_error:
        logging.error(f"Ошибка доступа к атрибутам одного из объектов: {attr_error}")
        return None, None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных из словаря: отсутствует ключ {key_error}")
        return None, None
    except TypeError as type_error:
        logging.error(f"Ошибка типов данных при обработке: {type_error}")
        return None, None
    except Exception as e:
        logging.error(f"Общая ошибка при обработке данных проекта: {e}")
        return None, None


def extract_tokenomics(data):
    tokenomics_data = []
    clean_data = data.replace('\n', '').replace('\r', '').strip()
    entries = re.split(r'\)\s*', clean_data)

    for entry in entries:
        if entry:
            tokenomics_data.append(entry.strip() + ")")

    return tokenomics_data


async def get_percantage_data(lower_name, user_coin_name):
    tokenomics_data = []

    try:
        async with SessionLocal() as async_session:
            project = await async_session.execute(
                select(Project).filter_by(coin_name=user_coin_name)
            )
            project = project.scalars().first()
            if project:
                funds_profit = await async_session.execute(
                    select(FundsProfit).filter_by(project_id=project.id)
                )
                user_tokenomics = funds_profit.scalars().first()
                if user_tokenomics and user_tokenomics.distribution != '':
                    tokenomics_data = extract_tokenomics(user_tokenomics.distribution) if user_tokenomics else []

                else:
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        page = await browser.new_page()
                        try:
                            await page.goto(f"https://cryptorank.io/price/{lower_name}/vesting",
                                            wait_until='networkidle')
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
                                logging.warning(
                                    "Не удалось найти таблицу с заданными заголовками на Cryptorank. Пробуем Tokenomist.ai...")
                                await page.goto(f"https://tokenomist.ai/{lower_name}", wait_until='networkidle')
                                await page.wait_for_selector('div[class*="overflow-y-auto"]', timeout=60000)

                                content = await page.content()
                                soup = BeautifulSoup(content, 'html.parser')

                                # Поиск таблицы с распределением
                                allocation_divs = soup.select('div[class*="overflow-y-auto"] > div')
                                for div in allocation_divs:
                                    try:
                                        name = div.select_one(
                                            'div.flex.items-center.w-[60px], div.flex.items-center.w-[90px]').get_text(
                                            strip=True)
                                        percentage = div.select_one('div.font-medium.mr-1.w-8.text-right').get_text(
                                            strip=True)
                                        tokenomics_data.append(f"{name} ({percentage})")
                                    except AttributeError:
                                        logging.warning(
                                            "Не удалось извлечь данные для одного из элементов Tokenomist.ai.")

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

                        if table:
                            rows = table.find_all('tr')[1:]  # Пропустить заголовок

                            # Извлечение названий и первых процентов
                            for row in rows:
                                columns = row.find_all('td')
                                if len(columns) >= 2:  # Проверка, что есть как минимум 2 столбца
                                    name = columns[0].get_text(strip=True)
                                    percentage = columns[1].get_text(strip=True)
                                    tokenomics_data.append(f"{name} ({percentage})")
                        else:
                            logging.warning(
                                "Не удалось найти таблицу с заданными заголовками на Cryptorank. Пробуем Tokenomist.ai...")
                            await page.goto(f"https://tokenomist.ai/{lower_name}", wait_until='networkidle')
                            await page.wait_for_selector('div[class*="overflow-y-auto"]', timeout=60000)

                            content = await page.content()
                            soup = BeautifulSoup(content, 'html.parser')

                            # Поиск таблицы с распределением
                            allocation_divs = soup.select('div[class*="overflow-y-auto"] > div')
                            for div in allocation_divs:
                                try:
                                    name = div.select_one(
                                        'div.flex.items-center.w-[60px], div.flex.items-center.w-[90px]').get_text(
                                        strip=True)
                                    percentage = div.select_one('div.font-medium.mr-1.w-8.text-right').get_text(
                                        strip=True)
                                    tokenomics_data.append(f"{name} ({percentage})")
                                except AttributeError:
                                    logging.warning("Не удалось извлечь данные для одного из элементов Tokenomist.ai.")

                        return tokenomics_data
                    except Exception as e:
                        logging.error(f"Error loading tokenomics data: {e}")

                        return
                    finally:
                        # Закрытие браузера
                        await browser.close()

    except AttributeError as attr_error:
        logging.error(f"Ошибка доступа к атрибутам объекта Tokenomics: {attr_error}")
        return None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных из словаря Tokenomics: отсутствует ключ {key_error}")
        return None
    except TypeError as type_error:
        logging.error(f"Ошибка типов данных при обработке Tokenomics: {type_error}")
        return None
    except Exception as e:
        logging.error(f"Общая ошибка при обработке данных Tokenomics: {e}")
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
    except AttributeError as attr_error:
        logging.error(f"Ошибка доступа к атрибутам данных фандрайзинга: {attr_error}")
        return None, []
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных фандрайзинга: отсутствует ключ {key_error}")
        return None, []
    except TypeError as type_error:
        logging.error(f"Ошибка типов данных при обработке фандрайзинга: {type_error}")
        return None, []
    except Exception as e:
        logging.error(f"Общая ошибка при получении данных фандрайзинга: {e}")
        return None, []


async def fetch_coingecko_data(user_coin_name=None):
    try:
        url = f'https://api.coingecko.com/api/v3/coins/{user_coin_name}'
        response = requests.get(url)
        data = response.json()

        if "market_data" in data:
            coin_name = data['name'].lower()
            circulating_supply = data['market_data']['circulating_supply']
            total_supply = data['market_data']['total_supply']
            price = data['market_data']['current_price']['usd']
            market_cap = data['market_data']['market_cap']['usd']
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
            logging.error(f"Error: No market data found for {user_coin_name}")
            return None
    except Exception as e:
        logging.error(f"Error fetching data from CoinGecko for {user_coin_name}: {e}")
        return None


async def fetch_coinmarketcap_data(message=None, user_coin_name=None, headers=None, parameters=None):
    try:
        data = requests.get(COINMARKETCAP_API_URL, headers=headers, params=parameters)
        data = data.json()
        if "data" in data:
            coin_name = data['data'][user_coin_name]['name'].lower()
            logging.info(f"{coin_name, data['data'][user_coin_name]['name']}")

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
            if message:
                phrase_by_user("error_input_token_from_user", message.from_user.id)
            logging.info("Ошибка: данные о монете не получены. Проверьте введённый тикер.")
            return
    except AttributeError as attr_error:
        logging.error(f"Ошибка доступа к атрибутам данных монеты {user_coin_name}: {attr_error}")
        return None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных для монеты {user_coin_name}: отсутствует ключ {key_error}")
        return None
    except TypeError as type_error:
        logging.error(f"Ошибка типов данных при получении данных для монеты {user_coin_name}: {type_error}")
        return None
    except Exception as e:
        logging.error(f"Общая ошибка при получении данных для монеты {user_coin_name}: {e}")
        return None


def fetch_binance_data(symbol):
    try:
        # Запрос данных с Binance API
        params = {
            "symbol": symbol,
            "interval": "1d",
            "limit": 180  # 180 дней
        }
        response = requests.get("https://api.binance.com/api/v3/klines", params=params)
        response.raise_for_status()  # Проверяем наличие ошибок HTTP

        data = response.json()

        # Извлекаем максимальные и минимальные значения из свечей
        highs = [float(candle[2]) for candle in data]  # Индекс 2 для 'high'
        lows = [float(candle[3]) for candle in data]  # Индекс 3 для 'low'

        max_price = max(highs)
        min_price = min(lows)
        return max_price, min_price

    except Exception as e:
        logging.error(f"Ошибка при извлечении данных с Binance API: {e}")
        return None, None


async def fetch_cryptocompare_data(cryptocompare_params, price, request_type=None):
    max_price = None
    min_price = None
    fail_high = None
    growth_low = None

    try:
        response = requests.get("https://min-api.cryptocompare.com/data/v2/histoday", params=cryptocompare_params)
        data = response.json()
        if 'Data' in data and 'Data' in data['Data']:
            daily_data = data['Data']['Data']
            highs = [day['high'] for day in daily_data if day['high'] > 0]
            lows = [day['low'] for day in daily_data if day['low'] > 0]
            max_price = max(highs)
            min_price = min(lows)

            fail_high = (price / max_price) - 1
            growth_low = price / min_price
        else:
            logging.info("Нет данных от CryptoCompare, переключаемся на Binance API.")
            symbol = cryptocompare_params['fsym'] + cryptocompare_params['tsym']
            max_price, min_price = fetch_binance_data(symbol)

            if max_price and min_price:
                fail_high = (price / max_price) - 1
                growth_low = price / min_price

            logging.error("Нет данных от Binance API.")

        if request_type == 'top_and_bottom':
            return max_price, min_price
        elif request_type == 'market_metrics':
            return fail_high, growth_low
        else:
            return fail_high, growth_low, max_price, min_price

    except AttributeError as attr_error:
        logging.error(f"Ошибка доступа к атрибутам при извлечении исторических данных: {attr_error}")
        return None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении исторических данных: отсутствует ключ {key_error}")
        return None
    except ValueError as value_error:
        logging.error(f"Ошибка при обработке значений исторических данных: {value_error}")
        return None
    except Exception as e:
        logging.error(f"Общая ошибка при извлечении исторических данных: {e}")
        return None


async def fetch_twitter_data(name):
    try:
        twitter_response = await get_twitter(name)
        return twitter_response['twitter'], int(twitter_response['twitterscore'])
    except AttributeError as attr_error:
        logging.error(f"Ошибка при доступе к атрибутам данных Twitter: {attr_error}")
        return None, None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных Twitter: отсутствует ключ {key_error}")
        return None, None
    except ValueError as value_error:
        logging.error(f"Ошибка при обработке значений данных Twitter: {value_error}")
        return None, None
    except Exception as e:
        logging.error(f"Общая ошибка при получении данных Twitter: {e}")
        return None, None


async def fetch_top_100_wallets(coin_name):
    try:
        return await get_top_100_wallets(coin_name)
    except AttributeError as attr_error:
        logging.error(f"Ошибка при доступе к атрибутам данных о топ-100 кошельках: {attr_error}")
        return None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных о топ-100 кошельках: отсутствует ключ {key_error}")
        return None
    except ValueError as value_error:
        logging.error(f"Ошибка при обработке значений данных о топ-100 кошельках: {value_error}")
        return None
    except Exception as e:
        logging.error(f"Общая ошибка при получении данных о топ-100 кошельках: {e}")
        return None


@save_execute
async def fetch_fundraise_data(user_coin_name):
    try:
        clean_data, investors = await get_fundraise(user_coin_name)
        return clean_data, investors
    except AttributeError as attr_error:
        logging.error(f"Ошибка доступа к атрибутам данных фандрейза: {attr_error}")
        return None
    except KeyError as key_error:
        logging.error(f"Ошибка при извлечении данных фандрейза: отсутствует ключ {key_error}")
        return None
    except ValueError as value_error:
        logging.error(f"Ошибка при обработке значений фандрейза: {value_error}")
        return None
    except Exception as e:
        logging.error(f"Общая ошибка при обработке данных фандрейза: {e}")
        return None


async def fetch_tvl_data(coin_name):
    base_url = "https://api.llama.fi/v2/historicalChainTvl/"
    url = f"{base_url}{coin_name.lower()}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # print("data tvl", coin_name.lower(), data)
                    if data:
                        last_tvl = data[-1]['tvl']
                        return last_tvl
                    else:
                        logging.error(f"No TVL data found for {coin_name}.")
                        return None
                else:
                    logging.error(f"Failed to fetch TVL data. Status code: {response.status}")
                    return None
        except AttributeError as attr_error:
            logging.error(f"Ошибка доступа к атрибутам данных TVL для {coin_name}: {attr_error}")
            return None
        except KeyError as key_error:
            logging.error(f"Ошибка при извлечении данных TVL для {coin_name}: отсутствует ключ {key_error}")
            return None
        except ValueError as value_error:
            logging.error(f"Ошибка при обработке значений TVL для {coin_name}: {value_error}")
            return None
        except Exception as e:
            logging.error(f"Общая ошибка при извлечении данных TVL для {coin_name}: {e}")
            return None


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
    header_params = get_header_params(coin_name=None)  # Передаем None, так как символ здесь не используется

    async with aiohttp.ClientSession() as session_local:
        async with session_local.get(url, headers=header_params["headers"]) as response:
            if response.status == 200:
                data = await response.json()
                logging.info(f"{data['data']}")
                if user_coin_name.upper() in data['data']:
                    lower_name = data['data'][user_coin_name.upper()].get('name', None).lower()

                    return lower_name


def get_top_projects_by_capitalization_and_category(tokenomics_data_list):
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

    return top_projects


async def get_top_projects_by_capitalization(project_type: str, tickers: list, top_n_tickers=5, top_n_other=10):
    async with SessionLocal() as session:
        stmt_ticker_projects = (
            select(Project)
            .join(Tokenomics, Project.id == Tokenomics.project_id)
            .where(Project.category == project_type)
            .where(Project.coin_name.in_(tickers))
            .order_by(Tokenomics.capitalization.desc())
            .limit(top_n_tickers)
        )
        stmt_other_projects = (
            select(Project)
            .join(Tokenomics, Project.id == Tokenomics.project_id)
            .where(Project.category == project_type)
            .where(Project.coin_name.in_(tickers))
            .order_by(Tokenomics.capitalization.desc())
            .limit(top_n_other)
        )
        result_ticker_projects = await session.execute(stmt_ticker_projects)
        result_other_projects = await session.execute(stmt_other_projects)
        top_ticker_projects = result_ticker_projects.scalars().all()
        top_other_projects = result_other_projects.scalars().all()
        return [project.coin_name for project in list(top_ticker_projects) + list(top_other_projects)]


async def check_and_run_tasks(
        project,
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
        user_coin_name,
        session: AsyncSession,
        model_mapping: dict
):
    logging.info(f"IN CHECK_AND_RUN_TASKS --- : {project}")
    tasks = []
    results = {}

    cryptocompare_params = get_cryptocompare_params(user_coin_name)

    if investing_metrics and not all([
        getattr(investing_metrics, 'fundraise', None),
        getattr(investing_metrics, 'fund_level', None),
        getattr(investing_metrics, 'fund_level', '-') != '-'
    ]):
        tasks.append((fetch_fundraise_data(lower_name), "investing_metrics"))

    if social_metrics and not all([
        getattr(social_metrics, 'twitter', '') != '',
        getattr(social_metrics, 'twitterscore', '') != ''
    ]):
        tasks.append((fetch_twitter_data(twitter_name), "social_metrics"))

    if funds_profit and not all([
        getattr(funds_profit, 'distribution', None),
        getattr(funds_profit, 'distribution', '') != ''
    ]):
        tasks.append((get_percantage_data(lower_name, user_coin_name), "funds_profit"))

    logging.info(f"{top_and_bottom, market_metrics, price}")
    if not all([
        top_and_bottom,
        market_metrics,
        getattr(top_and_bottom, 'lower_threshold', None),
        getattr(top_and_bottom, 'upper_threshold', None),
        getattr(market_metrics, 'fail_high', None),
        getattr(market_metrics, 'growth_low', None)
    ]) and price:
        tasks.append((fetch_cryptocompare_data(cryptocompare_params, price, "market_metrics"), "market_metrics"))
        tasks.append((fetch_cryptocompare_data(cryptocompare_params, price, "top_and_bottom"), "top_and_bottom"))

    if manipulative_metrics and not getattr(manipulative_metrics, 'top_100_wallet', None):
        tasks.append((fetch_top_100_wallets(lower_name), "manipulative_metrics"))

    if network_metrics and not getattr(network_metrics, 'tvl', None):
        tasks.append((fetch_tvl_data(lower_name), "network_metrics"))

    # Выполняем задачи
    if tasks:
        task_results = await asyncio.gather(*(task for task, _ in tasks))
        logging.info(f"Результаты выполнения задач: {task_results}")
        for (result, (_, model_name)) in zip(task_results, tasks):
            if model_name not in results:
                results[model_name] = []
            results[model_name].append(result)

    print("results.items():", results.items(), tasks)
    # Сохранение результатов в базу данных
    for model_name, data_list in results.items():
        model = model_mapping.get(model_name)
        if not model:
            logging.warning(f"Модель для {model_name} не найдена. Пропускаем.")
            continue

        for data in data_list:
            # Преобразуем данные в формат для модели
            data_dict = map_data_to_model_fields(model_name, data)
            if not data_dict or "N/A" in data_dict.values():
                logging.warning(f"Данные содержат N/A, пропускаем сохранение: {data}")
                continue

            # Сохраняем в базу данных
            await update_or_create(session, model, project_id=project.id, defaults=data_dict)

    logging.info(f"Результаты сохранены: {results}")
    return results


def calculate_expected_x(entry_price, total_supply, fdv):
    try:
        expected_x = fdv / (entry_price * total_supply)
        fair_price = entry_price * expected_x if total_supply else 0

        return {
            "expected_x": expected_x,
            "fair_price": fair_price,
        }

    except AttributeError as attr_error:
        return {"error": f"Ошибка доступа к атрибутам: {attr_error}"}
    except KeyError as key_error:
        return {"error": f"Ошибка при извлечении данных: отсутствует ключ {key_error}"}
    except TypeError as type_error:
        return {"error": f"Ошибка типов данных: {type_error}"}
    except ValueError as value_error:
        return {"error": f"Ошибка обработки значений: {value_error}"}
    except Exception as e:
        return {"error": f"Общая ошибка при обработке данных: {e}"}


async def send_long_message(bot_or_message, text, chat_id=None, reply_markup=None):
    """
    Отправляет длинные сообщения, разбивая их на части, если они превышают лимит.
    """

    if isinstance(bot_or_message, Message):
        sender = bot_or_message.answer
    else:
        sender = lambda text, reply_markup=None: bot_or_message.send_message(chat_id=chat_id, text=text,
                                                                             reply_markup=reply_markup)

    while text:
        part = text[:MAX_MESSAGE_LENGTH]
        await sender(part, reply_markup=reply_markup if len(text) <= MAX_MESSAGE_LENGTH else None)
        text = text[MAX_MESSAGE_LENGTH:]


def process_and_update_models(input_lines, field_mapping, model_mapping, session, new_project, chosen_project_obj):
    """
    Обрабатывает строки ввода, сопоставляет поля и обновляет/создает записи в базе данных.
    """

    updates = {}

    # Разбор строк ввода и обновление маппинга
    for line in input_lines:
        if ":" in line:
            field, value = line.split(":", 1)
            field = field.strip()
            value = value.strip()
            if field in field_mapping:
                updates[field_mapping[field]] = value

    # Обновление или создание моделей
    for (model_name, column_name), value in updates.items():
        model_class = model_mapping.get(model_name)
        model_instance = session.query(model_class).filter_by(project_id=new_project.id).first()

        if model_instance is None:
            model_instance = model_class(
                project_id=chosen_project_obj.id,
                **{column_name: float(value) if value.replace('.', '', 1).isdigit() else value}
            )
            session.add(model_instance)

        else:
            if column_name in model_instance.__table__.columns.keys():
                if value.replace('.', '', 1).isdigit():
                    value = float(value)
                setattr(model_instance, column_name, value)
                session.add(model_instance)

    session.commit()


async def generate_flags_answer(
    user_id=None,
    session=None,
    all_data_string_for_flags_agent=None,
    user_languages=None,
    project=None,
    tokenomics_data=None,
    investing_metrics=None,
    social_metrics=None,
    funds_profit=None,
    market_metrics=None,
    manipulative_metrics=None,
    network_metrics=None,
    tier=None,
    funds_answer=None,
    tokemonic_answer=None,
    comparison_results=None,
    category_answer=None,
    twitter_link=None,
    top_and_bottom=None,
    language=None,
):
    flags_answer = None
    if (user_id and user_languages and user_languages.get(user_id) == 'RU') or (language and language == 'RU'):
        logging.info("Ответ будет на русском")

        language = 'RU'
        flags_answer = agent_handler("flags", topic=all_data_string_for_flags_agent, language=language)
        flags_answer += (
            f"\n\nДанные для анализа\n"
            f"- Анализ категории: {category_answer}\n\n"
            f"- Тир проекта (из функции): {tier}\n"
            f"- Тикер монеты: {project.coin_name if project and project.coin_name else 'N/A'}\n"
            f"- Категория: {project.category if project and project.category else 'N/A'}\n"
            f"- Капитализация: ${round(tokenomics_data.capitalization, 2) if tokenomics_data and tokenomics_data.capitalization else 'N/A'}\n"
            f"- Фандрейз: ${round(investing_metrics.fundraise) if investing_metrics and investing_metrics.fundraise else 'N/A'}\n"
            f"- Количество подписчиков: {social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A'} (Twitter: {replaced_project_twitter.get(twitter_link[0], twitter_link[0])})\n"
            f"- Twitter Score: {social_metrics.twitterscore if social_metrics and social_metrics.twitterscore else 'N/A'}\n"
            f"- Тир фондов: {investing_metrics.fund_level if investing_metrics and investing_metrics.fund_level else 'N/A'}\n"
            f"- Распределение токенов: {funds_profit.distribution if funds_profit and funds_profit.distribution else 'N/A'}\n"
            f"- Минимальная цена токена: ${round(top_and_bottom.lower_threshold, 2) if top_and_bottom and top_and_bottom.lower_threshold else 'N/A'}\n"
            f"- Максимальная цена токена: ${round(top_and_bottom.upper_threshold, 2) if top_and_bottom and top_and_bottom.upper_threshold else 'N/A'}\n"
            f"- Рост токена с минимальных значений (%): {round((market_metrics.growth_low - 1) * 100, 2) if market_metrics and market_metrics.growth_low else 'N/A'}\n"
            f"- Падение токена от максимальных значений (%): {round(market_metrics.fail_high * 100, 2) if market_metrics and market_metrics.fail_high else 'N/A'}\n"
            f"- Процент нахождения монет на топ 100 кошельков блокчейна: {round(manipulative_metrics.top_100_wallet * 100, 2) if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A'}%\n"
            f"- Заблокированные токены (TVL): {round((network_metrics.tvl / tokenomics_data.capitalization) * 100) if network_metrics and tokenomics_data and  tokenomics_data.capitalization and network_metrics.tvl else 'N/A'}%\n\n"
            f"- Оценка доходности фондов: {funds_answer if funds_answer else 'N/A'}\n"
            f"- Оценка токеномики: {tokemonic_answer if tokemonic_answer else 'N/A'}\n\n"
        )
    elif (user_id and user_languages and user_languages.get(user_id) == 'ENG') or (language and language == 'ENG'):
        logging.info("Ответ будет на английском")

        language = 'ENG'
        flags_answer = agent_handler("flags", topic=all_data_string_for_flags_agent, language=language)
        flags_answer += (
            f"\n\nData to analyze\n"
            f"- Category analysis: {category_answer}\n\n"
            f"- Coin Ticker: {project.coin_name if project and project.coin_name else 'N/A'}\n"
            f"- Category: {project.category if project and project.category else 'N/A'}\n"
            f"- Capitalization: ${round(tokenomics_data.capitalization, 2) if tokenomics_data and tokenomics_data.capitalization else 'N/A'}\n"
            f"- Fundraise: ${round(investing_metrics.fundraise) if investing_metrics and investing_metrics.fundraise else 'N/A'}\n"
            f"- Number of Twitter subscribers: {social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A'} (Twitter: {replaced_project_twitter.get(twitter_link[0], twitter_link[0])})\n"
            f"- Twitter Score: {social_metrics.twitterscore if social_metrics and social_metrics.twitterscore else 'N/A'}\n"
            f"- Funds tier: {investing_metrics.fund_level if investing_metrics and investing_metrics.fund_level else 'N/A'}\n"
            f"- Token allocation: {funds_profit.distribution if funds_profit and funds_profit.distribution else 'N/A'}\n"
            f"- Minimum token price: ${round(top_and_bottom.lower_threshold, 2) if top_and_bottom and top_and_bottom.lower_threshold else 'N/A'}\n"
            f"- Maximum token price: ${round(top_and_bottom.upper_threshold, 2) if top_and_bottom and top_and_bottom.upper_threshold else 'N/A'}\n"
            f"- Token value growth from a low: {round((market_metrics.growth_low - 1) * 100, 2) if market_metrics and market_metrics.growth_low else 'N/A'}%\n"
            f"- Token drop from the high: {f'{round(market_metrics.fail_high * 100, 2)}%' if market_metrics and market_metrics.fail_high else 'N/A'}\n"
            f"- Percentage of coins found on top 100 blockchain wallets: {f'{round(manipulative_metrics.top_100_wallet * 100, 2)}%' if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A'}\n"
            f"- Blocked tokens (TVL): {f'{round((network_metrics.tvl / tokenomics_data.capitalization) * 100)}%' if network_metrics and network_metrics.tvl and tokenomics_data and tokenomics_data.capitalization else 'N/A'}\n"
            f"- Estimation of fund returns: {funds_answer if funds_answer else 'N/A'}\n"
            f"- Tokenomics valuation: {tokemonic_answer if tokemonic_answer else 'N/A'}\n\n"
        )

    return flags_answer


@save_execute
async def find_record(model, session: AsyncSession, **filters):
    query = select(model).filter_by(**filters)
    result = await session.execute(query)
    record = result.scalars().first()

    if record is None:
        return None
    return record


@save_execute
async def find_records(model, session: AsyncSession, **filters):
    query = select(model).filter_by(**filters)
    result = await session.execute(query)
    records = result.scalars().all()

    if records is None:
        return None
    return records


def map_data_to_model_fields(model_name, data):
    """
    Сопоставляет данные из results полям модели с обработкой None значений.

    :param model_name: Название модели.
    :param data: Кортеж или список данных из results.
    :return: Словарь с данными для записи в модель, None если значения невалидные.
    """

    def safe_value(value):
        return value if value is not None else "N/A"

    if model_name == "market_metrics":
        return {
            "fail_high": safe_value(data[0] if data else None),
            "growth_low": safe_value(data[1] if data else None)
        }
    elif model_name == "top_and_bottom":
        return {
            "upper_threshold": safe_value(data[0] if data else None),
            "lower_threshold": safe_value(data[1] if data else None)
        }
    elif model_name == "investing_metrics":
        return {
            "fundraise": safe_value(data[0] if data else None),
            "fund_level": safe_value(data[1] if data else None)
        }
    elif model_name == "social_metrics":
        return {
            "twitter": safe_value(data[0] if data else None),
            "twitterscore": safe_value(data[1] if data else None)
        }
    elif model_name == "funds_profit":
        return {
            "distribution": safe_value(data[0] if data else None)
        }
    elif model_name == "manipulative_metrics":
        return {
            "top_100_wallet": safe_value(data[0] if data else None)
        }
    elif model_name == "network_metrics":
        return {
            "tvl": safe_value(data[0] if data else None)
        }

    logging.warning(f"Не задано сопоставление для модели {model_name}")
    return None


@save_execute
async def update_or_create(session, model, project_id=None, id=None, defaults=None, **kwargs):
    """ Вспомогательная функция для обновления или создания записи. """
    instance = None

    logging.info(f"project_id {project_id} id {id}")

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


def extract_text_with_formatting(pdf_file):
    """
    Функция для извлечения текста с форматированием (HTML).
    """
    doc = fitz.open(pdf_file)
    formatted_text = ""

    for page in doc:
        # Извлечение текста с форматированием (HTML)
        formatted_text += page.get_text("html")

    return formatted_text


def extract_project_score(answer, language):
    # Заменяем типографские кавычки на обычные
    answer = answer.replace("“", "\"").replace("”", "\"")

    # Если язык RU
    if language == "RU":
        # Регулярное выражение для поиска баллов и оценки
        match = re.search(r"Итоговые баллы проекта:\s*([\d,]+)\s*баллов?\s*–\s*оценка\s*\"(.+?)\"", answer)
    else:
        match = re.search(r"Overall Project Score:\s*([\d,]+)\s*points\s*–\s*rating\s*\"(.+?)\"", answer)

    # Если найдено совпадение
    if match:
        # Заменяем запятую на точку в числе и конвертируем в float
        project_score = float(match.group(1).replace(",", "."))
        project_rating = match.group(2)
        print(f"Итоговые баллы: {project_score}")
        print(f"Оценка проекта: {project_rating}")
    else:
        project_score = "Данных по баллам не поступило" if language == "RU" else "No data on scores were received"
        project_rating = "Нет данных по оценке баллов проекта" if language == "RU" else "No data available on project scoring"
        print("Не удалось найти итоговые баллы и/или оценку.")

    return project_score, project_rating


def clean_text_preserving_list(content):
    lines = content.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped_line = " ".join(line.split())  # Убираем лишние пробелы внутри строки
        if stripped_line.startswith("-"):  # Если строка начинается с пункта списка
            cleaned_lines.append(stripped_line)
        elif cleaned_lines and not cleaned_lines[-1].endswith(":"):  # Присоединяем к предыдущей строке
            cleaned_lines[-1] += f" {stripped_line}"
        else:
            cleaned_lines.append(stripped_line)
    return "\n".join(cleaned_lines)
