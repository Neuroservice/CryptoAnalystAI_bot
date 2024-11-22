import logging

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from bot.database.models import User

router = Router()
user_languages = {}
DATABASE_URL = "sqlite+aiosqlite:///./crypto_analysis.db" # Локалка
# DATABASE_URL = "sqlite+aiosqlite:///bot/crypto_analysis.db" # Прод

engine = create_async_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    class_=AsyncSession,
    bind=engine,
    expire_on_commit=False
)


def language_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text='Русский'),
                KeyboardButton(text='English'),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def main_menu_keyboard(language='RU'):
    if language == 'RU':
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text='Помощь'),
                    KeyboardButton(text='Расчет и анализ проектов'),
                    KeyboardButton(text='История расчетов'),
                ],
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text='Help'),
                    KeyboardButton(text='Project Calculation & Analysis'),
                    KeyboardButton(text='Calculation History'),
                ],
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
    return keyboard


@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(None)

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalars().first()

        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.commit()

        if user.language:
            if user.language == 'RU':
                await message.answer(
                    "Привет! Это блок с анализом крипто-проектов. Выбери действие из меню ниже:",
                    reply_markup=main_menu_keyboard(language='RU')
                )
            else:
                await message.answer(
                    "Hello! This is the crypto project analysis block. Choose an action from the menu below:",
                    reply_markup=main_menu_keyboard(language='ENG')
                )
            user_languages[user.language] = user.language
        else:
            await message.answer(
                "Please choose your language / Пожалуйста, выберите язык:",
                reply_markup=language_keyboard()
            )


@router.message(lambda message: message.text in ['Русский', 'English'])
async def language_choice(message: types.Message):
    user_id = message.from_user.id
    chosen_language = 'RU' if message.text == 'Русский' else 'ENG'

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalars().first()

        if user:
            user.language = chosen_language
            await session.commit()

        user_languages[user.language] = user.language

    if chosen_language == 'RU':
        await message.answer(
            "Привет! Это блок с анализом крипто-проектов. Выбери действие из меню ниже:",
            reply_markup=main_menu_keyboard(language='RU')
        )
    else:
        await message.answer(
            "Hello! This is the crypto project analysis block. Choose an action from the menu below:",
            reply_markup=main_menu_keyboard(language='ENG')
        )
