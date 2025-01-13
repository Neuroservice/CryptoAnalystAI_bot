import re

from aiohttp import ClientSession
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

dejavu_path = 'D:\\dejavu-fonts-ttf-2.37\\ttf\\DejaVuSansCondensed.ttf'  # Для локалки (обычный)
dejavu_bold_path = 'D:\\dejavu-fonts-ttf-2.37\\ttf\\DejaVuSansCondensed-Bold.ttf'  # Для локалки (жирный)
dejavu_italic_path = 'D:\\dejavu-fonts-ttf-2.37\\ttf\\DejaVuSansCondensed-Oblique.ttf'  # Для локалки (курсив)
times_new_roman_path = 'C:\\Users\\dimak\\PycharmProjects\\Crypto-Analyst\\fonts\\TimesNewRomanPSMT.ttf'  # Для локалки (обычный)
times_new_roman_bold_path = 'C:\\Users\\dimak\\PycharmProjects\\Crypto-Analyst\\fonts\TimesNewRomanPS-BoldMT.ttf'  # Для локалки (жирный)
times_new_roman_italic_path = 'C:\\Users\\dimak\\PycharmProjects\\Crypto-Analyst\\fonts\\TimesNewRomanPS-ItalicMT.ttf'  # Для локалки (курсив)
# dejavu_path = '/app/fonts/DejaVuSansCondensed.ttf'
# dejavu_bold_path = 'D:\\dejavu-fonts-ttf-2.37\\ttf\\DejaVuSansCondensed-Bold.ttf'
# dejavu_italic_path = 'D:\\dejavu-fonts-ttf-2.37\\ttf\\DejaVuSansCondensed-Oblique.ttf'


# Числовые константы
MAX_MESSAGE_LENGTH = 4096


# Адрес кошелька
WALLET_ADDRESS = "0x1D99EdC1431f27cF26FF8a464A814Ba2Bb757602"


# Токены и категории (типы)
tickers = [
    "ME", "APT", "SEI", "SUI", "KAS", "TIA", "FLR", "ARB", "OP", "IMX", "MNT", "STRK", "ZK", "POL",
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
        'allData': 'true'
    }


calculations_choices = {
    'RU': (
        "Результаты расчета для {user_coin_name} в сравнении с {project_coin_name}:\n"
        "Возможный прирост токена (в %): {growth:.2f}%\n"
        "Ожидаемая цена токена: {fair_price}\n\n"
    ),
    'ENG': (
        "Calculation results for {user_coin_name} compared to {project_coin_name}:\n"
        "Possible token growth (in %): {growth:.2f}%\n"
        "The expected price of the token: {fair_price}\n\n"
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


client_session = ClientSession

engine = create_engine(DATABASE_URL)
async_engine = create_async_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
sync_session = Session()
async_session = SessionLocal()

# Папка сохранения бэкапов
BACKUP_FOLDER = "fasolka_backups"


# Данные для ответов:
def prepare_eng_data_for_analysis(
    category_answer, project, tokenomics_data, investing_metrics, social_metrics,
    twitter_link, funds_profit, top_and_bottom, market_metrics, manipulative_metrics,
    network_metrics, tier_answer, funds_answer, tokemonic_answer, comparison_results, tier
):
    return f"\n\nData to analyze\n" \
           f"- Category analysis: {category_answer}\n\n" \
           f"- Tier of project (from function): {tier}\n" \
           f"- Coin Ticker: {project.coin_name if project else 'N/A'}\n" \
           f"- Category: {project.category if project else 'N/A'}\n" \
           f"- Capitalization: ${round(tokenomics_data.capitalization, 2) if tokenomics_data else 'N/A'}\n" \
           f"- Fundraise: ${round(investing_metrics.fundraise) if investing_metrics and investing_metrics.fundraise else 'N/A'}\n" \
           f"- Number of Twitter subscribers: {social_metrics.twitter} (Twitter: {twitter_link[0]})\n" \
           f"- Twitter Score: {social_metrics.twitterscore}\n" \
           f"- Funds tier: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n" \
           f"- Token allocation: {funds_profit.distribution if funds_profit else 'N/A'}\n" \
           f"- Minimum token price: ${round(top_and_bottom.lower_threshold, 2) if top_and_bottom else 'N/A'}\n" \
           f"- Maximum token price: ${round(top_and_bottom.upper_threshold, 2) if top_and_bottom else 'N/A'}\n" \
           f"- Token value growth from a low: {round((market_metrics.growth_low - 1) * 100, 2) if market_metrics else 'N/A'}%\n" \
           f"- Token drop from the high: {round(market_metrics.fail_high * 100, 2) if market_metrics else 'N/A'}%\n" \
           f"- Percentage of coins found on top 100 blockchain wallets: {round(manipulative_metrics.top_100_wallet * 100, 2) if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A'}%\n" \
           f"- Blocked tokens (TVL): {round((network_metrics.tvl / tokenomics_data.capitalization) * 100) if network_metrics and tokenomics_data else 'N/A'}%\n" \
           f"- Project Tier: {tier_answer}\n" \
           f"- Estimation of fund returns: {funds_answer if funds_answer else 'N/A'}\n" \
           f"- Tokenomics valuation: {tokemonic_answer if tokemonic_answer else 'N/A'}\n\n" \
           f"Data for tokenomic analysis:\n{comparison_results}"


def prepare_ru_data_for_analysis(
    category_answer, project, tokenomics_data, investing_metrics, social_metrics,
    twitter_link, funds_profit, top_and_bottom, market_metrics, manipulative_metrics,
    network_metrics, tier_answer, funds_answer, tokemonic_answer, comparison_results, tier):
    return f"\n\nДанные для анализа\n" \
           f"- Анализ категории: {category_answer}\n\n" \
           f"- Тир проекта (из функции): {tier}\n" \
           f"- Тикер монеты: {project.coin_name if project else 'N/A'}\n" \
           f"- Категория: {project.category if project else 'N/A'}\n" \
           f"- Капитализация: ${round(tokenomics_data.capitalization, 2) if tokenomics_data else 'N/A'}\n" \
           f"- Фандрейз: ${round(investing_metrics.fundraise) if investing_metrics and investing_metrics.fundraise else 'N/A'}\n" \
           f"- Количество подписчиков: {social_metrics.twitter} (Twitter: {twitter_link[0]})\n" \
           f"- Twitter Score: {social_metrics.twitterscore}\n" \
           f"- Тир фондов: {investing_metrics.fund_level if investing_metrics else 'N/A'}\n" \
           f"- Распределение токенов: {funds_profit.distribution if funds_profit else 'N/A'}\n" \
           f"- Минимальная цена токена: ${round(top_and_bottom.lower_threshold, 2) if top_and_bottom else 'N/A'}\n" \
           f"- Максимальная цена токена: ${round(top_and_bottom.upper_threshold, 2) if top_and_bottom else 'N/A'}\n" \
           f"- Рост токена с минимальных значений (%): {round((market_metrics.growth_low - 1) * 100, 2) if market_metrics else 'N/A'}\n" \
           f"- Падение токена от максимальных значений (%): {round(market_metrics.fail_high * 100, 2) if market_metrics else 'N/A'}\n" \
           f"- Процент нахождения монет на топ 100 кошельков блокчейна: {round(manipulative_metrics.top_100_wallet * 100, 2) if manipulative_metrics and manipulative_metrics.top_100_wallet else 'N/A'}%\n" \
           f"- Заблокированные токены (TVL): {round((network_metrics.tvl / tokenomics_data.capitalization) * 100) if network_metrics and tokenomics_data else 'N/A'}%\n\n" \
           f"- Тир проекта: {tier_answer}\n" \
           f"- Оценка доходности фондов: {funds_answer if funds_answer else 'N/A'}\n" \
           f"- Оценка токеномики: {tokemonic_answer if tokemonic_answer else 'N/A'}\n\n" \
           f"**Данные для анализа токеномики**:\n{comparison_results}"


replaced_project_twitter = {
    "https://twitter.com/aptos_network": "https://x.com/Aptos",
}


# Слоаврь строк, которые нужно выделять в отчете
patterns = {
    "RU": [
        r"(Описание проекта:)",
        r"(Проект относится к категории:)",
        r"(Метрики проекта \(уровень Tier \d+\):)",
        r"(Распределение токенов:)",
        r"(Оценка прибыльности инвесторов:)",
        r"(Данные\s*роста/падения\s*токена\s*с\s*минимальных\s*и\s*максимальных\s*значений\s*\(за\s*последние\s*2\s*года\):)",
        r"(Сравнение проекта с другими, схожими по уровню и категории:)",
        r"(Оценка проекта:)",
        r"(Общая оценка проекта [\d.]+ баллов? \(.+?\))",
        r"(«Ред» флаги и «грин» флаги:)"
    ],
    "EN": [
        r"(Project description:)",
        r"(The project is categorized as:)",
        r"(Project metrics \(level Tier \d+\):)",
        r"(Token distribution:)",
        r"(Evaluating investor profitability:)",
        r"(Token growth/decline data from minimum and maximum values \(for the last 2 years\):)",
        r"(Comparing the project with others similar in level and category:)",
        r"(Overall evaluation:)",
        r"(Overall project evaluation [\d.]+ points \(.+?\))",
        r"(«Red» flags and «green» flags:)"
    ]
}

ai_help_ru = r"\*\*\*Если\s+Вам\s+не\s+понятна\s+терминология,\s+изложенная\s+в\s+отчете,\s+Вы\s+можете\s+воспользоваться\s+нашим\s+ИИ\s+консультантом\."
ai_help_en = r"\*\*\*If\s+you\s+do\s+not\s+understand\s+the\s+terminology\s+in\s+the\s+report,\s+you\s+can\s+use\s+our\s+AI\s+consultant\."
ai_link = "https://t.me/FasolkaAI_bot"

ai_help_ru_split = re.escape("***Если Вам не понятна терминология, изложенная в отчете, Вы можете воспользоваться\nнашим ИИ консультантом.\nhttps://t.me/FasolkaAI_bot")
ai_help_en_split = re.escape("***If you do not understand the terminology in the report, you can use our AI consultant.\nhttps://t.me/FasolkaAI_bot")
