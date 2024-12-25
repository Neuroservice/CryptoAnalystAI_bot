from dotenv import load_dotenv
import os

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
API_KEY = os.getenv("COINMARKETCAP_APIKEY")
COINMARKETCAP_API_URL = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
GPT_SECRET_KEY_FASOLKAAI = os.getenv("GPT_SECRET_KEY_FASOLKAAI")
engine_url = os.getenv("ENGINE_URL")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

REDIS_HOST = os.getenv("DB_HOST")
REDIS_PORT = 6379

S3_URL = os.getenv("S3_URL")
S3_AWS_STORAGE_BUCKET_NAME = os.getenv("S3_AWS_STORAGE_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_PUBLIC_PATH_STYLE_URL = os.getenv("S3_PUBLIC_PATH_STYLE_URL")
S3_PUBLIC_VIRTUAL_HOSTED_STYLE_URL = os.getenv("S3_PUBLIC_VIRTUAL_HOSTED_STYLE_URL")
