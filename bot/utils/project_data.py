import asyncio
import logging
import aiohttp
import httpx
import requests

from bs4 import BeautifulSoup
from aiogram.types import Message
from typing import Any, Dict, Optional
from sqlalchemy.orm import selectinload
from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_fixed

from bot.utils.common.sessions import client_session
from bot.utils.resources.gpt.gpt import agent_handler
from bot.utils.common.config import CRYPTORANK_API_KEY, API_KEY
from bot.utils.validations import clean_fundraise_data, extract_tokenomics
from bot.utils.resources.files_worker.google_doc import load_document_for_garbage_list
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
    Category,
    project_category_association,
)
from bot.utils.common.consts import (
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
    START_TITLE_FOR_GARBAGE_CATEGORIES,
    END_TITLE_FOR_GARBAGE_CATEGORIES,
)
from bot.utils.common.params import (
    get_header_params,
    get_cryptocompare_params,
    get_cryptocompare_params_with_full_name,
)
from bot.utils.resources.exceptions.exceptions import (
    DataTypeError,
    MissingKeyError,
    AttributeAccessError,
    ValueProcessingError,
    ExceptionError,
    DatabaseFetchError,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
def get_crypto_key(symbol: str) -> str:
    """
    Получает `key` для токена по его символу (тикеру) через API CryptoRank
    """
    params = {"symbol": symbol}
    headers = {"X-Api-Key": CRYPTORANK_API_KEY, "Accept": "application/json"}
    response = requests.get(CRYPTORANK_API_URL, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        print(f"data in get_crypto_key: {data}")
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0]["key"]


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def get_user_project_info(user_coin_name: str):
    """
    Получает информацию о проекте и связанных метриках по имени монеты пользователя.
    """

    try:
        project, created = await get_or_create(Project, coin_name=user_coin_name)
        if created:
            logging.info(f"Создан новый проект: {user_coin_name}")
        else:
            logging.info(f"Найден существующий проект: {user_coin_name}")

        tokenomics_data = await get_one(Tokenomics, project_id=project.id)
        basic_metrics = await get_one(BasicMetrics, project_id=project.id)
        investing_metrics = await get_one(InvestingMetrics, project_id=project.id)
        social_metrics = await get_one(SocialMetrics, project_id=project.id)
        funds_profit = await get_one(FundsProfit, project_id=project.id)
        top_and_bottom = await get_one(TopAndBottom, project_id=project.id)
        market_metrics = await get_one(MarketMetrics, project_id=project.id)
        manipulative_metrics = await get_one(ManipulativeMetrics, project_id=project.id)
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


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def get_project_and_tokenomics(project_names: list, project_tier: str = None):
    """
    Получает информацию о проекте и связанных метриках по категории и токену пользователя.
    Берёт только уникальные проекты (не повторяя coin_name).
    """

    try:
        tokenomics_data_list = []
        projects = []
        seen_coin_names = set()  # множество для отслеживания уже добавленных coin_name

        for project_name in project_names:
            project_name = project_name.strip()

            # Корректный запрос с JOIN через промежуточную таблицу
            projects_data = await get_all(
                Project,
                join_model=lambda q: q.join(project_category_association)
                .join(Category)
                .filter(
                    Category.category_name == project_name,
                ),
            )

            if project_tier and project_tier != "Нет данных":
                projects_data = await get_all(
                    Project,
                    join_model=lambda q: q.join(project_category_association)
                    .join(Category)
                    .filter(
                        Category.category_name == project_name,
                        Project.tier == project_tier,
                    ),
                )

            if not projects_data:
                logger.warning(f"Проект с именем {project_name} не найден.")
                continue

            # Добавим все подходящие проекты в общий список (но без повторения coin_name)
            filtered_projects = []
            for p in projects_data:
                if p.coin_name not in seen_coin_names:
                    seen_coin_names.add(p.coin_name)
                    filtered_projects.append(p)
                else:
                    logger.info(f"Пропущен дубликат coin_name: {p.coin_name}")

            if not filtered_projects:
                logger.info(f"Все проекты для {project_name} оказались дубликатами, пропускаем.")
                continue

            # Сохраняем итоговые отфильтрованные проекты
            projects.append(filtered_projects)

            # Для каждого проекта получаем токеномику
            for project in filtered_projects:
                logger.info(f"Получение данных токеномики для проекта: {project.coin_name}")

                tokenomics_data, _ = await get_or_create(
                    Tokenomics,
                    defaults={"project_id": project.id},
                    project_id=project.id,
                )
                # Оборачиваем в список, как у вас в исходном коде
                tokenomics_data = [tokenomics_data]

                tokenomics_data_list.append((project, tokenomics_data))

                # Если (на всякий случай) tokenomics_data_list пуст (хотя только что добавили),
                # проверим логику
                if not tokenomics_data_list and tokenomics_data:
                    logger.warning("Нет доступных проектов для сравнения.")

                    # Создание новой записи токеномики, если она отсутствует
                    tokenomics_data, _ = await get_or_create(
                        Tokenomics,
                        defaults={"project_id": project.id},
                        project_id=project.id,
                    )
                    logger.warning("Нет доступных проектов для сравнения.")

            logger.info(f"Проекты и токеномика успешно получены для категории {project_name}.")
        return projects, tokenomics_data_list

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def get_twitter_link_by_symbol(symbol: str):
    """
    Получает ссылку на твиттер по символу токена.
    """

    url = f"{COINMARKETCUP_API}info?symbol={symbol}"
    header_params = get_header_params(coin_name=symbol)
    garbage_categories = load_document_for_garbage_list(
        START_TITLE_FOR_GARBAGE_CATEGORIES,
        END_TITLE_FOR_GARBAGE_CATEGORIES,
    )

    async with client_session().get(url, headers=header_params["headers"]) as response:
        if response.status == 200:
            data = await response.json()
            print("CoinMarketCup data: ---", data)
            if symbol in data["data"]:
                project_data = data["data"][symbol]

                # Извлекаем основную информацию
                description = project_data.get("description", None)
                lower_name = project_data.get("name", None)
                urls = project_data.get("urls", {})
                twitter_links = urls.get("twitter", [])

                # Извлекаем категории проекта
                tag_names = project_data.get("tag-names", [])
                tag_groups = project_data.get("tag-groups", [])

                # Фильтруем только категории (CATEGORY)
                # Проверяем, что tag_names и tag_groups не равны None
                if tag_names is None or tag_groups is None:
                    categories = []
                else:
                    categories = [
                        tag
                        for tag, group in zip(tag_names, tag_groups)
                        if group == "CATEGORY" and tag not in garbage_categories
                    ]

                if twitter_links and description and categories:
                    twitter_link = twitter_links[0].lower()
                    return (
                        twitter_link,
                        description,
                        lower_name.lower(),
                        categories,
                    )
                else:
                    print(f"Twitter link for '{symbol}' not found.")
                    return None, None, None, []
            else:
                print(f"Cryptocurrency with symbol '{symbol}' not found.")
                return None, None, None, []
        else:
            print(f"Error retrieving data: {response.status}, {await response.text()}")
            return None, None, None, []


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def get_twitter(name: str):
    """
    Получает информацию о твиттере и твиттерскоре по токену.
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-extensions",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--blink-settings=imagesEnabled=false",
            ]
        )
        context = await browser.new_context()
        page = await context.new_page()

        if type(name) is str:
            coin_name = name
        else:
            coin_name, about, lower_name, categories = name

        await page.route(
            "**/*",
            lambda route: route.continue_() if "image" not in route.request.resource_type else route.abort(),
        )
        coin = coin_name.split("/")[-1]

        try:
            await page.goto(f"{TWITTERSCORE_API}twitter/{coin}/overview/?i=16846")
            await asyncio.sleep(15)
        except Exception as e:
            await context.close()
            await browser.close()
            return None

        try:
            await page.wait_for_selector(SELECTOR_TWITTERSCORE, timeout=30000)
            twitter = await page.locator(SELECTOR_TWITTERSCORE).first.inner_text()
            print("twitter: ", twitter)
        except:
            twitter = None

        try:
            twitterscore = await page.locator("#insideChartCount").inner_text()
        except:
            twitterscore = None

        await context.close()
        await browser.close()

        return {"twitter": twitter, "twitterscore": twitterscore} if twitter or twitterscore else None


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def get_top_100_wallets(user_coin_name: str):
    """
    Получает процент токенов на топ 100 кошельках блокчейна.
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-extensions",
                    "--disable-dev-shm-usage",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--blink-settings=imagesEnabled=false",
                ]
            )

            context = await browser.new_context()
            page = await context.new_page()
            coin = user_coin_name.split("/")[-1]
            logging.info(f"Запрашиваем данные для {coin}")

            try:
                # Переход на страницу richlist
                await page.goto(f"{COINCARP_API}{coin}/richlist/", timeout=120000)

                # Даем время для загрузки JS
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(5)  # Подстраховка

                # Проверяем наличие элемента
                element = await page.query_selector(SELECTOR_TOP_100_WALLETS)

                if not element:
                    logging.warning(f"Элемент {SELECTOR_TOP_100_WALLETS} не найден для {coin}")
                    return None  # Возвращаем None, если элемент не найден

                top_100_text = await element.inner_text()

                logging.info(f"Текст топ-100: {top_100_text}")

                # Преобразуем в число
                try:
                    top_100_percentage = float(top_100_text.replace("%", "").strip())
                    return round(top_100_percentage / 100, 2)
                except ValueError:
                    return None

            except TimeoutError as time_error:
                logging.info(f"Таймаут ожидания страницы: {time_error}")
            except ValueError as value_error:
                logging.info(f"Ошибка обработки данных: {value_error}")
            except Exception as e:
                logging.info(f"Непредвиденная ошибка: {e}")

            finally:
                await context.close()
                await browser.close()

    except AttributeError as attr_error:
        raise AttributeAccessError(f"Ошибка доступа к атрибуту: {attr_error}")
    except KeyError as key_error:
        raise MissingKeyError(f"Отсутствует ключ в данных: {key_error}")
    except ValueError as value_error:
        raise ValueProcessingError(f"Ошибка обработки значения: {value_error}")
    except Exception as e:
        raise ExceptionError(f"Общая ошибка: {e}")


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def fetch_tokenomics_data(url: str) -> list:
    """
    Загружает данные о распределении токенов с указанного URL.
    """
    tokenomics_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-extensions",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--blink-settings=imagesEnabled=false",
            ]
        )

        context = await browser.new_context()
        page = await context.new_page()

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
                                tokenomics_data.append(f"{name} ({percentage})")
                except Exception as e:
                    print(f"❌ Ошибка при поиске таблицы: {e}")

            # Парсим ICO-токеномику (Cryptorank API - ico)
            elif "ico" in url:
                await page.goto(url, wait_until="networkidle")

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

                try:
                    # 1. Ждём появления заголовка с текстом 'Token allocation'
                    token_allocation_header = await page.query_selector(
                        "xpath=//h3[contains(text(), 'Token allocation')]"
                    )
                    if not token_allocation_header:
                        print("❌ 'Token allocation' не найдено на странице.")

                    # 2. Поднимаемся к родительскому контейнеру.
                    tokenomics_container = await token_allocation_header.query_selector(
                        "xpath=ancestor::div[contains(@class, 'sc-c6d4550b-0')]"
                    )
                    if not tokenomics_container:
                        print("❌ Не удалось найти контейнер с классом 'sc-c6d4550b-0'.")

                    # 3. Внутри контейнера ищем список <ul>
                    ul_element = await tokenomics_container.query_selector("ul")
                    if not ul_element:
                        print("❌ Не найден тег <ul> в блоке tokenomics.")

                    # 4. Собираем все элементы <li> внутри <ul>
                    li_elements = await ul_element.query_selector_all("li")
                    if not li_elements:
                        print("❌ Нет элементов <li> внутри <ul>.")

                    print(f"✅ Найдено {len(li_elements)} элементов <li> с распределением.")

                    for li in li_elements:
                        try:
                            print("li: ------", li)
                            # Ищем название (p, например 'Allocated After 2030')
                            name_tag = await li.query_selector("p")
                            name = await name_tag.inner_text() if name_tag else "Не найдено"

                            # Ищем процент (span, например '52.172%')
                            span_tags = await li.query_selector_all("span")
                            if len(span_tags) > 1:
                                percentage = await span_tags[1].inner_text()

                            if name != "Не найдено" and percentage != "Не найдено":
                                tokenomics_data.append(f"{name} ({percentage})")
                            else:
                                print(f"⚠️ Пропущен элемент (нет данных): {await li.inner_html()}")
                        except Exception as e:
                            print(f"❌ Ошибка при обработке <li>: {e}")
                            print(f"🚨 Проблемный элемент: {await li.inner_html()}")

                except Exception as exc:
                    print(f"❌ Сбой при поиске 'Token allocation': {exc}")

            # Для Tokenomist API
            else:
                try:
                    await page.goto(url, wait_until="networkidle")

                    await page.wait_for_selector("div.tokenomics-container > div", timeout=5000)
                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")

                    allocation_divs = soup.select("div.tokenomics-container > div")
                    for div in allocation_divs:
                        try:
                            name = div.select_one("p").get_text(strip=True)
                            percentage = div.select_one("span").get_text(strip=True)
                            tokenomics_data.append(f"{name} ({percentage})")
                        except AttributeError:
                            continue
                except Exception as e:
                    print(f"❌ Ошибка при поиске данных Tokenomist: {e}")

        except Exception as e:
            logging.error(f"🚨 Ошибка при получении данных: {e}")

        finally:
            await context.close()
            await browser.close()

    return tokenomics_data


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def get_percentage_data(lower_name: str, user_coin_name: str):
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

        cryptorank_coin_key = get_crypto_key(user_coin_name)

        # Запрос к Cryptorank
        vesting_url = f"{CRYPTORANK_WEBSITE}price/{lower_name}/vesting"
        if cryptorank_coin_key:
            vesting_url = f"{CRYPTORANK_WEBSITE}price/{cryptorank_coin_key}/vesting"

        tokenomics_data = await fetch_tokenomics_data(vesting_url)

        if not tokenomics_data:
            logging.warning("Не удалось найти таблицу на Cryptorank. Пробуем из ico...")
            ico_url = f"{CRYPTORANK_WEBSITE}ico/{lower_name}"
            if cryptorank_coin_key:
                ico_url = f"{CRYPTORANK_WEBSITE}ico/{cryptorank_coin_key}"

            tokenomics_data = await fetch_tokenomics_data(ico_url)

        if not tokenomics_data:
            logging.warning("Не удалось найти таблицу с заданными заголовками на Cryptorank. Пробуем Tokenomist.ai...")
            tokenomics_data = await fetch_tokenomics_data(f"{TOKENOMIST_API}{lower_name}")

        return tokenomics_data if tokenomics_data else None

    except (AttributeError, KeyError, ValueError) as e:
        raise ExceptionError(str(e))
    except Exception as e:
        raise ExceptionError(str(e))


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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
            logging.error(f"Failed to fetch data: {response.status_code} - {response.text}")

    except Exception as e:
        raise ExceptionError(str(e))

    return description


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def get_fundraise(user_coin_name: str, lower_name: str = None):
    """
    Получение информации о фандрейзе проекта на Cryptorank
    """

    try:
        print(f"get_fundraise {user_coin_name}")
        user_coin_key = get_crypto_key(user_coin_name)
        if not user_coin_key:
            logging.info(f"Токен '{user_coin_name}' не найден в CryptoRank API")
            return None, "-"

        url = f"{CRYPTORANK_WEBSITE}ico/{user_coin_key}"
        response = requests.get(url)

        if response.status_code != 200:
            url = f"{CRYPTORANK_WEBSITE}ico/{lower_name}"
            response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Ищем div, который содержит два <p>, первый из которых "Total Raised"
            funding_divs = soup.find_all("div")

            clean_data = None
            for div in funding_divs:
                p_tags = div.find_all("p")  # Все <p> внутри div

                if len(p_tags) == 2 and p_tags[0].text.strip() == "Total Raised":
                    clean_data = clean_fundraise_data(p_tags[1].text.strip())
                    break  # Нашли нужный div, выходим

            print("Total Raised:", clean_data)

            investors_data = ""
            investors_data_list = []  # Храним инвесторов в списке

            # Ищем абзац <p> или заголовок <h2>, <h3>, содержащий "Investors and Backers"
            investor_heading = soup.find(
                lambda tag: tag.name in ["p", "h2", "h3"] and "Investors and Backers" in tag.get_text(strip=True)
            )

            if investor_heading:
                print(f"🔹 Найден заголовок: {investor_heading.text.strip()}")
            else:
                print("❌ Заголовок 'Investors and Backers' не найден!")

            if investor_heading:
                # Найти следующую таблицу после заголовка
                investors_table = investor_heading.find_next("table")

                if investors_table:
                    investors_rows = investors_table.select("tbody tr")

                    for investor in investors_rows[:5]:  # Ограничение до 5 элементов
                        try:
                            # Извлекаем название инвестора
                            name_tag = investor.select_one("td.sc-7338db8c-0.jHJJVG p.sc-dec2158d-0.jYFsAb")
                            name = name_tag.get_text(strip=True) if name_tag else "Не найдено"

                            # Извлекаем Tier
                            tier_tag = investor.select_one("td.sc-7338db8c-0.hakNfu p.sc-dec2158d-0.jYFsAb")
                            tier = tier_tag.get_text(strip=True) if tier_tag else "Не найдено"

                            investors_data_list.append(f"{name} (Tier: {tier})")

                        except AttributeError as e:
                            print(f"❌ Ошибка при обработке инвестора: {e}")
                            continue

            investors_data = ", ".join(investors_data_list)

            logging.info(f"Инвесторы, fundraise: {investors_data, clean_data}")
            return clean_data, investors_data

        else:
            logging.error(f"Ошибка при получении данных: {response.status_code}")
            return None, "-"

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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
        response = requests.get(
            f"{COINMARKETCUP_API}quotes/latest",
            headers=headers,
            params=parameters,
        )
        data = response.json()
        print("COINMARKETCUP_API: ", data)

        # Проверяем, есть ли "data" в ответе
        if "data" not in data:
            logging.error("Ошибка: ключ 'data' отсутствует в ответе API CoinMarketCap.")
            return None

        # Проверяем, есть ли запрошенный токен в данных
        if user_coin_name not in data["data"]:
            logging.error(f"Ошибка: токен '{user_coin_name}' не найден в API CoinMarketCap.")
            raise MissingKeyError(f"Токен '{user_coin_name}' не найден в данных CoinMarketCap.")

        coin_info = data["data"][user_coin_name]

        # Проверяем наличие ключей перед доступом
        required_keys = ["name", "quote", "circulating_supply", "total_supply"]
        for key in required_keys:
            if key not in coin_info:
                logging.error(f"Ошибка: Отсутствует ключ '{key}' для '{user_coin_name}'.")
                raise MissingKeyError(f"Ошибка: отсутствует ключ '{key}' для '{user_coin_name}'.")

        coin_name = coin_info["name"].lower()
        logging.info(f"{coin_name}, {coin_info['name']}")

        crypto_data = coin_info["quote"].get("USD", {})
        price = crypto_data.get("price", 0)
        market_cap = crypto_data.get("market_cap", 0)
        circulating_supply = coin_info.get("circulating_supply", 0)
        total_supply = coin_info.get("total_supply", 0)

        # Вычисление FDV
        coin_fdv = total_supply * price if price > 0 else None

        return {
            "coin_name": coin_name,
            "circulating_supply": circulating_supply,
            "total_supply": total_supply,
            "price": price,
            "capitalization": market_cap,
            "coin_fdv": coin_fdv,
        }

    except AttributeError as attr_error:
        logging.error(f"Ошибка атрибута: {attr_error}")
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        logging.error(f"Ошибка ключа: {key_error}")
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        logging.error(f"Ошибка обработки значения: {value_error}")
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        logging.error(f"Общая ошибка: {e}")
        raise ExceptionError(str(e))


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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
            highs = [day["high"] for day in daily_data if day["high"] > 0.00001]
            lows = [day["low"] for day in daily_data if day["low"] > 0.00001]
            max_price = max(highs)
            min_price = min(lows)

            fail_high = (price / max_price) - 1
            growth_low = price / min_price
        else:
            logging.info("Нет данных от первого запроса CryptoCompare, пробуем с полным названием токена.")

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
                logging.info("Нет данных от CryptoCompare, переключаемся на Binance API.")

                # Попытка получения данных с Binance
                symbol = cryptocompare_params["fsym"] + cryptocompare_params["tsym"]
                max_price, min_price = fetch_binance_data(symbol)

                if max_price and min_price:
                    fail_high = (price / max_price) - 1
                    growth_low = price / min_price
                else:
                    logging.error("Нет данных от Binance API, переключаемся на CoinGecko API.")

                    # Попытка получения данных с CoinGecko
                    token_id = get_coingecko_id_by_symbol(cryptocompare_params["fsym"])
                    max_price, min_price = fetch_coingecko_max_min_data(token_id, cryptocompare_params["tsym"])

                    if max_price and min_price:
                        fail_high = (price / max_price) - 1
                        growth_low = price / min_price

        # Возврат данных в зависимости от типа запроса
        if request_type == "top_and_bottom":
            return None, None, max_price, min_price
        elif request_type == "market_metrics":
            return fail_high, growth_low, None, None
        else:
            return fail_high, growth_low, max_price, min_price

    except Exception as e:
        logging.error(f"Ошибка при получении данных: {str(e)}")
        return None  # Возвращаем None в случае ошибки


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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
            raise ValueProcessingError("CoinGecko API не вернул данные о ценах.")

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

        return twitter_response.get("twitter"), int(twitter_response.get("twitterscore", 0))

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


async def fetch_fundraise_data(user_coin_name: str, lower_name: str = None):
    """
    Получение данных о фандрейзе токена.
    """

    try:
        clean_data, investors = await get_fundraise(user_coin_name, lower_name)
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


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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
                        print("last_entry: ", last_entry)
                        last_tvl = last_entry.get("tvl", 0)
                        return float(last_tvl)
                    else:
                        logging.error(f"No TVL data found for {coin_name} using base_url.")

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
                                print(f"Найден TVL стейкинга ({key}): {staking_tvl}")
                                return staking_tvl

                    logging.error(f"No staking TVL found for {coin_name} using protocol_url.")
                else:
                    logging.error(f"Protocol URL failed for {coin_name}. Status code: {response.status}")
                    return None

        except AttributeError as e:
            raise AttributeAccessError(str(e))
        except KeyError as e:
            raise MissingKeyError(str(e))
        except ValueError as e:
            raise ValueProcessingError(str(e))
        except Exception as e:
            raise ExceptionError(str(e))


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def get_lower_name(user_coin_name: str):
    """
    Получение полного названия криптовалюты в нижнем регистре по тикеру.
    """

    url = f"{COINMARKETCUP_API}info"
    header_params = get_header_params(coin_name=user_coin_name)

    async with aiohttp.ClientSession() as session_local:
        async with session_local.get(url, headers=header_params["headers"]) as response:
            if response.status == 200:
                data = await response.json()
                logging.info(f"{data['data']}")
                if user_coin_name.upper() in data["data"]:
                    lower_name = data["data"][user_coin_name.upper()].get("name", None).lower()

                    return lower_name


def get_top_projects_by_capitalization_and_category(
    tokenomics_data_list: dict,
):
    """
    Получение топ-проектов по капитализации и категории для определенных тикеров.
    """

    top_projects = sorted(
        tokenomics_data_list,
        key=lambda item: item[1][0].capitalization if item[1][0].capitalization else 0,
        reverse=True,
    )[:5]

    return top_projects


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def get_top_projects_by_capitalization(
    project_type: str,
    tickers: list,
    top_n_tickers: int = 5,
    top_n_other: int = 10,
) -> list[str]:
    """
    Получение топ-проектов по капитализации по категориям (например, Layer 1).
    Использует универсальные функции для запросов в базу данных и обрабатывает ошибки с кастомными исключениями.
    """
    try:
        if not isinstance(project_type, str):
            raise ValueProcessingError(
                f"Ожидаемый тип данных для project_type — str, получено: {type(project_type).__name__}"
            )

        if not isinstance(tickers, list) or not all(isinstance(ticker, str) for ticker in tickers):
            raise ValueProcessingError("Тикеры должны быть списком строк.")

        top_ticker_projects = await get_all(
            Project,
            join_model=lambda q: (
                q.select_from(Project)
                .join(Tokenomics, Project.id == Tokenomics.project_id)
                .join(
                    project_category_association,
                    Project.id == project_category_association.c.project_id,
                )
                .join(
                    Category,
                    Category.id == project_category_association.c.category_id,
                )
                .filter(Category.category_name == project_type)
            ),
            coin_name=lambda col: col.in_(tickers),
            order_by=Tokenomics.capitalization.desc(),
            limit=top_n_tickers,
            options=[selectinload(Project.categories)],
        )

        top_other_projects = await get_all(
            Project,
            join_model=lambda q: (
                q.select_from(Project)
                .join(Tokenomics, Project.id == Tokenomics.project_id)
                .join(
                    project_category_association,
                    Project.id == project_category_association.c.project_id,
                )
                .join(
                    Category,
                    Category.id == project_category_association.c.category_id,
                )
                .filter(Category.category_name == project_type)
            ),
            order_by=Tokenomics.capitalization.desc(),
            limit=top_n_other,
            options=[selectinload(Project.categories)],
        )

        # Возвращаем список имен монет
        return [
            project.coin_name
            for project in (top_ticker_projects + top_other_projects)
            if project.cmc_rank and project.cmc_rank < 1000
        ]

    except DatabaseFetchError as e:
        logging.error(f"Ошибка извлечения данных из базы: {e.detail}")
        raise

    except ValueProcessingError as e:
        logging.error(f"Ошибка обработки значений: {e}")
        raise

    except Exception as e:
        logging.error(f"Неизвестная ошибка: {e}")
        raise ExceptionError(f"Критическая ошибка в get_top_projects_by_capitalization: {e}")


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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
    cryptocompare_params_with_full_coin_name = get_cryptocompare_params_with_full_name(lower_name.upper())

    if (
        investing_metrics
        and not all(
            [
                getattr(investing_metrics, "fundraise", None),
                getattr(investing_metrics, "fund_level", None),
                getattr(investing_metrics, "fund_level", "-") not in ["-", None, ""],
            ]
        )
    ) or not investing_metrics:
        tasks.append((fetch_fundraise_data(project.coin_name, lower_name), "investing_metrics"))

    if (
        social_metrics
        and not all(
            [
                getattr(social_metrics, "twitter", "") not in ["-", None, ""],
                getattr(social_metrics, "twitterscore", "") not in ["-", None, ""],
            ]
        )
    ) or not social_metrics:
        tasks.append((fetch_twitter_data(twitter_name), "social_metrics"))

    if (
        funds_profit
        and not all(
            [
                getattr(funds_profit, "distribution", None),
                getattr(funds_profit, "distribution", "") not in ["--)", "-", "-)", ""],
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

    if (manipulative_metrics and not getattr(manipulative_metrics, "top_100_wallet", None)) or not manipulative_metrics:
        tasks.append((fetch_top_100_wallets(lower_name), "manipulative_metrics"))

    if (network_metrics and not getattr(network_metrics, "tvl", None)) or not network_metrics:
        tasks.append((fetch_tvl_data(lower_name), "network_metrics"))

    # Выполняем задачи
    if tasks:
        task_results = []
        for task, (model_name) in tasks:
            print(f"Запуск задачи для модели: {model_name}")
            task_results.append(task)

        task_results = await asyncio.gather(*task_results)

        logging.info(f"Результаты выполнения задач: {task_results}")
        for (result, (_, model_name)) in zip(task_results, tasks):
            if model_name not in results:
                results[model_name] = []
            results[model_name].append(result)

    if results:
        for model_name, data_list in results.items():
            model = model_mapping.get(model_name)
            if not model:
                logging.warning(f"Модель для {model_name} не найдена. Пропускаем.")
                continue

            for data in data_list:
                data_dict = map_data_to_model_fields(model_name, data)
                filtered_data_dict = {k: v for k, v in data_dict.items() if v is not None and v != "N/A"}

                if not filtered_data_dict:
                    logging.warning(f"Данные после фильтрации пустые, пропускаем сохранение: {data}")
                    continue

                # Сохраняем в базу данных
                await update_or_create(model, project_id=project.id, defaults=filtered_data_dict)
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


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
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
    investors_tier: Optional[str] = None,
    tokenomic_answer: Optional[str] = None,
    categories: Optional[str] = None,
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

    print("all_data_string_for_flags_agent: ---", all_data_string_for_flags_agent)

    if (user_id and user_language == "RU") or (language and language == "RU"):
        language = "RU"
        flags_answer = await agent_handler("flags", topic=all_data_string_for_flags_agent, language=language)
        flags_answer += (
            f"\n\nДанные для анализа\n"
            f"- Категории: {categories}\n\n"
            f"- Тир проекта: {tier}\n"
            f"- Тикер монеты: {project.coin_name if project and project.coin_name else 'N/A'}\n"
            f"- Капитализация: ${round(tokenomics_data.capitalization, 2) if tokenomics_data and tokenomics_data.capitalization else 'N/A'}\n"
            f"- Фандрейз: ${round(investing_metrics.fundraise) if investing_metrics and investing_metrics.fundraise else 'N/A'}\n"
            f"- Количество подписчиков: {social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A'} (Twitter: {REPLACED_PROJECT_TWITTER.get(twitter_link[0], twitter_link[0])})\n"
            f"- Twitter Score: {social_metrics.twitterscore if social_metrics and social_metrics.twitterscore else 'N/A'}\n"
            f"- Инвесторы: {investing_metrics.fund_level if investing_metrics and investing_metrics.fund_level else 'N/A'}\n"
            f"- Общий уровень инвесторов: {investors_tier}\n"
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
    elif (user_id and user_language == "ENG") or (language and language == "ENG"):
        language = "ENG"
        flags_answer = await agent_handler("flags", topic=all_data_string_for_flags_agent, language=language)
        flags_answer += (
            f"\n\nData to analyze\n"
            f"- Categories: {categories}\n\n"
            f"- Coin Ticker: {project.coin_name if project and project.coin_name else 'N/A'}\n"
            f"- Capitalization: ${round(tokenomics_data.capitalization, 2) if tokenomics_data and tokenomics_data.capitalization else 'N/A'}\n"
            f"- Fundraise: ${round(investing_metrics.fundraise) if investing_metrics and investing_metrics.fundraise else 'N/A'}\n"
            f"- Number of Twitter subscribers: {social_metrics.twitter if social_metrics and social_metrics.twitter else 'N/A'} (Twitter: {REPLACED_PROJECT_TWITTER.get(twitter_link[0], twitter_link[0])})\n"
            f"- Twitter Score: {social_metrics.twitterscore if social_metrics and social_metrics.twitterscore else 'N/A'}\n"
            f"- Investors: {investing_metrics.fund_level if investing_metrics and investing_metrics.fund_level else 'N/A'}\n"
            f"- Investors tier: {investors_tier}\n"
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
    labels = RATING_LABELS.get(language, RATING_LABELS["EN"])  # Язык по умолчанию — английский

    if final_score < 50:
        return labels["bad"]
    elif 50 <= final_score <= 100:
        return labels["neutral"]
    elif 101 <= final_score <= 200:
        return labels["good"]
    else:
        return labels["excellent"]


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def fetch_categories():
    """
    Получает список категорий криптовалют с CoinMarketCap API.
    """
    url = f"{COINMARKETCUP_API}categories"
    headers = {"X-CMC_PRO_API_KEY": API_KEY}

    async with client_session().get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return [item["name"] for item in data.get("data", [])]
        else:
            logging.error(f"Ошибка API CoinMarketCap: {response.status}")
            return []


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def fetch_top_tokens(limit: int):
    """
    Получает список топ-токенов CoinMarketCap с опциональным лимитом.
    """
    url = f"{COINMARKETCUP_API}listings/latest?limit={limit}"
    headers = {"X-CMC_PRO_API_KEY": API_KEY}

    async with client_session().get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return [{"symbol": item["symbol"], "cmc_rank": item.get("cmc_rank")} for item in data.get("data", [])]
        else:
            logging.error(f"Ошибка API CoinMarketCap: {response.status}")
            return []


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def fetch_token_quote(token_symbol: str) -> dict:
    """
    Получает подробную информацию для конкретного токена по его символу,
    включая рейтинг (cmc_rank), используя endpoint cryptocurrency/quotes/latest.

    Аргументы:
      - token_symbol: строка-символ токена (например, "BTC").

    Возвращает:
      - Словарь с ключами "symbol" и "cmc_rank", либо пустой словарь при ошибке.
    """

    url = f"{COINMARKETCUP_API}quotes/latest?symbol={token_symbol}"
    headers = {"X-CMC_PRO_API_KEY": API_KEY}

    async with client_session().get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            token_info = data.get("data", {}).get(token_symbol, {})
            return {
                "symbol": token_symbol,
                "cmc_rank": token_info.get("cmc_rank"),
            }
        else:
            logging.error(f"Ошибка API CoinMarketCap для {token_symbol}: {response.status}")
            return {}
