import logging
from aiogram import Router, types
from bot.handlers.start import user_languages

router = Router()


@router.message(lambda message: message.text == 'Помощь' or message.text == 'Help')
async def help_command(message: types.Message):
    if 'RU' in user_languages.values():
        help_text = (
            "Это блок анализа крипто-проектов!\n\n"
            "Вот наши функции:\n"
            "- Расчет и анализ проектов: Вы можете запускать расчеты для различных крипто-проектов. Просто выберите соответствующую опцию, проект, и я помогу вам просчитать ожидаемую цену монеты, ожидаемые иксы, и предоставлю полную таблицу для сравнения.\n"
            "- История расчетов: Последние 5 ваших расчетов сохраняются. Вы можете легко просматривать их, что позволяет анализировать изменения и тенденции со временем.\n\n"
            "Как начать работу с ботом:\n"
            "1. Нажмите на кнопку 'Расчет и анализ проектов': Это приведет вас к процессу, где вы сможете вводить необходимые данные для анализа.\n"
            "2. Выберите 'История расчетов': Здесь вы можете увидеть все свои предыдущие результаты и вернуться к ним в любое время.\n"
            "3. Используйте кнопку 'Помощь': Если у вас есть вопросы или вам нужна дополнительная информация о функциональности бота, просто нажмите на 'Помощь'. Я постараюсь ответить на ваши вопросы!\n"
            "\nТакже вы можете сменить язык бота, используя команду '/language'.\n"
        )
    else:
        help_text = (
            "This is a crypto-project analysis bot!\n\n"
            "Here are our functions:\n"
            "- Calculate and analyze projects: You can run calculations for different crypto-projects. Just select the appropriate option, project, and I will help you calculate the expected price of the coin, the expected growth of the coin in percent, and provide a full table for comparison.\n"
            "- History of calculations: Last five of your calculations are saved. You can easily view them, allowing you to analyze changes and trends over time.\n\n"
            "How to start using the bot:\n"
            "1. Click on the 'Calculate and analyze projects' button: This will take you to the calculation process where you can enter necessary data for analysis.\n"
            "2. Choose 'History of calculations': Here you can view all your previous results and return to them at any time.\n"
            "3. Use the 'Help' button: If you have questions or need additional information about the bot's functionality, just click on 'Help'. I will try to answer your questions!\n\n"
            "\nYou can also change the bot's language by using the '/language' command.\n"
        )
    await message.answer(help_text)
