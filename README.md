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
GPT_SECRET_KEY_FASOLKAAI=your_OpenAI_secret_key
MODEL_NAME=primary_model_name
MODEL_NAME_MEM=memory_model_name

TG_TOKEN=telegram_bot_token
CHANNEL_ID=telegram_channel_id
CHANNEL_LINK=telegram_channel_link

SERVICE_ACCOUNT_FILE=path_to_Google_service_account_file
SPREADSHEET_ID=Google_spreadsheet_id

GRASPIL_API_KEY=Graspil_API_key
TARGET_START_ID_LIMIT=target_start_id_limit
TARGET_START_ID_START=target_start_initial_id
TARGET_START_ID_BLOCK=target_id_block

GOOGLE_API_KEY=Google_API_key
SEARCH_ENGINE_GLOBAL_ID=Google_search_engine_id

LANGCHAIN_TRACING_V2=True_or_False
LANGCHAIN_ENDPOINT=Langchain_endpoint
LANGCHAIN_API_KEY=Langchain_API_key
LANGCHAIN_PROJECT=Langchain_project_name

DB_HOST=database_host
DB_PORT=database_port
DB_NAME=database_name
DB_USER=database_user
DB_PASSWORD=database_user_password
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
