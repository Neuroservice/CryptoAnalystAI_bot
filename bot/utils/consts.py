from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from bot.config import API_KEY, engine_url
from bot.database.models import (
    BasicMetrics,
    InvestingMetrics,
    SocialMetrics,
    Tokenomics,
    FundsProfit,
    TopAndBottom,
    MarketMetrics,
    ManipulativeMetrics,
    NetworkMetrics
)

# Пути к файлам
DATABASE_URL = engine_url
# DATABASE_URL = "sqlite+aiosqlite:///./crypto_analysis.db"  # Локалка
# DATABASE_URL = "sqlite+aiosqlite:///bot/crypto_analysis.db" # Прод

logo_path = "C:\\Users\\dimak\\PycharmProjects\\Crypto-Analyst\\bot\\fasolka.jpg"  # Для локалки
# logo_path = "/app/bot/fasolka.jpg" # Для прода

dejavu_path = 'D:\\dejavu-fonts-ttf-2.37\\ttf\\DejaVuSansCondensed.ttf'  # Для локалки
# dejavu_path = '/app/fonts/DejaVuSansCondensed.ttf'  # Для прода


# Числовые константы
MAX_MESSAGE_LENGTH = 4096


# Токены и категории (типы)
tickers = [
    "APT", "SEI", "SUI", "KAS", "TIA", "FLR", "ARB", "OP", "IMX", "MNT", "STRK", "ZK", "POL",
    "TON", "ADA", "AVAX", "ATOM", "NEAR", "DOT", "TRX", "APE", "XAI", "MEME", "SHRAP", "MAGIC",
    "ACE", "BIGTIME", "AGI", "ZTX", "PIXEL", "MAVIA", "FAR", "MRS", "CATS", "NOT", "HMSTR", "DOGS",
    "CATI", "BLUR", "AGLD", "WE", "MYRIA", "LOOKS", "OAS", "ULTIMA", "MPLX", "LMWR", "FLIX", "GF",
    "PANDORA", "NFP", "ADF", "NYM", "PYTH", "ALT", "AXL", "ACX", "KYVE", "CERE", "BFIC", "SSV",
    "TAO", "AI", "0X0", "PAAL", "ALI", "CGPT", "RSS3", "FORT", "BICO", "XLM", "XRP", "CPOOL",
    "POLYX", "HIFI", "RBN", "TOKEN", "ID", "ARKM", "L3", "ENS", "WLD", "TOMI", "NUM", "T", "GAL",
    "GG", "MOBILE", "HONEY", "DIMO", "EDU", "WIFI", "CSIX", "ONDO", "HBAR", "ALGO", "CYBER", "BBL",
    "BTRST", "CHEEL", "HOOK", "ACS", "STG", "DYDX", "ETHFI", "HFT", "JUP", "GMX", "OSMO", "JTO",
    "MAV", "NTRN", "DYM", "GSWIFT"
]
project_types = [
    "Layer 1", "Layer 2 (ETH)", "Layer 1 (OLD)", "GameFi / Metaverse", "TON",
    "NFT Platforms / Marketplaces", "Infrastructure", "AI", "RWA", "Digital Identity",
    "Blockchain Service", "Financial sector", "SocialFi", "DeFi", "Modular Blockchain"
]


# Недостающие данные для анализа проекта
field_mapping = {
    "- Circulation Supply (циркулирующее предложение)": ("tokenomics", "circ_supply"),
    "- Total Supply (общее предложение)": ("tokenomics", "total_supply"),
    "- Capitalization (капитализация)": ("tokenomics", "capitalization"),
    "- FDV (fully diluted valuation)": ("tokenomics", "fdv"),
    "- Entry Price (начальная цена)": ("basic_metrics", "entry_price"),
    "- Market Price (рыночная цена)": ("basic_metrics", "market_price"),
    "- Sphere (сфера проекта)": ("basic_metrics", "sphere"),
    "- Fundraise (инвестиции в проект)": ("investing_metrics", "fundraise"),
    "- Funds Level (уровень фондов)": ("investing_metrics", "fund_level"),
    "- Twitter (подписчики)": ("social_metrics", "twitter"),
    "- Twitter Score (рейтинг в Twitterscore проекта)": ("social_metrics", "twitterscore"),
    "- Distribution (распределение монет)": ("funds_profit", "distribution"),
    "- Lower Threshold (нижнее значение монеты)": ("top_and_bottom", "lower_threshold"),
    "- Upper Threshold (верхнее значение монеты)": ("top_and_bottom", "upper_threshold"),
    "- Fail High (падение от верхнего значения)": ("market_metrics", "fail_high"),
    "- Growth Low (рост от минимального значения)": ("market_metrics", "growth_low"),
    "- Top 100 Holders (топ-100 холдеров)": ("manipulative_metrics", "top_100_wallet"),
    "- TVL (вложенные средства)": ("network_metrics", "tvl"),
}
checking_map = {
    "circ_supply": "Circulation Supply (циркулирующее предложение)",
    "total_supply": "Total Supply (общее предложение)",
    "capitalization": "Capitalization (капитализация)",
    "fdv": "FDV (fully diluted valuation)",
    "entry_price": "Entry Price (начальная цена)",
    "market_price": "Market Price (рыночная цена)",
    "sphere": "Sphere (сфера проекта)",
    "fundraise": "Fundraise (инвестиции в проект)",
    "fund_level": "Funds Level (уровень фондов)",
    "twitter": "Twitter (подписчики)",
    "twitterscore": "Twitter Score (рейтинг в Twitterscore проекта)",
    "distribution": "Distribution (распределение монет)",
    "lower_threshold": "Lower Threshold (нижнее значение монеты)",
    "upper_threshold": "Upper Threshold (верхнее значение монеты)",
    "fail_high": "Fail High (падение от верхнего значения)",
    "growth_low": "Growth Low (рост от минимального значения)",
    "top_100_wallet": "Top 100 Holders (топ-100 холдеров)",
    "tvl": "TVL (вложенные средства)"
}


# Словарь соответствий для таблиц в БД
model_mapping = {
    "basic_metrics": BasicMetrics,
    "investing_metrics": InvestingMetrics,
    "social_metrics": SocialMetrics,
    "tokenomics": Tokenomics,
    "funds_profit": FundsProfit,
    "top_and_bottom": TopAndBottom,
    "market_metrics": MarketMetrics,
    "manipulative_metrics": ManipulativeMetrics,
    "network_metrics": NetworkMetrics
}


# Настройки для столбцов, диаграмм
column_widths = [17, 15, 30, 17, 23, 26, 23, 17, 20, 22, 20, 20, 15, 10, 15, 18, 20, 15, 15, 12, 10, 10]
color_palette = ['#FF6633', '#FF33FF', '#00B3E6', '#E6B333', '#3366E6', '#B34D4D', '#6680B3', '#FF99E6', '#FF1A66', '#B366CC', '#4D8000', '#809900']


# Списки стейблкоинов и фундаментальных токенов
stablecoins = [
    "USDT",
    "USDC",
    "BUSD",
    "DAI",
    "TUSD",
    "FRAX",
    "GUSD",
    "USTC",
]
fundamental_tokens = [
    "BTC",
    "ETH",
    "XRP",
]


# Общая константа для языков пользователей
user_languages = {}


# Функция для получения header-ов и parametr-ов
def get_header_params(coin_name):
    return {
        "parameters": {
            'symbol': coin_name,
            'convert': 'USD'
    },
        "headers": {
            'X-CMC_PRO_API_KEY': API_KEY,
            'Accepts': 'application/json'
        }
    }


def get_cryptocompare_params(user_coin_name):
    return {
        'fsym': user_coin_name,
        'tsym': 'USD',
        'limit': 90
    }


calculations_choices = {
    'RU': (
        "Вариант {index}\n"
        "Результаты расчета для {user_coin_name} в сравнении с {project_coin_name}:\n"
        "Возможный прирост токена (в %): {growth:.2f}%\n"
        "Ожидаемая цена токена: {fair_price}\n"
    ),
    'ENG': (
        "Variant {index}\n"
        "Calculation results for {user_coin_name} compared to {project_coin_name}:\n"
        "Possible token growth (in %): {growth:.2f}%\n"
        "The expected price of the token: {fair_price}\n"
    )
}


# Локальная асинхронная сессия
async_engine = create_async_engine(DATABASE_URL, echo=False, pool_timeout=60,  connect_args={"timeout": 60},)
SessionLocal = sessionmaker(
    class_=AsyncSession,
    bind=async_engine,
    expire_on_commit=False
)
session_local = SessionLocal()


engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
sync_session = Session()
async_session = SessionLocal()

# Папка сохранения бэкапов
BACKUP_FOLDER = "fasolka_backups"
