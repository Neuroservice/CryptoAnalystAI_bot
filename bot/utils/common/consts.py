import re

from bot.utils.common.config import engine_url
from bot.database.models import (
    BasicMetrics,
    InvestingMetrics,
    SocialMetrics,
    Tokenomics,
    FundsProfit,
    TopAndBottom,
    MarketMetrics,
    ManipulativeMetrics,
    NetworkMetrics,
)


# Телеграм Фасольки-бота
FASOLKA_TG = "https://t.me/FasolkaAI_bot"


LOCAL_BACKUP_DIR = "\\home\\CryptoAnalyst_bot\\fasolka_backups"
BUCKET = "c462de58-1673afa0-028c-4482-9d49-87f46960a44f"
PREFIX = "fasolka_backups/"


PROJECT_ANALYSIS_RU = "Анализ проектов"
PROJECT_ANALYSIS_ENG = "Project analysis"
NEW_PROJECT = "Пожалуйста, выберите новый проект для расчета."
LISTING_PRICE_BETA_RU = "Блок анализа цены на листинге (бета)"
LISTING_PRICE_BETA_ENG = "Block of price analysis on the listing (beta)"
LIST_OF_TEXT_FOR_REBALANCING_BLOCK = [
    "блок ребалансировки портфеля",
    "block of portfolio rebalancing",
]
LIST_OF_TEXT_FOR_ANALYSIS_BLOCK = [
    "блок анализа и оценки проектов",
    "block of projects analysis and evaluation",
]
DONATE_TEXT_RU = "Донат"
DONATE_TEXT_ENG = "Donate"
HELP_TEXT_RU = "Помощь"
HELP_TEXT_ENG = "Help"
CALC_HISTORY_TEXT_RU = "История расчетов"
CALC_HISTORY_TEXT_ENG = "Calculation History"


# Пути к файлам
DATABASE_URL = engine_url

# LOGO_PATH = "C:\\Users\\dimak\\PycharmProjects\\Crypto-Analyst\\bot\\media\\fasolka.jpg"
LOGO_PATH = "/app/bot/media/fasolka.jpg"

# TIMES_NEW_ROMAN_PATH = "C:\\Users\\dimak\\PycharmProjects\\Crypto-Analyst\\fonts\\TimesNewRomanPSMT.ttf"
# TIMES_NEW_ROMAN_BOLD_PATH = "C:\\Users\\dimak\\PycharmProjects\\Crypto-Analyst\\fonts\\TimesNewRomanPS-BoldMT.ttf"
# TIMES_NEW_ROMAN_ITALIC_PATH = "C:\\Users\\dimak\\PycharmProjects\\Crypto-Analyst\\fonts\\TimesNewRomanPS-ItalicMT.ttf"
TIMES_NEW_ROMAN_PATH = "/app/fonts/TimesNewRomanPSMT.ttf"
TIMES_NEW_ROMAN_BOLD_PATH = "/app/fonts/TimesNewRomanPS-BoldMT.ttf"
TIMES_NEW_ROMAN_ITALIC_PATH = "/app/fonts/TimesNewRomanPS-ItalicMT.ttf"


# Числовые константы
MAX_MESSAGE_LENGTH = 4096


# Документ с промтами
DOCUMENT_ID = "1_NHFo4b4FmWNxZn6ycQsjm_KaWGdG-mHp6SGCjtPvgI"
DOCUMENT_URL = (
    f"https://docs.google.com/document/d/{DOCUMENT_ID}/export?format=txt"
)


# Настройки модели GPT
GPT_MODEL = "gpt-4o-mini-2024-07-18"
TEMPERATURE = 0


# Адрес кошелька
WALLET_ADDRESS = "0x1D99EdC1431f27cF26FF8a464A814Ba2Bb757602"


# Путь к папке с миграциями
MIGRATIONS_DIR = "alembic/versions"


# Регулярные выражения
REVISION_PATTERN = re.compile(r"Revision ID: (\w+)")
REVISES_PATTERN = re.compile(r"Revises: (\w+|None)")
OVERALL_PROJECT_CATEGORY_PATTERN = r'Общая категория проекта:\s*"([^"]+)"'
PROJECT_DESCRIPTION_PATTERN = r"Описание проекта:\s*(.+?)(?=\n\s*\n|$)"
POSITIVE_PATTERN_RU = (
    r"(Положительные характеристики:.*?)(?=\s*Отрицательные характеристики|$)"
)
NEGATIVE_PATTERN_RU = (
    r"(Отрицательные характеристики:.*?)(?=\s*Данные для анализа|$)"
)
POSITIVE_PATTERN_ENG = (
    r"(?i)(Positive Characteristics:.*?)(?=\s*Negative Characteristics|$)"
)
NEGATIVE_PATTERN_ENG = (
    r"(?i)(Negative Characteristics:.*?)(?=\s*Data to analyze|$)"
)
TOKENOMICS_PATTERN_RU = r"Данные для анализа токеномики:\s*"
TOKENOMICS_PATTERN_ENG = r"Data for tokenomic analysis:\s*"
CALCULATIONS_PATTERN_RU = r"(Результаты расчета для.*?)$"
CALCULATIONS_PATTERN_ENG = r"(Calculation results for.*?)$"
COMPARISON_PATTERN_RU = r"Сравнение\s*проекта\s*с\s*другими,\s*схожими\s*по\s*уровню\s*и\s*категории:"
COMPARISON_PATTERN_ENG = r"Comparing\s*the\s*project\s*with\s*others\s*similar\s*in\s*level\s*and\s*category:"


# Токены и их категории
TICKERS = [
    "ME",
    "APT",
    "SEI",
    "SUI",
    "KAS",
    "TIA",
    "FLR",
    "ARB",
    "OP",
    "IMX",
    "MNT",
    "STRK",
    "ZK",
    "POL",
    "TON",
    "ADA",
    "AVAX",
    "ATOM",
    "NEAR",
    "DOT",
    "TRX",
    "APE",
    "XAI",
    "MEME",
    "SHRAP",
    "MAGIC",
    "ACE",
    "BIGTIME",
    "AGI",
    "ZTX",
    "PIXEL",
    "MAVIA",
    "FAR",
    "MRS",
    "CATS",
    "NOT",
    "HMSTR",
    "DOGS",
    "CATI",
    "BLUR",
    "AGLD",
    "WE",
    "MYRIA",
    "LOOKS",
    "OAS",
    "ULTIMA",
    "MPLX",
    "LMWR",
    "FLIX",
    "GF",
    "PANDORA",
    "NFP",
    "ADF",
    "NYM",
    "PYTH",
    "ALT",
    "AXL",
    "ACX",
    "KYVE",
    "CERE",
    "BFIC",
    "SSV",
    "TAO",
    "AI",
    "0X0",
    "PAAL",
    "ALI",
    "CGPT",
    "RSS3",
    "FORT",
    "BICO",
    "XLM",
    "XRP",
    "CPOOL",
    "POLYX",
    "HIFI",
    "RBN",
    "TOKEN",
    "ID",
    "ARKM",
    "L3",
    "ENS",
    "WLD",
    "TOMI",
    "NUM",
    "T",
    "GAL",
    "GG",
    "MOBILE",
    "HONEY",
    "DIMO",
    "EDU",
    "WIFI",
    "CSIX",
    "ONDO",
    "HBAR",
    "ALGO",
    "CYBER",
    "BBL",
    "BTRST",
    "CHEEL",
    "HOOK",
    "ACS",
    "STG",
    "DYDX",
    "ETHFI",
    "HFT",
    "JUP",
    "GMX",
    "OSMO",
    "JTO",
    "MAV",
    "NTRN",
    "DYM",
    "GSWIFT",
]
PROJECT_TYPES = [
    "Layer 1",
    "Layer 2 (ETH)",
    "Layer 1 (OLD)",
    "GameFi / Metaverse",
    "TON",
    "NFT Platforms / Marketplaces",
    "Infrastructure",
    "AI",
    "RWA",
    "Digital Identity",
    "Blockchain Service",
    "Financial sector",
    "SocialFi",
    "DeFi",
    "Modular Blockchain",
]


# Недостающие данные для анализа проекта
FIELD_MAPPING = {
    "- Circulation Supply (циркулирующее предложение)": (
        "tokenomics",
        "circ_supply",
    ),
    "- Total Supply (общее предложение)": ("tokenomics", "total_supply"),
    "- Capitalization (капитализация)": ("tokenomics", "capitalization"),
    "- FDV (fully diluted valuation)": ("tokenomics", "fdv"),
    "- Entry Price (начальная цена)": ("basic_metrics", "entry_price"),
    "- Market Price (рыночная цена)": ("basic_metrics", "market_price"),
    "- Sphere (сфера проекта)": ("basic_metrics", "sphere"),
    "- Fundraise (инвестиции в проект)": ("investing_metrics", "fundraise"),
    "- Funds Level (уровень фондов)": ("investing_metrics", "fund_level"),
    "- Twitter (подписчики)": ("social_metrics", "twitter"),
    "- Twitter Score (рейтинг в Twitterscore проекта)": (
        "social_metrics",
        "twitterscore",
    ),
    "- Distribution (распределение монет)": ("funds_profit", "distribution"),
    "- Lower Threshold (нижнее значение монеты)": (
        "top_and_bottom",
        "lower_threshold",
    ),
    "- Upper Threshold (верхнее значение монеты)": (
        "top_and_bottom",
        "upper_threshold",
    ),
    "- Fail High (падение от верхнего значения)": (
        "market_metrics",
        "fail_high",
    ),
    "- Growth Low (рост от минимального значения)": (
        "market_metrics",
        "growth_low",
    ),
    "- Top 100 Holders (топ-100 холдеров)": (
        "manipulative_metrics",
        "top_100_wallet",
    ),
    "- TVL (вложенные средства)": ("network_metrics", "tvl"),
}


# Словарь соответствий для таблиц в БД
MODEL_MAPPING = {
    "basic_metrics": BasicMetrics,
    "investing_metrics": InvestingMetrics,
    "social_metrics": SocialMetrics,
    "tokenomics": Tokenomics,
    "funds_profit": FundsProfit,
    "top_and_bottom": TopAndBottom,
    "market_metrics": MarketMetrics,
    "manipulative_metrics": ManipulativeMetrics,
    "network_metrics": NetworkMetrics,
}


# Списки стейблкоинов и фундаментальных токенов
STABLECOINS = [
    "USDT",
    "USDC",
    "USDE",
    "DAI",
    "FDUSD",
    "USD0",
    "USDD",
    "FRAX",
    "PYUSD",
    "TUSD",
    "USDY",
    "USDJ",
    "USDL",
    "EURS",
    "USTC",
    "USDP",
    "EURC",
    "USDB",
    "SBD",
    "USDX",
    "BUSD",
    "VBUSD",
    "LUSD",
    "GUSD",
    "AEUR",
    "XSGD",
    "EURT",
    "CUSD",
    "EURI",
    "USDG",
    "RSV",
    "SUSD",
    "ZUSD",
    "IDRT",
    "USDV",
]
FUNDAMENTAL_TOKENS = [
    "BTC",
    "ETH",
    "XRP",
]


# Твиттеры проектов для замены
REPLACED_PROJECT_TWITTER = {
    "https://twitter.com/aptos_network": "https://x.com/Aptos",
}


# Оценка проекта
RATING_LABELS = {
    "RU": {
        "bad": "Плохо",
        "neutral": "Нейтрально",
        "good": "Хорошо",
        "excellent": "Отлично",
    },
    "EN": {
        "bad": "Bad",
        "neutral": "Neutral",
        "good": "Good",
        "excellent": "Excellent",
    },
}


# Словарь регулярных выражений для заголовков, которые нужно выделять в отчете
PATTERNS = {
    "RU": [
        r"(Описание проекта:)",
        r"(Проект относится к категории:)",
        r"(Метрики проекта.*?:)",
        r"(Распределение токенов:)",
        r"(Оценка прибыльности инвесторов:)",
        r"(Данные\s*роста/падения\s*токена\s*с\s*минимальных\s*и\s*максимальных\s*значений\s*\(за\s*последние\s*2\s*года\):)",
        r"(Сравнение проекта с другими, схожими по уровню и категории:)",
        r"(Оценка проекта:)",
        r"(Общая оценка проекта [\d.]+ баллов? \(.+?\))",
        r"(«Ред» флаги и «грин» флаги:)",
    ],
    "EN": [
        r"(Project description:)",
        r"(The project is categorized as:)",
        r"(Project metrics.*?:)",
        r"(Token distribution:)",
        r"(Evaluating investor profitability:)",
        r"(Token growth/decline data from minimum and maximum values \(for the last 2 years\):)",
        r"(Comparing the project with others similar in level and category:)",
        r"(Overall evaluation:)",
        r"(Overall project evaluation [\d.]+ points \(.+?\))",
        r"(«Red» flags and «green» flags:)",
    ],
}


# Телеграм Фасольки
AI_LINK = "https://t.me/FasolkaAI_bot"


# Шаблоны для поиска текста на русском и английском
AI_HELP_RU = (
    r"\*\*\*Если\s+Вам\s+не\s+понятна\s+терминология,\s+изложенная\s+в\s+отчете,\s+Вы\s+можете\s+воспользоваться\s+нашим\s+ИИ\s+консультантом\."
    r"\s+https://t\.me/FasolkaAI_bot"
    r"\s+\*\*\*Сформированный\s+ИИ\s+агентом\s+отчет\s+не\s+является\s+финансовым\s+советом\s+или\s+рекомендацией\s+к\s+покупке\s+токена\."
)
AI_HELP_EN = (
    r"\*\*\*If\s+you\s+do\s+not\s+understand\s+the\s+terminology\s+in\s+the\s+report,\s+you\s+can\s+use\s+our\s+AI\s+consultant\."
    r"\s+https://t\.me/FasolkaAI_bot"
    r"\s+\*\*\*The\s+report\s+generated\s+by\s+the\s+AI\s+agent\s+is\s+not\s+financial\s+advice\s+or\s+a\s+recommendation\s+to\s+purchase\s+the\s+token\."
)

# Добавление новых текстов взамен найденных через шаблоны
AI_HELP_RU_SPLIT = (
    r"\*\*\*Если\s+Вам\s+не\s+понятна\s+терминология,\s+изложенная\s+в\s+отчете,\s+Вы\s+можете\s+воспользоваться\s+нашим\s+ИИ\s+консультантом\.\s*"
    r"https://t\.me/FasolkaAI_bot\s*"
    r"\*\*\*Сформированный\s+ИИ\s+агентом\s+отчет\s+не\s+является\s+финансовым\s+советом\s+или\s+рекомендацией\s+к\s+покупке\s+токена\."
)
AI_HELP_EN_SPLIT = (
    r"\*\*\*If\s+you\s+do\s+not\s+understand\s+the\s+terminology\s+in\s+the\s+report,\s+you\s+can\s+use\s+our\s+AI\s+consultant\.\s*"
    r"https://t\.me/FasolkaAI_bot\s*"
    r"\*\*\*The\s+report\s+generated\s+by\s+the\s+AI\s+agent\s+is\s+not\s+financial\s+advice\s+or\s+a\s+recommendation\s+to\s+purchase\s+the\s+token\."
)

# Регулярные выражения для поиска баллов и оценки
PROJECT_OVERALL_SCORE_RU = (
    r"Итоговые баллы проекта:\s*([\d.,]+)\s*баллов?\s*– оценка\s*\"(.+?)\""
)
PROJECT_OVERALL_SCORE_ENG = (
    r"Overall project score:\s*([\d.,]+)\s*points\s*– rating\s*\"(.+?)\""
)
PROJECT_POINTS_RU = r"Общая оценка проекта\s*([\d.]+)\s*баллов?\s*\((.+?)\)"
PROJECT_POINTS_ENG = (
    r"Overall project evaluation\s*([\d.]+)\s*points\s*\((.+?)\)"
)
PROJECT_ANALYSIS = (
    r"Анализ проекта .+?\(\$\w+?\)|Project analysis .+?\(\$\w+?\)"
)


# Константы для оценки метрик
TIER_RANK = {"TIER 1": 1, "TIER 2": 2, "TIER 3": 3, "TIER 4": 4}
TIER_RANK_LIST = ["Tier: 1", "Tier: 2", "Tier: 3", "Tier: 4", "Tier: 5"]
TIER_CRITERIA = {
    "Tier 1": {
        "capitalization": 1_000_000_000,
        "fundraising": 100_000_000,
        "twitter_followers": 500_000,
        "twitter_score": 250,
        "categories": [
            "Layer 1",
            "Layer 2 (ETH)",
            "Financial sector",
            "Infrastructure",
        ],
        "required_investors": {"TIER 1": 1, "TIER 2": 2},
    },
    "Tier 2": {
        "capitalization": 200_000_000,
        "fundraising": 50_000_000,
        "twitter_followers": 100_000,
        "twitter_score": 100,
        "categories": [
            "Layer 1",
            "Layer 2 (ETH)",
            "Financial sector",
            "Infrastructure",
            "Layer 1 (OLD)",
            "DeFi",
            "Modular Blockchain",
            "AI",
            "RWA",
            "Digital Identity",
        ],
        "required_investors": {"TIER 2": 1, "TIER 3": 1},
    },
    "Tier 3": {
        "capitalization": 50_000_000,
        "fundraising": 20_000_000,
        "twitter_followers": 50_000,
        "twitter_score": 50,
        "categories": [
            "Layer 1",
            "Layer 2 (ETH)",
            "Financial sector",
            "Infrastructure",
            "Layer 1 (OLD)",
            "DeFi",
            "Modular Blockchain",
            "AI",
            "RWA",
            "Digital Identity",
            "GameFi / Metaverse",
            "NFT Platforms / Marketplaces",
            "SocialFi",
        ],
        "required_investors": {"TIER 3": 1, "TIER 4": 1},
    },
    "Tier 4": {
        "capitalization": 10_000_000,
        "fundraising": 5_000_000,
        "twitter_followers": 10_000,
        "twitter_score": 20,
        "categories": [
            "TON",
            "Layer 1",
            "Layer 2 (ETH)",
            "Financial sector",
            "Infrastructure",
            "Layer 1 (OLD)",
            "DeFi",
            "Modular Blockchain",
            "AI",
            "RWA",
            "Digital Identity",
            "GameFi / Metaverse",
            "NFT Platforms / Marketplaces",
            "SocialFi",
        ],
        "required_investors": {"TIER 4": 1},
    },
}
FUNDRAISING_DIVISOR = 5_000_000
FOLLOWERS_DIVISOR = 15_000
TWITTER_SCORE_MULTIPLIER = 0.1
TIER_COEFFICIENTS = {
    "Tier 1": 1.00,
    "Tier 2": 0.90,
    "Tier 3": 0.80,
    "Tier 4": 0.70,
    "Tier 5": 0.60,
}
LEVEL_TO_SCORE = {
    1: 100,
    2: 60,
    3: 40,
    4: 20,
    5: 0,
}


# Строки для оценки проекта
RESULT_STRING = (
    "Общая оценка токеномики проекта {project_name}: {total_score} баллов.\n\n"
    "Отдельные набранные баллы в сравнении с другими проектами:\n"
    "{results}."
)
CALCULATIONS_SUMMARY_STR = """
Расчеты:
    Баллы за привлеченные инвестиции: {fundraising_score} баллов.
    Баллы за Уровень инвесторов проекта: {tier_score} баллов.
    Баллы за количество подписчиков в Twitter: {followers_score} баллов.
    Баллы за Twitter Score: {twitter_engagement_score} баллов.
    Баллы от оценки токеномики: {tokenomics_score} баллов.
    Оценка прибыльности фондов: {profitability_score} баллов.

Предварительное общее количество баллов проекта до снижения: {preliminary_score} баллов.
Применен снижающий коэффициент: {tier_coefficient}.
Итоговое общее количество баллов проекта: {final_score} баллов.
"""


# Словарь хранящий метрики для их вставки в PDF-файл
METRICS_MAPPING = {
    "capitalization": {
        "RU": "Капитализация проекта",
        "ENG": "Project capitalization",
    },
    "fdv": {
        "RU": "Полная капитализация проекта (FDV)",
        "ENG": "Fully Diluted Valuation (FDV)",
    },
    "total_supply": {
        "RU": "Общее количество токенов (Total Supply)",
        "ENG": "Total Supply",
    },
    "fundraising": {
        "RU": "Сумма сбора средств от инвесторов (Fundraising)",
        "ENG": "Fundraising",
    },
    "twitter_followers": {
        "RU": "Количество подписчиков на Twitter",
        "ENG": "Twitter followers",
    },
    "twitter_score": {"RU": "Twitter Score", "ENG": "Twitter Score"},
    "tvl": {
        "RU": "Общая стоимость заблокированных активов (TVL)",
        "ENG": "Total Value Locked (TVL)",
    },
    "top_100_wallet": {
        "RU": "Процент нахождения токенов на топ 100 кошельков блокчейна",
        "ENG": "Percentage of tokens on top 100 wallets",
    },
    "investors": {"RU": "Инвесторы", "ENG": "Investors"},
}


# Текстовые константы о недостающей информации
NO_DATA_TEXT = {"RU": "Нет данных", "ENG": "No info"}
NO_COEFFICIENT = [
    "Нет данных, коэффициент не применен",
    "No data, coefficient not applied",
]


# Текст для добавления в отчет модели
DATA_FOR_ANALYSIS_TEXT = "**Данные для анализа токеномики**:\n"


# Словарь полей, по которым проверяется наличие спаршенных метрик
EXPECTED_KEYS = {
    "coin_name",
    "circulating_supply",
    "total_supply",
    "price",
    "capitalization",
    "coin_fdv",
}


# Словарь для маппинга категорий проекта на стандартизированный формат
CATEGORY_MAP = {
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
    "Реальные активы (Real World Assets)": "RWA",
    "Реальные активы": "RWA",
    "Цифровая идентификация, сервисы": "Digital Identity",
    "Блокчейн сервисы": "Blockchain Service",
    "Финансовый сектор": "Financial sector",
    "Социальные сети на блокчейне (SocialFi)": "SocialFi",
    "Социальные сети на блокчейне": "SocialFi",
    "Децентрализованные финансы (DeFi)": "DeFi",
    "Децентрализованные финансы": "DeFi",
    "Модульные блокчейны": "Modular Blockchain",
}


# API для вызова
COINMARKETCUP_API = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/"
COINCARP_API = "https://www.coincarp.com/currencies/"
CRYPTORANK_WEBSITE = "https://cryptorank.io/"
CRYPTORANK_API_URL = "https://api.cryptorank.io/v2/currencies"
TOKENOMIST_API = "https://tokenomist.ai/"
TWITTERSCORE_API = "https://twitterscore.io/"
COINGECKO_API = "https://api.coingecko.com/api/v3/coins/"
CRYPTOCOMPARE_API = "https://min-api.cryptocompare.com/data/v2/histoday"
BINANCE_API = "https://api.binance.com/api/v3/"
LLAMA_API_BASE = "https://api.llama.fi/v2/historicalChainTvl/"
LLAMA_API_PROTOCOL = "https://api.llama.fi/protocol/"


# Селекторы
SELECTOR_TOP_100_WALLETS = (
    ".overflow-right-box .holder-Statistics #holders_top100"
)
SELECTOR_TWITTERSCORE = "span.more-info-data"
SELECTOR_GET_INVESTORS = "p.sc-56567222-0"
SELECTOR_PERCENTAGE_DATA = 'div[class*="overflow-y-auto"]'
SELECTOR_PERCENTAGE_TOKEN = "div.flex.items-center.w-"


# Информация для анализа моделью
ALL_DATA_STRING_FUNDS_AGENT = (
    "Распределение токенов: {funds_profit_distribution}\n"
)
ALL_DATA_STRING_FLAGS_AGENT = (
    "Проект: {project_coin_name}\n"
    "Category: {project_category}\n"
    "Tier agent: {tier_answer}\n"
    "Tokemonic agent: {tokemonic_answer}\n"
    "Funds agent: {funds_answer}\n"
    "Project rating agent: {project_rating_answer}\n"
    "Социальные метрики: Количество подписчиков - {social_metrics_twitter} (twitter link: {twitter_link}), Twitter Score - {social_metrics_twitterscore}"
)
