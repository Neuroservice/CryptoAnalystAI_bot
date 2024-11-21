from dotenv import load_dotenv
import os

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
API_KEY = os.getenv("COINMARKETCAP_APIKEY")
COINMARKETCAP_API_URL = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
GPT_SECRET_KEY_FASOLKAAI = os.getenv("GPT_SECRET_KEY_FASOLKAAI")
# engine_url = "sqlite+aiosqlite:///bot/crypto_analysis.db"  # Для прода
engine_url = "sqlite+aiosqlite:///./crypto_analysis.db"  # Для локалки

