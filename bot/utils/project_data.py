import asyncio
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import aiohttp
import httpx
import requests
from aiogram.types import Message
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db_operations import (
    get_one,
    get_all,
    get_or_create,
    update_or_create,
    get_user_from_redis_or_db,
)
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
    NetworkMetrics,
)
from bot.utils.common.config import CRYPTORANK_API_KEY
from bot.utils.common.consts import (
    TICKERS,
    REPLACED_PROJECT_TWITTER,
    COINMARKETCUP_API,
    COINCARP_API,
    CRYPTORANK_WEBSITE,
    TOKENOMIST_API,
    TWITTERSCORE_API,
    COINGECKO_API,
    CRYPTOCOMPARE_API,
    BINANCE_API,
    LLAMA_API_BASE,
    LLAMA_API_PROTOCOL,
    SELECTOR_TOP_100_WALLETS,
    SELECTOR_TWITTERSCORE,
    RATING_LABELS,
    CRYPTORANK_API_URL,
)
from bot.utils.common.decorators import save_execute
from bot.utils.common.params import (
    get_header_params,
    get_cryptocompare_params,
    get_cryptocompare_params_with_full_name,
)
from bot.utils.common.sessions import client_session, session_local
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.resources.exceptions.exceptions import (
    DataTypeError,
    MissingKeyError,
    AttributeAccessError,
    ValueProcessingError,
    ExceptionError,
    TimeOutError,
    DatabaseFetchError,
)
from bot.utils.resources.gpt.gpt import agent_handler
from bot.utils.validations import clean_fundraise_data, extract_tokenomics

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_crypto_key(symbol: str) -> str:
    """
    Получает `key` для токена по его символу (тикеру) через API CryptoRank
    """
    params = {"symbol": symbol}
    headers = {"X-Api-Key": CRYPTORANK_API_KEY, "Accept": "application/json"}
    response = requests.get(CRYPTORANK_API_URL, params=params, headers=headers)
    print(response.status_code, response.json())
    if response.status_code == 200:
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0]["key"]


@save_execute
async def get_user_project_info(session: AsyncSession, user_coin_name: str):
    """
    Получает информацию о проекте и связанных метриках по имени монеты пользователя.
    """

    try:
        project, created = await get_or_create(
            Project, coin_name=user_coin_name
        )
        if created:
            logging.info(f"Создан новый проект: {user_coin_name}")
        else:
            logging.info(f"Найден существующий проект: {user_coin_name}")

        tokenomics_data = await get_one(Tokenomics, project_id=project.id)
        basic_metrics = await get_one(BasicMetrics, project_id=project.id)
        investing_metrics = await get_one(
            InvestingMetrics, project_id=project.id
        )
        social_metrics = await get_one(SocialMetrics, project_id=project.id)
        funds_profit = await get_one(FundsProfit, project_id=project.id)
        top_and_bottom = await get_one(TopAndBottom, project_id=project.id)
        market_metrics = await get_one(MarketMetrics, project_id=project.id)
        manipulative_metrics = await get_one(
            ManipulativeMetrics, project_id=project.id
        )
        network_metrics = await get_one(NetworkMetrics, project_id=project.id)

        return {
            "project": project,
            "tokenomics_data": tokenomics_data,
            "basic_metrics": basic_metrics,
            "investing_metrics": investing_metrics,
            "social_metrics": social_metrics,
            "funds_profit": funds_profit,
            "top_and_bottom": top_and_bottom,
            "market_metrics": market_metrics,
            "manipulative_metrics": manipulative_metrics,
            "network_metrics": network_metrics,
        }

    except AttributeError as attr_error:
        raise ExceptionError(str(attr_error))
    except KeyError as key_error:
        raise ExceptionError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


@save_execute
async def get_project_and_tokenomics(
    session: AsyncSession, project_name: str, user_coin_name: str
):
    """
    Получает информацию о проекте и связанных метриках по категории и токену пользователя.
    """

    user_coin_added = False  # Флаг для отслеживания добавленного токена

    try:
        project_name = project_name.strip()

        projects = await get_all(Project, category=project_name)

        tokenomics_data_list = []
        if not projects:
            logger.warning(f"Проект с именем {project_name} не найден.")
            raise ValueProcessingError(f"Project '{project_name}' not found.")

        if user_coin_name and user_coin_name not in TICKERS:
            logger.info(
                f"Добавление монеты {user_coin_name} в список тикеров."
            )
            TICKERS.insert(0, user_coin_name)
            user_coin_added = True  # Запоминаем, что токен был добавлен

        for project in projects:
            tokenomics_data = None
            if project.coin_name in TICKERS:
                logger.info(
                    f"Получение данных токеномики для проекта: {project.coin_name}"
                )

                tokenomics_data, _ = await get_or_create(
                    Tokenomics,
                    defaults={"project_id": project.id},
                    project_id=project.id,
                )
                tokenomics_data = [tokenomics_data]

            tokenomics_data_list.append((project, tokenomics_data))

            if not tokenomics_data_list and tokenomics_data:
                logger.warning("Нет доступных проектов для сравнения.")

                # Создание новой записи токеномики, если она отсутствует
                tokenomics_data, _ = await get_or_create(
                    Tokenomics,
                    defaults={"project_id": project.id},
                    project_id=project.id,
                )
                logger.warning("Нет доступных проектов для сравнения.")

        logger.info(
            f"Проекты и токеномика успешно получены для категории {project_name}."
        )
        return projects, tokenomics_data_list

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))

    finally:
        # Удаляем пользовательский токен из TICKERS, если он был добавлен
        if user_coin_added and user_coin_name in TICKERS:
            logger.info(f"Удаление монеты {user_coin_name} из списка тикеров.")
            TICKERS.remove(user_coin_name)


async def get_twitter_link_by_symbol(symbol: str):
    """
    Получает ссылку на твиттер по символу токена.
    """

    url = f"{COINMARKETCUP_API}info?symbol={symbol}"

    header_params = get_header_params(coin_name=symbol)

    async with client_session().get(
        url, headers=header_params["headers"]
    ) as response:
        if response.status == 200:
            data = await response.json()
            print(data)
            if symbol in data["data"]:
                description = data["data"][symbol].get("description", None)
                lower_name = data["data"][symbol].get("name", None)
                urls = data["data"][symbol].get("urls", {})
                twitter_links = urls.get("twitter", [])
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
            print(
                f"Error retrieving data: {response.status}, {await response.text()}"
            )
            return None, None, None


async def get_twitter(name: str):
    """
    Получает информацию о твиттере и твиттерскоре по токену.
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        if type(name) is str:
            coin_name = name
        else:
            coin_name, about, lower_name = name

        await page.route(
            "**/*",
            lambda route: route.continue_()
            if "image" not in route.request.resource_type
            else route.abort(),
        )
        coin = coin_name.split("/")[-1]

        try:
            await page.goto(
                f"{TWITTERSCORE_API}twitter/{coin}/overview/?i=16846"
            )
            await asyncio.sleep(15)
        except Exception as e:
            await browser.close()
            return None

        try:
            await page.wait_for_selector(SELECTOR_TWITTERSCORE, timeout=15000)
            twitter = await page.locator(
                SELECTOR_TWITTERSCORE
            ).first.inner_text()
        except:
            twitter = None

        try:
            twitterscore = await page.locator("#insideChartCount").inner_text()
        except:
            twitterscore = None

        await browser.close()

        return (
            {"twitter": twitter, "twitterscore": twitterscore}
            if twitter or twitterscore
            else None
        )


async def get_top_100_wallets(user_coin_name: str):
    """
    Получает процент токенов на топ 100 кошельках блокчейна.
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            coin = user_coin_name.split("/")[-1]
            logging.info(f"Запрашиваем данные для {coin}")

            try:
                # Переход на страницу richlist
                await page.goto(
                    f"{COINCARP_API}{coin}/richlist/", timeout=120000
                )

                # Даем время для загрузки JS
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(5)  # Подстраховка

                # Проверяем наличие элемента
                element = await page.query_selector(SELECTOR_TOP_100_WALLETS)

                if not element:
                    logging.warning(
                        f"Элемент {SELECTOR_TOP_100_WALLETS} не найден для {coin}"
                    )
                    return None  # Возвращаем None, если элемент не найден

                top_100_text = await element.inner_text()

                logging.info(f"Текст топ-100: {top_100_text}")

                # Преобразуем в число
                try:
                    top_100_percentage = float(
                        top_100_text.replace("%", "").strip()
                    )
                    return round(top_100_percentage / 100, 2)
                except ValueError:
                    return None

            except TimeoutError as time_error:
                raise TimeOutError(f"Таймаут ожидания страницы: {time_error}")
            except ValueError as value_error:
                raise ValueProcessingError(
                    f"Ошибка обработки данных: {value_error}"
                )
            except Exception as e:
                raise ExceptionError(f"Непредвиденная ошибка: {e}")

            finally:
                await browser.close()

    except AttributeError as attr_error:
        raise AttributeAccessError(f"Ошибка доступа к атрибуту: {attr_error}")
    except KeyError as key_error:
        raise MissingKeyError(f"Отсутствует ключ в данных: {key_error}")
    except ValueError as value_error:
        raise ValueProcessingError(f"Ошибка обработки значения: {value_error}")
    except Exception as e:
        raise ExceptionError(f"Общая ошибка: {e}")


async def fetch_tokenomics_data(url: str) -> list:
    """
    Загружает данные о распределении токенов с указанного URL.
    """
    tokenomics_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:

            # Поиск таблицы на Cryptorank (для 'vesting' запросов)
            if "vesting" in url:
                try:
                    await page.goto(url, wait_until="networkidle")

                    # Ждем появление контента с увеличенным таймаутом
                    await page.wait_for_selector("table", timeout=5000)
                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")

                    table = soup.find("table")
                    if table:
                        rows = table.find_all("tr")[1:]
                        for row in rows:
                            columns = row.find_all("td")
                            if len(columns) >= 2:
                                name = columns[0].get_text(strip=True)
                                percentage = columns[1].get_text(strip=True)
                                tokenomics_data.append(
                                    f"{name} ({percentage})"
                                )
                except Exception as e:
                    print(f"❌ Ошибка при поиске таблицы: {e}")

            # Парсим ICO-токеномику (Cryptorank API - ico)
            elif "ico" in url:
                await page.goto(url, wait_until="networkidle")

                # Ждем появления списка <ul>, иначе пробуем через XPath
                try:
                    await page.wait_for_selector(
                        "ul.sc-3c81cf8-0.ffoUXx > li", timeout=5000
                    )
                except Exception:
                    print("⚠️ Элемент не найден, пробуем XPath...")
                    await page.wait_for_timeout(3000)

                # Пробуем сначала CSS, затем XPath
                token_list = await page.query_selector_all(
                    "ul.sc-3c81cf8-0.ffoUXx > li"
                )
                if not token_list:
                    token_list = await page.query_selector_all(
                        "xpath=//ul[contains(@class, 'sc-') and contains(@class, 'ffoUXx')]/li"
                    )

                if not token_list:
                    print("❌ Токеномика не найдена!")
                else:
                    print(f"✅ Найдено {len(token_list)} элементов")

                for item in token_list:
                    print(f"Обрабатываем элемент: {await item.inner_html()}")

                    try:
                        name_tag = await item.query_selector(
                            "p.sc-3c81cf8-3.dISENB"
                        )
                        name = (
                            await name_tag.inner_text()
                            if name_tag
                            else "Не найдено"
                        )

                        percentage_tag = await item.query_selector(
                            "div.sc-3c81cf8-4.iugGsJ > span"
                        )
                        percentage = (
                            await percentage_tag.inner_text()
                            if percentage_tag
                            else "Не найдено"
                        )

                        tokenomics_data.append(f"{name} ({percentage})")

                    except Exception as e:
                        print(f"❌ Ошибка при обработке элемента: {e}")
                        print(
                            f"🚨 Проблемный элемент: {await item.inner_html()}"
                        )

            # Для Tokenomist API
            else:
                try:
                    await page.wait_for_selector(
                        "div.tokenomics-container > div", timeout=5000
                    )
                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")

                    allocation_divs = soup.select(
                        "div.tokenomics-container > div"
                    )
                    for div in allocation_divs:
                        try:
                            name = div.select_one("p").get_text(strip=True)
                            percentage = div.select_one("span").get_text(
                                strip=True
                            )
                            tokenomics_data.append(f"{name} ({percentage})")
                        except AttributeError:
                            continue
                except Exception as e:
                    print(f"❌ Ошибка при поиске данных Tokenomist: {e}")

        except Exception as e:
            logging.error(f"🚨 Ошибка при получении данных: {e}")

        finally:
            await browser.close()

    return tokenomics_data


@save_execute
async def get_percentage_data(
    async_session: AsyncSession, lower_name: str, user_coin_name: str
):
    """
    Получает данные о распределении токенов в проекте.
    """

    try:
        project = await get_one(Project, coin_name=user_coin_name)
        if project:
            user_tokenomics = await get_one(FundsProfit, project_id=project.id)
            if (
                user_tokenomics
                and user_tokenomics.distribution
                and user_tokenomics.distribution not in ["--)", "-", "-)", ""]
            ):
                return extract_tokenomics(user_tokenomics.distribution)

        # Запрос к Cryptorank
        tokenomics_data = await fetch_tokenomics_data(
            f"{CRYPTORANK_WEBSITE}price/{lower_name}/vesting"
        )

        # Если не удалось получить данные с Cryptorank, пробуем Tokenomist.ai
        if not tokenomics_data:
            logging.warning(
                "Не удалось найти таблицу на Cryptorank. Пробуем из ico..."
            )
            tokenomics_data = await fetch_tokenomics_data(
                f"{CRYPTORANK_WEBSITE}ico/{lower_name}"
            )

        if not tokenomics_data:
            logging.warning(
                "Не удалось найти таблицу с заданными заголовками на Cryptorank. Пробуем Tokenomist.ai..."
            )
            tokenomics_data = await fetch_tokenomics_data(
                f"{TOKENOMIST_API}{lower_name}"
            )

        return tokenomics_data if tokenomics_data else None

    except (AttributeError, KeyError, ValueError) as e:
        raise ExceptionError(str(e))
    except Exception as e:
        raise ExceptionError(str(e))


async def get_coin_description(coin_name: str):
    """
    Получение описания проекта на CoinGecko
    """

    url = f"{COINGECKO_API}{coin_name}"
    description = ""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            if "description" in data and "en" in data["description"]:
                description = data["description"]["en"]
            else:
                logging.warning(f"No description found for {coin_name}.")
        else:
            logging.error(
                f"Failed to fetch data: {response.status_code} - {response.text}"
            )

    except Exception as e:
        raise ExceptionError(str(e))

    return description


async def get_fundraise(user_coin_name: str, message: Message = None):
    """
    Получение информации о фандрейзе проекта на Cryptorank
    """

    try:
        print(f"get_fundraise {user_coin_name}")
        user_coin_key = get_crypto_key(user_coin_name)
        if not user_coin_key:
            if message:
                await message.answer(
                    f"Токен '{user_coin_name}' не найден в CryptoRank API"
                )
            return None, []

        url = f"{CRYPTORANK_WEBSITE}ico/{user_coin_key}"
        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            link = soup.select_one("a.sc-1f2a5732-0.jwxUWV")
            if link:
                new_url = urljoin(url, link["href"])
                response = requests.get(new_url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Получение информации о фандрайзе
                    fundraising_elements = soup.select(
                        "p.sc-56567222-0.fzulHc"
                    )
                    if len(fundraising_elements) > 1:
                        fundraising_data = fundraising_elements[1].text
                        clean_data = clean_fundraise_data(fundraising_data)
                    else:
                        clean_data = None

                    # Инициализация переменной investors_data пустым списком
                    investors_data = ""

                    # Получение инвесторов и их тиров
                    investors_rows = soup.select(
                        "table.sc-9b3136d-1.cnOWhJ tbody tr"
                    )

                    if not investors_rows:
                        print("❌ Таблица инвесторов не найдена!")

                    for investor in investors_rows[
                        :5
                    ]:  # Ограничение до 5 элементов
                        try:
                            # Извлекаем название инвестора
                            name_tag = investor.select_one(
                                "td.sc-4b43e9a5-0.dpEQjJ p.sc-56567222-0.ktClAm"
                            )
                            name = (
                                name_tag.get_text(strip=True)
                                if name_tag
                                else "Не найдено"
                            )

                            # Извлекаем Tier
                            tier_tag = investor.select_one(
                                "td.sc-4b43e9a5-0.hMDMTF p.sc-56567222-0.ktClAm"
                            )
                            tier = (
                                tier_tag.get_text(strip=True)
                                if tier_tag
                                else "Не найдено"
                            )

                            investors_data += f"{name} (Tier: {tier}), "

                        except AttributeError as e:
                            print(f"❌ Ошибка при обработке инвестора: {e}")
                            continue

                    logging.info(
                        f"Инвесторы, fundraise: {investors_data, clean_data}"
                    )
                    return clean_data, investors_data

            logging.error("Элемент для клика не найден")
            return None, []
        else:
            if message:
                await message.answer(
                    f"Ошибка получения данных для монеты '{user_coin_name}'"
                )

            logging.error(
                f"Ошибка при получении данных: {response.status_code}"
            )
            return None, []

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


async def fetch_coingecko_data(user_coin_name: str = None):
    """
    Получение основных данных о токене из CoinGecko
    """

    try:
        url = f"{COINGECKO_API}{user_coin_name}"
        response = requests.get(url)
        data = response.json()

        if "market_data" in data:
            coin_name = data["name"].lower()
            circulating_supply = data["market_data"]["circulating_supply"]
            total_supply = data["market_data"]["total_supply"]
            price = data["market_data"]["current_price"]["usd"]
            market_cap = data["market_data"]["market_cap"]["usd"]
            coin_fdv = total_supply * price if price > 0 else None

            return {
                "coin_name": coin_name,
                "circulating_supply": circulating_supply,
                "total_supply": total_supply,
                "price": price,
                "capitalization": market_cap,
                "coin_fdv": coin_fdv,
            }
        else:
            logging.error(f"Error: No market data found for {user_coin_name}")
            return None

    except Exception as e:
        raise ExceptionError(str(e))


async def fetch_coinmarketcap_data(
    message: Message = None,
    user_coin_name: str = None,
    headers: dict = None,
    parameters: dict = None,
):
    """
    Получение основных данных о токене из CoinMarketCap
    """

    try:
        data = requests.get(
            f"{COINMARKETCUP_API}quotes/latest",
            headers=headers,
            params=parameters,
        )
        data = data.json()
        print("COINMARKETCUP_API: ", data)

        if "data" in data:
            coin_name = data["data"][user_coin_name]["name"].lower()
            logging.info(f"{coin_name, data['data'][user_coin_name]['name']}")

            crypto_data = data["data"][user_coin_name]["quote"]["USD"]
            circulating_supply = data["data"][user_coin_name][
                "circulating_supply"
            ]
            total_supply = data["data"][user_coin_name]["total_supply"]
            price = crypto_data["price"]
            market_cap = crypto_data["market_cap"]
            coin_fdv = total_supply * price if price and price > 0 else None

            result = {
                "circulating_supply": circulating_supply
                if circulating_supply
                else None,
                "total_supply": total_supply if total_supply else None,
                "price": price if price else None,
                "capitalization": market_cap if market_cap else None,
                "coin_fdv": coin_fdv if coin_fdv else None,
            }

            # Удаляем ключи, у которых значение None
            result = {
                key: value
                for key, value in result.items()
                if value is not None
            }

            if result:
                result["coin_name"] = coin_name

            return result if result else None

        else:
            if message:
                await phrase_by_user(
                    "error_input_token_from_user",
                    message.from_user.id,
                    session_local,
                )
            logging.info(
                "Ошибка: данные о монете не получены. Проверьте введённый тикер."
            )
            return None

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


def fetch_binance_data(symbol: str):
    """
    Получение макс/мин цены токена с Binance API
    """

    try:
        # Запрос данных с Binance API
        params = {"symbol": symbol, "interval": "1d", "limit": 730}
        response = requests.get(f"{BINANCE_API}klines", params=params)
        response.raise_for_status()  # Проверяем наличие ошибок HTTP

        data = response.json()

        # Извлекаем максимальные и минимальные значения из свечей
        highs = [float(candle[2]) for candle in data]  # Индекс 2 для 'high'
        lows = [float(candle[3]) for candle in data]  # Индекс 3 для 'low'

        max_price = max(highs)
        min_price = min(lows)
        return max_price, min_price

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к Binance API: {e}")
        return None, None

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        return None, None


def get_coingecko_id_by_symbol(symbol: str):
    """
    Получение ID-токена из CoinGecko по тикеру
    """

    url = f"{COINGECKO_API}list"
    response = requests.get(url)
    tokens = response.json()
    for token in tokens:
        if token["symbol"].lower() == symbol.lower():
            return token["id"]
    return None


async def fetch_cryptocompare_data(
    cryptocompare_params: dict,
    cryptocompare_params_with_full_coin_name: dict,
    price: float,
    request_type: str = None,
):
    """
    Получение макс/мин цены токена из CryptoCompare
    """

    max_price = None
    min_price = None
    fail_high = None
    growth_low = None

    try:
        # Первый вариант запроса к CryptoCompare
        response = requests.get(CRYPTOCOMPARE_API, params=cryptocompare_params)
        data = response.json()

        if "Data" in data and "Data" in data["Data"]:
            daily_data = data["Data"]["Data"]
            highs = [
                day["high"] for day in daily_data if day["high"] > 0.00001
            ]
            lows = [day["low"] for day in daily_data if day["low"] > 0.00001]
            max_price = max(highs)
            min_price = min(lows)

            fail_high = (price / max_price) - 1
            growth_low = price / min_price
        else:
            logging.info(
                "Нет данных от первого запроса CryptoCompare, пробуем с полным названием токена."
            )

            # Второй вариант запроса к CryptoCompare
            response_full_name = requests.get(
                CRYPTOCOMPARE_API,
                params=cryptocompare_params_with_full_coin_name,
            )
            data_full_name = response_full_name.json()

            if "Data" in data_full_name and "Data" in data_full_name["Data"]:
                daily_data = data_full_name["Data"]["Data"]
                highs = [day["high"] for day in daily_data if day["high"] > 0]
                lows = [day["low"] for day in daily_data if day["low"] > 0]
                max_price = max(highs)
                min_price = min(lows)

                fail_high = (price / max_price) - 1
                growth_low = price / min_price
            else:
                logging.info(
                    "Нет данных от CryptoCompare, переключаемся на Binance API."
                )

                # Попытка получения данных с Binance
                symbol = (
                    cryptocompare_params["fsym"] + cryptocompare_params["tsym"]
                )
                max_price, min_price = fetch_binance_data(symbol)

                if max_price and min_price:
                    fail_high = (price / max_price) - 1
                    growth_low = price / min_price
                else:
                    logging.error(
                        "Нет данных от Binance API, переключаемся на CoinGecko API."
                    )

                    # Попытка получения данных с CoinGecko
                    token_id = get_coingecko_id_by_symbol(
                        cryptocompare_params["fsym"]
                    )
                    max_price, min_price = fetch_coingecko_max_min_data(
                        token_id, cryptocompare_params["tsym"]
                    )

                    if max_price and min_price:
                        fail_high = (price / max_price) - 1
                        growth_low = price / min_price

        # Возврат данных в зависимости от типа запроса
        if request_type == "top_and_bottom":
            return max_price, min_price
        elif request_type == "market_metrics":
            return fail_high, growth_low
        else:
            return fail_high, growth_low, max_price, min_price

    except Exception as e:
        logging.error(f"Ошибка при получении данных: {str(e)}")
        return None  # Возвращаем None в случае ошибки


def fetch_coingecko_max_min_data(fsym: str, tsym: str):
    """
    Получение макс/мин цены токена с CoinGecko API.
    """

    try:
        # Подготовка параметров для CoinGecko
        coingecko_symbol = fsym.lower()
        vs_currency = tsym.lower()
        url = f"{COINGECKO_API}{coingecko_symbol}/market_chart?vs_currency={vs_currency}&days=730"

        response = requests.get(url)
        data = response.json()

        if "prices" in data:
            prices = [price[1] for price in data["prices"]]
            max_price = max(prices)
            min_price = min(prices)
            return max_price, min_price
        else:
            raise ValueProcessingError(
                "CoinGecko API не вернул данные о ценах."
            )

    except Exception as e:
        raise ExceptionError(str(e))


async def fetch_twitter_data(name: str):
    """
    Получение данных о Twitter пользователе по его имени.
    """
    try:
        twitter_response = await get_twitter(name)

        if not twitter_response:
            return None, None

        return twitter_response.get("twitter"), int(
            twitter_response.get("twitterscore", 0)
        )

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


async def fetch_top_100_wallets(coin_name: str):
    """
    Получение процента токенов на топ 100 кошельках блокчейна.
    """
    try:
        return await get_top_100_wallets(coin_name)
    except AttributeError as e:
        raise AttributeAccessError(str(e))
    except KeyError as e:
        raise MissingKeyError(str(e))
    except ValueError as e:
        raise ValueProcessingError(str(e))
    except Exception as e:
        raise ExceptionError(str(e))


@save_execute
async def fetch_fundraise_data(session: AsyncSession, user_coin_name: str):
    """
    Получение данных о фандрейзе токена.
    """

    try:
        clean_data, investors = await get_fundraise(user_coin_name)
        return clean_data, investors
    except AttributeError as e:
        raise AttributeAccessError(str(e))
    except KeyError as e:
        raise MissingKeyError(str(e))
    except ValueError as e:
        raise ValueProcessingError(str(e))
    except TypeError as e:
        raise DataTypeError(str(e))
    except Exception as e:
        raise ExceptionError(str(e))


async def fetch_tvl_data(coin_name: str):
    """
    Получение текущего TVL блокчейна, или токенов в стейкинге, если TVL недоступен.
    """

    url = f"{LLAMA_API_BASE}{coin_name.lower()}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list) and data:
                        last_entry = data[-1]
                        last_tvl = last_entry.get("totalLiquidityUSD", 0)
                        logging.info(f"Последний TVL (base_url): {last_tvl}")
                        return float(last_tvl)
                    else:
                        logging.error(
                            f"No TVL data found for {coin_name} using base_url."
                        )

            # Если базовый URL не сработал, пробуем через протокол URL
            protocol_query = f"{LLAMA_API_PROTOCOL}{coin_name.lower()}"
            async with session.get(protocol_query) as response:
                if response.status == 200:
                    data = await response.json()

                    # Проверяем наличие данных о текущих TVL
                    current_chain_tvl = data.get("currentChainTvls", {})
                    if current_chain_tvl:
                        # Ищем ключи, связанные со стейкингом
                        staking_keys = [
                            "staking",
                            f"{coin_name.lower()}-staking",
                        ]
                        for key in staking_keys:
                            if key in current_chain_tvl:
                                staking_tvl = current_chain_tvl[key]
                                print(
                                    f"Найден TVL стейкинга ({key}): {staking_tvl}"
                                )
                                return staking_tvl

                    logging.error(
                        f"No staking TVL found for {coin_name} using protocol_url."
                    )
                else:
                    logging.error(
                        f"Protocol URL failed for {coin_name}. Status code: {response.status}"
                    )
                    return None

        except AttributeError as e:
            raise AttributeAccessError(str(e))
        except KeyError as e:
            raise MissingKeyError(str(e))
        except ValueError as e:
            raise ValueProcessingError(str(e))
        except Exception as e:
            raise ExceptionError(str(e))


async def get_lower_name(user_coin_name: str):
    """
    Получение полного названия криптовалюты в нижнем регистре по тикеру.
    """

    url = f"{COINMARKETCUP_API}info"
    header_params = get_header_params(coin_name=user_coin_name)

    async with aiohttp.ClientSession() as session_local:
        async with session_local.get(
            url, headers=header_params["headers"]
        ) as response:
            if response.status == 200:
                data = await response.json()
                logging.info(f"{data['data']}")
                if user_coin_name.upper() in data["data"]:
                    lower_name = (
                        data["data"][user_coin_name.upper()]
                        .get("name", None)
                        .lower()
                    )

                    return lower_name


def get_top_projects_by_capitalization_and_category(
    tokenomics_data_list: dict,
):
    """
    Получение топ-проектов по капитализации и категории для определенных тикеров.
    """

    filtered_projects = [
        (project, tokenomics_data)
        for project, tokenomics_data in tokenomics_data_list
        if project.coin_name in TICKERS
    ]

    top_projects = sorted(
        filtered_projects,
        key=lambda item: item[1][0].capitalization
        if item[1][0].capitalization
        else 0,
        reverse=True,
    )[:5]

    return top_projects


@save_execute
async def get_top_projects_by_capitalization(
    session: AsyncSession,
    project_type: str,
    tickers: list,
    top_n_tickers: int = 5,
    top_n_other: int = 10,
) -> list[str]:
    """
    Получение топ-проектов по капитализации для определенного проектного вида (например, Layer 1).
    Использует универсальные функции для запросов в базу данных и обрабатывает ошибки с кастомными исключениями.
    """
    try:
        if not isinstance(project_type, str):
            raise ValueProcessingError(
                f"Ожидаемый тип данных для project_type — str, получено: {type(project_type).__name__}"
            )

        if not isinstance(tickers, list) or not all(
            isinstance(ticker, str) for ticker in tickers
        ):
            raise ValueProcessingError("Тикеры должны быть списком строк.")

        # Получение топ-тикеров по капитализации
        top_ticker_projects = await get_all(
            Project,
            join_model=Tokenomics,
            category=project_type,
            coin_name=lambda col: col.in_(tickers),
            order_by=Tokenomics.capitalization.desc(),
            limit=top_n_tickers,
        )

        # Получение других проектов по капитализации
        top_other_projects = await get_all(
            Project,
            join_model=Tokenomics,
            category=project_type,
            coin_name=lambda col: col.in_(tickers),
            order_by=Tokenomics.capitalization.desc(),
            limit=top_n_other,
        )

        # Возвращаем список имен монет
        return [
            project.coin_name
            for project in top_ticker_projects + top_other_projects
        ]

    except DatabaseFetchError as e:
        logging.error(f"Ошибка извлечения данных из базы: {e.detail}")
        raise

    except ValueProcessingError as e:
        logging.error(f"Ошибка обработки значений: {e}")
        raise

    except Exception as e:
        logging.error(f"Неизвестная ошибка: {e}")
        raise ExceptionError(
            f"Критическая ошибка в get_top_projects_by_capitalization: {e}"
        )


async def check_and_run_tasks(
    project: Project,
    price: float,
    lower_name: str,
    top_and_bottom: TopAndBottom,
    investing_metrics: InvestingMetrics,
    funds_profit: FundsProfit,
    social_metrics: SocialMetrics,
    market_metrics: MarketMetrics,
    manipulative_metrics: ManipulativeMetrics,
    network_metrics: NetworkMetrics,
    twitter_name: Any,
    user_coin_name: str,
    model_mapping: dict,
):
    """
    Функция, которая проверяет отсутствующие метрики у проекта, если их нет - добавляет в список на выполнение
    и в асинхронном порядке выполняет.
    """

    tasks = []
    results = {}

    cryptocompare_params = get_cryptocompare_params(user_coin_name)
    cryptocompare_params_with_full_coin_name = (
        get_cryptocompare_params_with_full_name(lower_name.upper())
    )

    if (
        investing_metrics
        and not all(
            [
                getattr(investing_metrics, "fundraise", None),
                getattr(investing_metrics, "fund_level", None),
                getattr(investing_metrics, "fund_level", "-")
                not in ["-", None, ""],
            ]
        )
    ) or not investing_metrics:
        tasks.append((fetch_fundraise_data(lower_name), "investing_metrics"))

    if (
        social_metrics
        and not all(
            [
                getattr(social_metrics, "twitter", "") not in ["-", None, ""],
                getattr(social_metrics, "twitterscore", "")
                not in ["-", None, ""],
            ]
        )
    ) or not social_metrics:
        tasks.append((fetch_twitter_data(twitter_name), "social_metrics"))

    if (
        funds_profit
        and not all(
            [
                getattr(funds_profit, "distribution", None),
                getattr(funds_profit, "distribution", "")
                not in ["--)", "-", "-)", ""],
            ]
        )
    ) or not funds_profit:
        tasks.append(
            (
                get_percentage_data(lower_name, user_coin_name),
                "funds_profit",
            )
        )

    if (
        not all(
            [
                top_and_bottom,
                market_metrics,
                getattr(top_and_bottom, "lower_threshold", None),
                getattr(top_and_bottom, "upper_threshold", None),
                getattr(market_metrics, "fail_high", None),
                getattr(market_metrics, "growth_low", None),
            ]
        )
        and price
    ):
        tasks.append(
            (
                fetch_cryptocompare_data(
                    cryptocompare_params,
                    cryptocompare_params_with_full_coin_name,
                    price,
                    "market_metrics",
                ),
                "market_metrics",
            )
        )
        tasks.append(
            (
                fetch_cryptocompare_data(
                    cryptocompare_params,
                    cryptocompare_params_with_full_coin_name,
                    price,
                    "top_and_bottom",
                ),
                "top_and_bottom",
            )
        )

    if (
        manipulative_metrics
        and not getattr(manipulative_metrics, "top_100_wallet", None)
    ) or not manipulative_metrics:
        tasks.append(
            (fetch_top_100_wallets(lower_name), "manipulative_metrics")
        )

    if (
        network_metrics and not getattr(network_metrics, "tvl", None)
    ) or not network_metrics:
        tasks.append((fetch_tvl_data(lower_name), "network_metrics"))

    # Выполняем задачи
    if tasks:
        print("tasks: ", tasks)

        # Запускаем задачи и выводим название каждой задачи перед выполнением
        task_results = []
        for task, (model_name) in tasks:
            print(
                f"Запуск задачи для модели: {model_name}"
            )  # Выводим название текущей задачи
            task_results.append(task)

        # Ожидаем выполнения всех задач
        task_results = await asyncio.gather(*task_results)

        # Выводим результаты выполнения задач
        print("task_results: ", task_results)
        logging.info(f"Результаты выполнения задач: {task_results}")
        for (result, (_, model_name)) in zip(task_results, tasks):
            if model_name not in results:
                results[model_name] = []
            results[model_name].append(result)

    # Сохранение результатов в базу данных
    if results:
        for model_name, data_list in results.items():
            model = model_mapping.get(model_name)
            if not model:
                logging.warning(
                    f"Модель для {model_name} не найдена. Пропускаем."
                )
                continue

            for data in data_list:
                # Преобразуем данные в формат для модели
                data_dict = map_data_to_model_fields(model_name, data)
                print("data_dict: ", data_dict)
                if (
                    not data_dict
                    or "N/A" in data_dict.values()
                    or data_dict is None
                ):
                    logging.warning(
                        f"Данные содержат N/A или равны None, пропускаем сохранение: {data}"
                    )
                    continue

                # Сохраняем в базу данных
                await update_or_create(
                    model, project_id=project.id, defaults=data_dict
                )

    logging.info(f"Результаты сохранены: {results}")
    return results


def calculate_expected_x(entry_price: float, total_supply: float, fdv: float):
    """
    Вычисляет рост токена (во сколько раз вырастет/упадет) и предполагаемую цену.
    """

    try:
        expected_x = fdv / (entry_price * total_supply)
        fair_price = entry_price * expected_x if total_supply else 0

        return {
            "expected_x": expected_x,
            "fair_price": fair_price,
        }

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except TypeError as type_error:
        raise DataTypeError(str(type_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


async def generate_flags_answer(
    user_id: Optional[int] = None,
    all_data_string_for_flags_agent: Optional[str | tuple[str, ...]] = None,
    project: Optional[Project] = None,
    tokenomics_data: Optional[Tokenomics] = None,
    investing_metrics: Optional[InvestingMetrics] = None,
    social_metrics: Optional[SocialMetrics] = None,
    funds_profit: Optional[FundsProfit] = None,
    market_metrics: Optional[MarketMetrics] = None,
    manipulative_metrics: Optional[ManipulativeMetrics] = None,
    network_metrics: Optional[NetworkMetrics] = None,
    tier: Optional[str] = None,
    funds_answer: Optional[str] = None,
    tokenomic_answer: Optional[str] = None,
    category_answer: Optional[str] = None,
    twitter_link: Optional[list[str]] = None,
    top_and_bottom: Optional[TopAndBottom] = None,
    language: Optional[str] = None,
) -> Optional[str]:
    """
    Функция генерации ответа анализа метрик проекта
    """
    flags_answer = None
    user_data = await get_user_from_redis_or_db(user_id)
    user_language = user_data.get("language", "ENG")

    if (user_id and user_language == "RU") or (language and language == "RU"):
        language = "RU"
        flags_answer = await agent_handler(
            "flags", topic=all_data_string_for_flags_agent, language=language
        )
        flags_answer += (
            f"\n\nДанные для анализа\n"
            f"- Анализ категории: {category_answer}\n\n"
            f"- Тир проекта: {tier}\n"
            f"- Тикер монеты: {project.coin_name if project and project.coin_name else 'N/A'}\n"
            f"- Категория: {project.category if project and project.category else 'N/A'}\n"
            f"- Капитализация: ${round(tokenomics_data.capitalization, 2) if tokenomics_data and tokenomics_data.capitalization else 'N/A'}\n"
            f"- Фандрейз: ${round(investing_metrics.fundraise) if investing_metrics and investing_metrics.fundraise else 'N/A'}\n"
            f"- Количество подписчиков: {social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A'} (Twitter: {REPLACED_PROJECT_TWITTER.get(twitter_link[0], twitter_link[0])})\n"
            f"- Twitter Score: {social_metrics.twitterscore if social_metrics and social_metrics.twitterscore else 'N/A'}\n"
            f"- Тир фондов: {investing_metrics.fund_level if investing_metrics and investing_metrics.fund_level else 'N/A'}\n"
            f"- Распределение токенов: {funds_profit.distribution if funds_profit and funds_profit.distribution else 'N/A'}\n"
            f"- Минимальная цена токена: ${round(top_and_bottom.lower_threshold, 2) if top_and_bottom and top_and_bottom.lower_threshold else 'N/A'}\n"
            f"- Максимальная цена токена: ${round(top_and_bottom.upper_threshold, 2) if top_and_bottom and top_and_bottom.upper_threshold else 'N/A'}\n"
            f"- Рост токена с минимальных значений (%): {round((market_metrics.growth_low - 1) * 100, 2) if market_metrics and market_metrics.growth_low else 'N/A'}\n"
            f"- Падение токена от максимальных значений (%): {round(market_metrics.fail_high * 100, 2) if market_metrics and market_metrics.fail_high else 'N/A'}\n"
            f"- Процент нахождения монет на топ 100 кошельков блокчейна: {round(manipulative_metrics.top_100_wallet * 100, 2) if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A'}%\n"
            f"- Заблокированные токены (TVL): {round((network_metrics.tvl / tokenomics_data.capitalization) * 100) if network_metrics and tokenomics_data and tokenomics_data.capitalization and network_metrics.tvl else 'N/A'}%\n\n"
            f"- Оценка доходности фондов: {funds_answer if funds_answer else 'N/A'}\n"
            f"- Оценка токеномики: {tokenomic_answer if tokenomic_answer else 'N/A'}\n\n"
        )
    elif (user_id and user_language == "ENG") or (
        language and language == "ENG"
    ):
        language = "ENG"
        flags_answer = await agent_handler(
            "flags", topic=all_data_string_for_flags_agent, language=language
        )
        flags_answer += (
            f"\n\nData to analyze\n"
            f"- Category analysis: {category_answer}\n\n"
            f"- Coin Ticker: {project.coin_name if project and project.coin_name else 'N/A'}\n"
            f"- Category: {project.category if project and project.category else 'N/A'}\n"
            f"- Capitalization: ${round(tokenomics_data.capitalization, 2) if tokenomics_data and tokenomics_data.capitalization else 'N/A'}\n"
            f"- Fundraise: ${round(investing_metrics.fundraise) if investing_metrics and investing_metrics.fundraise else 'N/A'}\n"
            f"- Number of Twitter subscribers: {social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A'} (Twitter: {REPLACED_PROJECT_TWITTER.get(twitter_link[0], twitter_link[0])})\n"
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
            f"- Tokenomics valuation: {tokenomic_answer if tokenomic_answer else 'N/A'}\n\n"
        )

    return flags_answer


def map_data_to_model_fields(model_name: str, data: Any) -> Dict[str, Any]:
    """
    Маппинг полученных данных в поля модели.
    """

    def safe_value(value):
        return value if value is not None else "N/A"

    if model_name == "market_metrics":
        return {
            "fail_high": safe_value(data[0] if data else None),
            "growth_low": safe_value(data[1] if data else None),
        }
    elif model_name == "top_and_bottom":
        return {
            "upper_threshold": safe_value(data[0] if data else None),
            "lower_threshold": safe_value(data[1] if data else None),
        }
    elif model_name == "investing_metrics":
        return {
            "fundraise": safe_value(data[0] if data else None),
            "fund_level": safe_value(data[1] if data else None),
        }
    elif model_name == "social_metrics":
        return {
            "twitter": safe_value(data[0] if data else None),
            "twitterscore": safe_value(data[1] if data else None),
        }
    elif model_name == "funds_profit":
        return {"distribution": safe_value(data[0] if data else None)}
    elif model_name == "manipulative_metrics":
        return {"top_100_wallet": safe_value(data if data else None)}
    elif model_name == "network_metrics":
        return {"tvl": safe_value(data if data else None)}

    logging.warning(f"Не задано сопоставление для модели {model_name}")
    return {}


def get_project_rating(final_score: int, language: str = "RU") -> str:
    """
    Возвращает текстовую оценку проекта на основе финального балла и выбранного языка.

    :param final_score: Итоговый балл проекта.
    :param language: Язык ("RU" для русского или "EN" для английского).
    :return: Название рейтинга.
    """
    labels = RATING_LABELS.get(
        language, RATING_LABELS["EN"]
    )  # Язык по умолчанию — английский

    if final_score < 50:
        return labels["bad"]
    elif 50 <= final_score <= 100:
        return labels["neutral"]
    elif 101 <= final_score <= 200:
        return labels["good"]
    else:
        return labels["excellent"]
