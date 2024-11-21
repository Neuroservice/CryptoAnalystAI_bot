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


eng_additional_headers = [
                "Coin Comparison",
                "Sector",
                "Market Price",
                "Fundraising",
                "Tier Funds",
                "Twitter",
                "Twitter Score",
                "Market Cap",
                "Circulating Supply",
                "Total Supply",
                "FDV",
                "Drop High",
                "Rise Low",
                "FDV/Fundraising",
                "Top 100 Wallets",
                "TVL",
                "TVL/FDV",
                "Bottom",
                "Hashrate"
            ]

ru_additional_headers = [
                "Монета сравнения",
                "Сфера",
                "Цена Рынок",
                "Фандрейз",
                "Тир фондов",
                "Твиттер",
                "Твиттерскор",
                "Капитализация",
                "Circ. Supply",
                "Total Supply",
                "FDV",
                "Падение High",
                "Рост Low",
                "FDV/Фандрейз",
                "Топ 100 кошельков",
                "TVL",
                "TVL/FDV",
                "Дно",
                "Хаи"
            ]

headers_mapping = [
    ["Монета сравнения", "Сфера", "Цена Рынок", "Фандрейз"],
    ["Монета сравнения", "Тир фондов"],
    ["Монета сравнения", "Твиттер", "Твиттерскор"],
    ["Монета сравнения", "Капитализация", "Circ. Supply", "Total Supply", "FDV"],
    ["Монета сравнения", "Падение High", "Рост Low"],
    ["Монета сравнения", "FDV/Фандрейз", "Топ 100 кошельков", "TVL", "TVL/FDV", "Дно", "Хаи"]
]


column_widths = [17, 15, 30, 17, 23, 26, 23, 17, 20, 22, 20, 20, 15, 10, 15, 18, 20, 15, 15, 12, 10, 10]