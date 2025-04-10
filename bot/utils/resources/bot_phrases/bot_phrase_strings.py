calculations_choices = {
    "RU": (
        "Результаты расчета для {user_coin_name} в сравнении с {project_coin_name}:\n"
        "Возможный прирост токена (в %): {growth:.2f}%\n"
        "Ожидаемая цена токена: {fair_price}\n\n"
    ),
    "ENG": (
        "Calculation results for {user_coin_name} compared to {project_coin_name}:\n"
        "Possible token growth (in %): {growth:.2f}%\n"
        "The expected price of the token: {fair_price}\n\n"
    ),
}
phrase_dict = {
    "RU": {
        "hello_phrase": "Привет! Это блок с анализом крипто-проектов. Выбери действие из меню ниже:",
        "file_format": "Выберите формат файла: PDF или Excel?",
        "rebalancing_input_token": "Введите тикер токена (например SOL, SUI):",
        "analysis_input_token": "Введите тикер токена (например STRK, SUI):",
        "wait_for_calculations": "Делаю расчеты⏳\nЭто может занять некоторое время...",
        "wait_for_zip": "Создаю архив с расчетами⏳\nЭто может занять некоторое время...",
        "calculations_end": "Завершение расчетов. Чтобы начать снова пользоваться ботом, введите команду /start.",
        "stablecoins_answer": "Вы выбрали стейблкоин. Он плохо подходит для инвестирования, так как его стоимость фиксирована. Попробуйте другой токен.",
        "fundamental_tokens_answer": "Вы выбрали фундаментальный токен. Он подходит для долгосрочных инвестиций на 5 лет и более.",
        "scam_tokens_answer": "Данный проект определен командой к категории 'Повышенные риски, возможный скам'",
        "input_next_token_for_analysis": "Введите тикер следующего токена (например STRK, SUI) или введите /exit для завершения:",
        "input_next_token_for_basic_report": "Введите тикер следующего токена (например APT, ZK) или введите /exit для завершения:",
        "overal_project_rating": "Общая оценка проекта:",
        "language_changed": "Ваш язык был изменён на Русский.",
        "no_calculations": "У вас еще нет расчетов.",
        "calculations_history": "История расчетов.zip",
        "model_answer_for_calculations": "Ответ модели по расчету:",
        "tokens_distribution": "Распределение токенов для: ",
        "donate": "Задонатить на развитие проекта можно на наш кошелек:\n\nСети: BNB, ARB, OP, ERC20\n\n",
        "project_analysis_result": "Проведен анализ проекта {lower_name}. Общая оценка проекта {project_score} баллов ({project_rating}). Подробности анализа в файле:",
        "comparing_calculations": "Сравнение проекта с другими, схожими по уровню и категории:",
        "top_bottom_2_years": "Данные роста/падения токена с минимальных и максимальных значений (за последние 2 года):",
        "top_bottom_values": "Текущее значение: ${current_value}\nМинимальные значения: ${min_value}\nМаксимальные значения: ${max_value}",
        "funds_profit_scores": "Оценка прибыльности инвесторов:",
        "ai_help": "***Если Вам не понятна терминология, изложенная в отчете, Вы можете воспользоваться нашим ИИ консультантом.",
        "ai_answer_caution": "***Сформированный ИИ агентом отчет не является финансовым советом или рекомендацией к покупке токена.",
        "analyse_filename": "Анализ проекта {token_name}",
        "project_analysis": "Анализ проекта {lower_name} (${ticker})",
        "project_description": "Описание проекта:",
        "project_category": "Проект относится к категории:",
        "project_metrics": "Метрики проекта (уровень {tier}):",
        "token_distribution": "Распределение токенов:",
        "overall_evaluation": "Оценка проекта:",
        "overall_project_evaluation": "Общая оценка проекта {score} баллов ({rating_text})",
        "flags": "«Ред» флаги и «грин» флаги:",
        "analysis_block_choose": "Выберите блок аналитики:",
        "update_or_create_choose": "Выберите действие:",
        "created_project_success": "✅ Проект создан!",
        "updated_project_success": "🔄 Проект обновлён!",
        "input_categories": "Если каких-либо данных для проекта нет, отправьте '-'.\nВведите категории проекта через запятую (из https://coinmarketcap.com/, например: Layer 1, TRON Ecosystem):",
        "input_market_price": "Введите рыночную цену (из https://coinmarketcap.com/, например: 0.0013):",
        "input_fundraise": "Введите фандрейз (инвестиции в проект) (из https://cryptorank.io/):",
        "input_investors": "Введите инвесторов (в формате: Polychain Capital (Tier: 1), Andreessen Horowitz (Tier: 1)):",
        "input_twitter": "Введите количество подписчиков в Twitter (например: 616K, 1.2M):",
        "input_twitterscore": "Введите баллы TwitterScore (https://twitterscore.io/):",
        "input_circ_supply": "Введите circulating supply (https://coinmarketcap.com/):",
        "input_total_supply": "Введите total supply (https://coinmarketcap.com/):",
        "input_capitalization": "Введите капитализацию (https://coinmarketcap.com/):",
        "input_fdv": "Введите FDV (https://coinmarketcap.com/):",
        "input_distribution": "Введите распределение токенов (например: Rewards & Airdrops (35%) Investors (35%) Founders & Project (30%)):",
        "input_max_price": "Введите максимальное значение цены токена за 2 года:",
        "input_top_100_wallets": "Введите процент токенов на топ 100 кошельках блокчейна (https://www.coincarp.com/, например 75%):",
        "input_tvl": "Введите TVL (из https://defillama.com/):",
        ## Ошибки
        "error_input_token_from_user": "Проверьте правильность введенного тикера токена и попробуйте еще раз.",
        "beta_block": "Данный блок пока что находится в разработке. Попробуйте, пожалуйста, другой блок аналитики.",
        "error_not_valid_input_data": "Пожалуйста, убедитесь, что все данные введены корректно.\nПодробности ошибки:",
        "error_common": "Произошла ошибка.\nПодробности ошибки:",
        "error_file_format_message": "Пожалуйста, выберите формат файла: PDF или Excel.",
        "error_user_not_found": "Пользователь не найден в базе данных.",
        "error_project_inappropriate_category": "Токен {token} не подошел ни под одну из категорий, попробуйте другой.",
        "error_project_not_found": "Проект с таким именем не найден.",
        "no_red_flags": "Нет 'ред' флагов",
        "no_green_flags": "Нет 'грин' флагов",
        "no_description": "Нет описания",
        "no_project_rating": "Данных по баллам не поступило",
        "no_project_score": "Нет данных по оценке баллов проекта",
        "comparisons_error": "Ошибка в расчетах",
        "no_data": "Нет данных",
        "no_token_distribution": "Нет данных по распределению токенов",
        "incorrect_market_price": "❌ Введите корректную цену в формате числа, например: 0.15",
        "incorrect_fundraise": "❌ Введите корректное число для фандрейза",
        "incorrect_investors": "❌ Неверный формат. Пример: Polychain Capital (Tier: 1), Andreessen Horowitz (Tier: 1)",
        "incorrect_twitter": "❌ Введите количество подписчиков в формате 500K, 1.2M и т.д.",
        "incorrect_int": "❌ Введите целое число!",
        "incorrect_circ_supply": "❌ Введите корректное число для circulating supply!",
        "incorrect_total_supply": "❌ Введите корректное число для total supply!",
        "incorrect_capitalization": "❌ Введите корректное число капитализации!",
        "incorrect_fdv": "❌ Введите корректное число FDV!",
        "incorrect_distribution": "❌ Неверный формат распределения. Пример: Rewards & Airdrops (35%), Investors (35%), Founders & Project (30%)",
        "incorrect_price": "❌ Введите корректную цену!",
        "incorrect_top_100_wallets": "❌ Введите корректный процент токенов!",
        "incorrect_tvl": "❌ Введите корректное значение TVL!",
        "dublicate_project": "❌ Проект с таким именем уже существует в базе. Попробуйте другой токен.",
        "error_for_update": "❌ Проект не найден в базе. Пожалуйста, выберите пункт 'Добавить новый проект.'",
        "category_in_garbage_list": "Категория проекта относится к списку категорий, которые нуждаются в дополнительной проверке... Попробуйте другой токен.",
        "not_in_top_cmc": "Вы ввели неправильный тикер токена, либо токен не находится в списке топ 1000 платформы Coin Market Cap и представляет высокие риски для инвестирования",
        "calculation_type_choice": """
Если вы хотите просто рассчитать цену токена, на основании похожих проектов, выберите кнопку 'Блок ребалансировки портфеля'.\n\n
Если хотите полную сравнительную характеристику по токенам и ребалансировку портфеля, выберите кнопку 'Блок анализа и оценки проектов'.
        """,
        "help_phrase": """
Это блок анализа крипто-проектов!\n\n
Вот наши функции:\n
- Расчет и анализ проектов: Вы можете запускать расчеты для различных крипто-проектов. Просто выберите соответствующую опцию, проект, и я помогу вам просчитать ожидаемую цену токена, ожидаемые иксы, и предоставлю полную таблицу для сравнения.\n
- История расчетов: Последние 5 ваших расчетов сохраняются. Вы можете легко просматривать их, что позволяет анализировать изменения и тенденции со временем.\n\n
Как начать работу с ботом:\n
1. Нажмите на кнопку 'Расчет и анализ проектов': Это приведет вас к процессу, где вы сможете вводить необходимые данные для анализа.\n
2. Выберите 'История расчетов': Здесь вы можете увидеть все свои предыдущие результаты и вернуться к ним в любое время.\n
3. Используйте кнопку 'Помощь': Если у вас есть вопросы или вам нужна дополнительная информация о функциональности бота, просто нажмите на 'Помощь'. Я постараюсь ответить на ваши вопросы!\n\n
Система оценивания проектов: (в разработке)\n\n
Также вы можете сменить язык бота, используя команду '/language'.\n
""",
        "investor_profit_text": (
            "($ {fdv} (FDV) * {investors_percent} "
            "(Investors)) / $ {fundraising_amount} (Сумма сбора средств от инвесторов (Fundraising))"
            "= {result_ratio} == {final_score}"
        ),
        "project_rating_details": """
Сумма сбора средств от инвесторов (Fundraising) = {fundraising_score}
Уровень инвесторов Tier {tier} = {tier_score}
Количество подписчиков на Twitter = {followers_score}
Twitter Score = {twitter_engagement_score}
Сравнение проекта с другими, схожими по уровню и категории = {tokenomics_score}
Прибыль инвесторов = {profitability_score}
Рост с минимальных значений и падение с максимальных значений = {preliminary_score}
Процент нахождения токенов на топ 100 кошельков блокчейна = {top_100_percent}
Процент общих заблокированных активов (TVL) = {tvl_percent}
""",
    },
    "ENG": {
        "hello_phrase": "Hello! This is the crypto project analysis block. Choose an action from the menu below:",
        "file_format": "Choose the file format: PDF or Excel?",
        "rebalancing_input_token": "Enter the coin name (for example SOL, SUI):",
        "analysis_input_token": "Enter the token ticker (e.g. STRK, SUI):",
        "wait_for_calculations": "I'm doing the calculations⏳\nThis may take some time...",
        "wait_for_zip": "Creating an archive with the calculations⏳\nThis may take some time...",
        "calculations_end": "Completing the calculations. To start using the bot again, enter the /start command.",
        "stablecoins_answer": "You have chosen a stablecoin. It is not good for investing because its value is fixed. Try another token.",
        "fundamental_tokens_answer": "You have chosen a fundamental token. It is suitable for long-term investments for 5 years or more.",
        "scam_tokens_answer": "This project was categorized by the team as 'Increased risks, possible scam'",
        "input_next_token_for_analysis": "Enter the ticker of the next token (e.g. STRK, SUI) or enter /exit to complete:",
        "input_next_token_for_basic_report": "Enter the ticker of the next token (e.g. APT, ZK) or type /exit to complete:",
        "overal_project_rating": "Overall project evaluation:",
        "language_changed": "Your language has been changed to English.",
        "no_calculations": "You haven't made any calculations yet.",
        "calculations_history": "Calculation History.zip",
        "model_answer_for_calculations": "Model response by calculation:",
        "tokens_distribution": "Distribution of tokens for: ",
        "donate": "You can donate for the development of the project on our wallet:\n\nNetworks: BNB, ARB, OP, ERC20\n\n",
        "project_analysis_result": "The project {lower_name} has been analyzed.The overall project score is {project_score} points ({project_rating}). Details of the analysis are in the file:",
        "comparing_calculations": "Comparing the project with others similar in level and category:",
        "top_bottom_2_years": "Token growth/decline data from minimum and maximum values (for the last 2 years):",
        "top_bottom_values": "Current value: ${current_value}\nMinimum values: ${min_value}\nMaximum values: ${max_value}",
        "funds_profit_scores": "Evaluating investor profitability:",
        "ai_help": "***If you do not understand the terminology in the report, you can use our AI consultant.",
        "ai_answer_caution": "***The report generated by the AI agent is not financial advice or a recommendation to buy a token.",
        "analyse_filename": "Project analysis {token_name}",
        "project_analysis": "Project analysis {lower_name} (${ticker})",
        "project_description": "Project description:",
        "project_category": "The project is categorized as:",
        "project_metrics": "Project metrics (level {tier}):",
        "token_distribution": "Token distribution:",
        "overall_evaluation": "Overall evaluation:",
        "overall_project_evaluation": "Overall project evaluation {score} points ({rating_text})",
        "flags": "«Red» flags and «green» flags:",
        "analysis_block_choose": "Select an analytics block:",
        "update_or_create_choose": "Select action:",
        "created_project_success": "✅ The project has been created!",
        "updated_project_success": "🔄 The project has been updated!",
        "input_categories": "If there is no data for the project, send '-'.\nEnter the project categories separated by commas (from https://coinmarketcap.com/, eg: Layer 1, TRON Ecosystem):",
        "input_market_price": "Enter market price (from https://coinmarketcap.com/, example: 0.0013):",
        "input_fundraise": "Enter fundraise (investment in the project) (from https://cryptorank.io/ico/sui):",
        "input_investors": "Enter investors (in format: Polychain Capital (Tier: 1), Andreessen Horowitz (Tier: 1)):",
        "input_twitter": "Enter the number of Twitter followers (ex: 616K, 1.2M) (from https://cryptorank.io/):",
        "input_twitterscore": "Enter TwitterScore (https://twitterscore.io/):",
        "input_circ_supply": "Input circulating supply (https://coinmarketcap.com/):",
        "input_total_supply": "Input total supply (https://coinmarketcap.com/):",
        "input_capitalization": "Enter capitalization (https://coinmarketcap.com/):",
        "input_fdv": "Input FDV (https://coinmarketcap.com/):",
        "input_distribution": "Enter token distribution (eg: Rewards & Airdrops (35%) Investors (35%) Founders & Project (30%)):",
        "input_max_price": "Enter the maximum token price for 2 years:",
        "input_top_100_wallets": "Enter the percentage of tokens in the top 100 wallets of the blockchain (https://www.coincarp.com/, for example 75%):",
        "input_tvl": "Enter TVL (from https://defillama.com/):",
        ## Ошибки
        "error_input_token_from_user": "Check if the coin entered is correct and try again.",
        "beta_block": "This block is still under development. Please try another analytics block.",
        "error_not_valid_input_data": "Please make sure all data is entered correctly.\nError details:",
        "error_common": "An error has occurred.\nDetails of the error:",
        "error_file_format_message": "Please select the file format: PDF or Excel.",
        "error_user_not_found": "User not found in the database.",
        "error_project_inappropriate_category": "The token {token} did not fit any of the categories, try another one.",
        "error_project_not_found": "Project with this name was not found.",
        "no_red_flags": "No 'red' flags",
        "no_green_flags": "No 'green' flags",
        "no_description": "No description",
        "no_project_rating": "No data on scores were received",
        "no_project_score": "No data available on project scoring",
        "comparisons_error": "Error on comparisons",
        "no_data": "No data",
        "no_token_distribution": "No token distribution data",
        "incorrect_market_price": "❌ Enter the correct price in number format, for example: 0.15",
        "incorrect_fundraise": "❌ Please enter a valid number for fundraising",
        "incorrect_investors": "❌ Incorrect format. Example: Polychain Capital (Tier: 1), Andreessen Horowitz (Tier: 1)",
        "incorrect_twitter": "❌ Enter the number of followers in the format 500K, 1.2M, etc.",
        "incorrect_int": "❌ Enter an integer!",
        "incorrect_circ_supply": "❌ Please enter a correct number for circulating supply!",
        "incorrect_total_supply": "❌ Enter a correct number for total supply!",
        "incorrect_capitalization": "❌ Please enter a correct capitalization number!",
        "incorrect_fdv": "❌ Please enter a correct FDV number!",
        "incorrect_distribution": "❌ Incorrect distribution format. Example: Rewards & Airdrops (35%), Investors (35%), Founders & Project (30%)",
        "incorrect_price": "❌ Enter the correct price!",
        "incorrect_top_100_wallets": "❌ Enter the correct percentage of tokens!",
        "incorrect_tvl": "❌ Please enter a correct TVL value!",
        "dublicate_project": "❌ A project with this name already exists in the database. Try another token.",
        "error_for_update": "❌ Project not found in the database. Please select 'Add new project.'",
        "category_in_garbage_list": "Project category refers to the list of categories that need additional verification... Try a different token.",
        "not_in_top_cmc": "You entered the wrong token ticker, or the token is not in the top 1000 list of the Coin Market Cap platform and poses high risks for investment",
        "calculation_type_choice": """
If you want to simply calculate the token price based on similar projects, choose the 'Block of portfolio rebalancing' button.\n\n
If you want a full comparison of token characteristics, choose the 'Block of projects analysis and evaluation' button.
        """,
        "help_phrase": """
This is a crypto-project analysis bot!\n\n
Here are our functions:\n
- Calculate and analyze projects: You can run calculations for different crypto-projects. Just select the appropriate option, project, and I will help you calculate the expected price of the coin, the expected growth of the coin in percent, and provide a full table for comparison.\n
- History of calculations: Last five of your calculations are saved. You can easily view them, allowing you to analyze changes and trends over time.\n\n
How to start using the bot:\n
1. Click on the 'Calculate and analyze projects' button: This will take you to the calculation process where you can enter necessary data for analysis.\n
2. Choose 'History of calculations': Here you can view all your previous results and return to them at any time.\n
3. Use the 'Help' button: If you have questions or need additional information about the bot's functionality, just click on 'Help'. I will try to answer your questions!\n\n
Project evaluation system: (in development)\n\n\n
You can also change the bot's language by using the '/language' command.\n
""",
        "investor_profit_text": (
            "($ {fdv} (FDV) * {investors_percent} "
            "(Investors)) / $ {fundraising_amount} (Total fundraising amount)"
            "= {result_ratio} == {final_score}"
        ),
        "project_rating_details": """
Total fundraising amount from investors = {fundraising_score}
Investors level Tier {tier} = {tier_score}
Twitter followers count = {followers_score}
Twitter Score = {twitter_engagement_score}
Comparison with other projects of the same level and category = {tokenomics_score}
Investor profitability = {profitability_score}
Growth from minimum values and decline from maximum values = {preliminary_score}
Percentage of tokens on the top 100 blockchain wallets = {top_100_percent}
Percentage of total blocked assets (TVL) = {tvl_percent}
""",
    },
}
