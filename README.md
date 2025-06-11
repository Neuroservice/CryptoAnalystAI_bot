# 🤖 CryptoAnalystAI Bot

### 1. Project Overview
CryptoAnalystAI is an advanced Telegram bot that provides insightful crypto analytics powered by GPT-4o-mini and LangChain. Designed for traders, analysts, and enthusiasts, it enables fast research and dialogue on any project.

### 2. What the Bot Can Do
- Provides both basic and advanced analytics of top 1000 CoinMarketCap projects  
- Allows users to add and track custom tokens  
- Stores analysis history for each user  
- Supports conversation in English and Russian  

### 3. Why It’s Useful
CryptoAnalystAI combines automation with natural interaction. It's accessible, intuitive, and significantly speeds up project due diligence directly inside Telegram.

### 4. Technologies & Libraries
- Python  
- aiogram, aiohttp, requests  
- beautifulsoup4, playwright  
- langchain, OpenAI GPT-4o-mini  
- PostgreSQL, psycopg2-binary  
- Redis  

### 5. Required Configuration (.env)
```env
API_TOKEN=your_telegram_bot_token_here
COINMARKETCAP_APIKEY=your_coinmarketcap_api_key_here
GPT_SECRET_KEY_FASOLKAAI='your_openai_secret_key_here'
CRYPTORANK_API_KEY=your_cryptorank_api_key_here

DB_ENGINE=postgresql+asyncpg
DB_HOST=your_database_host_here
DB_PORT=your_database_port_here
DB_NAME=your_database_name_here
DB_USER=your_database_user_here
DB_PASSWORD=your_database_password_here
ENGINE_URL=postgresql+asyncpg://your_database_user:your_database_password@your_database_host:your_database_port/your_database_name

PGADMIN_DEFAULT_EMAIL=your_pgadmin_email_here
PGADMIN_DEFAULT_PASSWORD=your_pgadmin_password_here

DATABASE_URL=postgresql://your_database_user:your_database_password@your_database_host:your_database_port/your_database_name

REDIS_HOST=your_redis_host_here
REDIS_PORT=your_redis_port_here

S3_URL=https://s3.your-provider.com
S3_AWS_STORAGE_BUCKET_NAME=your_bucket_name
S3_REGION=your_s3_region
S3_ACCESS_KEY=your_s3_access_key
S3_SECRET_KEY=your_s3_secret_key
S3_PUBLIC_PATH_STYLE_URL=https://s3.your-provider.com/your_bucket/
S3_PUBLIC_VIRTUAL_HOSTED_STYLE_URL=https://your_bucket.s3.your-provider.com

LANGCHAIN_TRACING_V2=true_or_false
LANGCHAIN_ENDPOINT="your_langchain_endpoint_here"
LANGCHAIN_API_KEY="your_langchain_api_key_here"
LANGCHAIN_PROJECT="your_langchain_project_name_here"
```

### 6. Local Installation
```bash
git clone https://github.com/Neuroservice/CryptoAnalystAI_bot.git
cd CryptoAnalystAI_bot

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env  # or create .env manually
python app.py
```

### 7. Docker Setup
```bash
docker build -t cryptoanalystai_bot .
docker run --env-file .env cryptoanalystai_bot
```

### 8. Authors

- **Dmitriy Kulaga** — [GitHub](https://github.com/DmitriyKuladmed), [Telegram](https://t.me/kuladmedDm)  
- **Founder and CEO of BeanAI — Vladguru** — [GitHub](https://github.com/vladguru), [Telegram](https://t.me/vladguru_AI)

If you have any questions or ideas, contact the authors!
