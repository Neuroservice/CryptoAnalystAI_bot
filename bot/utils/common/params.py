from bot.utils.common.config import API_KEY


def get_header_params(coin_name: str):
    """
    Получает заголовки для запроса к CoinMarketCap API.
    """

    return {
        "parameters": {"symbol": coin_name, "convert": "USD"},
        "headers": {
            "X-CMC_PRO_API_KEY": API_KEY,
            "Accepts": "application/json",
        },
    }


def get_cryptocompare_params(user_coin_name: str):
    """
    Получает параметры для запроса к Compare API.
    """

    return {"fsym": user_coin_name, "tsym": "USD", "limit": 730}


def get_cryptocompare_params_with_full_name(full_coin_name: str):
    """
    Получает параметры для запроса к Compare API с полным названием монеты.
    """

    return {"fsym": full_coin_name, "tsym": "USD", "limit": 730}
