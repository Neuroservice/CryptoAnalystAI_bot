import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from bot.database.db_operations import get_one
from bot.database.models import Project
from bot.utils.common.bot_states import UpdateOrCreateProject
from bot.utils.common.consts import (
    LIST_OF_TEXT_FOR_UPDATE,
    LIST_OF_TEXT_FOR_CREATE,
    START_TITLE_FOR_GARBAGE_CATEGORIES,
    END_TITLE_FOR_GARBAGE_CATEGORIES,
)
from bot.utils.project_data import save_or_update_full_project_data, fetch_token_quote, fetch_categories
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.resources.files_worker.google_doc import load_document_for_garbage_list
from bot.utils.validations import (
    is_float,
    is_percentage,
    is_valid_investors_format,
    is_valid_distribution_format,
    is_general_number_or_dash,
    parse_general_number_or_none,
    is_valid_number_with_suffix,
)

create_or_update_router = Router()


@create_or_update_router.message(UpdateOrCreateProject.update_or_create_state)
async def update_or_create_chosen(message: types.Message, state: FSMContext):
    """
    Функция, для обработки выбранного пользователем действия с проектом.
    Делает проверку выбранного пользователем пункта меню и вызывает соответствующий блок.
    """

    analysis_type = message.text.lower()
    print("analysis_type:", analysis_type)

    if analysis_type in LIST_OF_TEXT_FOR_CREATE:
        print("тут 1")
        # Вместо жёсткой строки — фраза из словаря
        await message.answer(await phrase_by_user("rebalancing_input_token", message.from_user.id))
        await state.update_data(mode="create")
        await state.set_state(UpdateOrCreateProject.wait_for_project_name)

    elif analysis_type in LIST_OF_TEXT_FOR_UPDATE:
        print("тут 2")
        await message.answer(await phrase_by_user("rebalancing_input_token", message.from_user.id))
        await state.update_data(mode="update")
        await state.set_state(UpdateOrCreateProject.wait_for_project_name)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_project_name)
async def get_project_name(message: types.Message, state: FSMContext):
    """
    Получает название токена и автоматически запрашивает CMC Rank.
    Дополнительно проверяет, существует ли уже проект в БД:
    - Если режим create, но проект уже в БД, отправляем сообщение, что проект уже есть.
    - Если режим update, но проекта нет, отправляем сообщение, что нужно добавить проект сначала.
    """
    project_name = message.text.strip().upper()
    data = await state.get_data()
    mode = data.get("mode", "create")

    print("mode:", mode)

    await state.update_data(project_name=project_name)
    existing_project = await get_one(Project, coin_name=project_name)

    if mode == "create":
        if existing_project:
            return await message.answer(await phrase_by_user("dublicate_project", message.from_user.id))
    else:
        if not existing_project:
            return await message.answer(await phrase_by_user("error_for_update", message.from_user.id))

    token_data = await fetch_token_quote(project_name)

    cmc_rank = token_data.get("cmc_rank")
    if cmc_rank and cmc_rank > 1000:
        return await message.answer(await phrase_by_user("not_in_top_cmc", message.from_user.id))

    await state.update_data(cmc_rank=int(cmc_rank))
    await message.answer(await phrase_by_user("input_categories", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_categories)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_categories)
async def get_categories(message: types.Message, state: FSMContext):
    if message.text.strip() == "-":
        await state.update_data(categories=[])
    else:
        categories = message.text.split(", ")
        all_categories = await fetch_categories()
        garbage_categories = load_document_for_garbage_list(
            START_TITLE_FOR_GARBAGE_CATEGORIES,
            END_TITLE_FOR_GARBAGE_CATEGORIES,
        )
        valid_categories = [cat for cat in all_categories if cat not in garbage_categories]
        valid_project_categories = [cat for cat in categories if cat in valid_categories]
        await state.update_data(categories=valid_project_categories)
    await message.answer(await phrase_by_user("input_market_price", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_market_price)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_market_price)
async def get_market_price(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        # Нет данных
        await state.update_data(market_price=None)
    else:
        if not is_float(text):
            return await message.answer(await phrase_by_user("incorrect_market_price", message.from_user.id))
        await state.update_data(market_price=float(text))

    await message.answer(await phrase_by_user("input_fundraise", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_fundraise)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_fundraise)
async def get_fundraise(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(fundraise=None)
    else:
        if not is_float(text):
            return await message.answer(await phrase_by_user("incorrect_fundraise", message.from_user.id))
        await state.update_data(fundraise=float(text))

    await message.answer(await phrase_by_user("input_investors", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_investors)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_investors)
async def get_investors(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(investors=None)
    else:
        if not is_valid_investors_format(text):
            return await message.answer(await phrase_by_user("incorrect_investors", message.from_user.id))
        await state.update_data(investors=text)

    await message.answer(await phrase_by_user("input_twitter", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_twitter_followers)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_twitter_followers)
async def get_twitter_followers(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(twitter_followers=None)
    else:
        try:
            followers = is_valid_number_with_suffix(text)
            if followers:
                await state.update_data(twitter_followers=text)
            else:
                await state.update_data(twitter_followers=None)
        except Exception:
            return await message.answer(await phrase_by_user("incorrect_twitter", message.from_user.id))

    await message.answer(await phrase_by_user("input_twitterscore", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_twitter_score)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_twitter_score)
async def get_twitter_score(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(twitter_score=None)
    else:
        try:
            await state.update_data(twitter_score=int(text))
        except ValueError:
            return await message.answer(await phrase_by_user("incorrect_int", message.from_user.id))

    await message.answer(await phrase_by_user("input_circ_supply", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_circulating_supply)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_circulating_supply)
async def get_circulating_supply(message: types.Message, state: FSMContext):
    text = message.text.strip()

    if not is_general_number_or_dash(text):
        return await message.answer(await phrase_by_user("incorrect_circ_supply", message.from_user.id))

    value = parse_general_number_or_none(text)
    await state.update_data(circulating_supply=value)

    await message.answer(await phrase_by_user("input_total_supply", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_total_supply)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_total_supply)
async def get_total_supply(message: types.Message, state: FSMContext):
    text = message.text.strip()

    if not is_general_number_or_dash(text):
        return await message.answer(await phrase_by_user("incorrect_total_supply", message.from_user.id))

    value = parse_general_number_or_none(text)
    await state.update_data(total_supply=value)

    await message.answer(await phrase_by_user("input_capitalization", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_capitalization)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_capitalization)
async def get_capitalization(message: types.Message, state: FSMContext):
    text = message.text.strip()

    # Проверяем, что это '-' или валидный формат (K, M, B, запятые)
    if not is_general_number_or_dash(text):
        return await message.answer(await phrase_by_user("incorrect_capitalization", message.from_user.id))

    # Парсим: либо float, либо None
    value = parse_general_number_or_none(text)
    await state.update_data(capitalization=value)

    await message.answer(await phrase_by_user("input_fdv", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_fdv)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_fdv)
async def get_fdv(message: types.Message, state: FSMContext):
    text = message.text.strip()

    # Аналогичная проверка
    if not is_general_number_or_dash(text):
        return await message.answer(await phrase_by_user("incorrect_fdv", message.from_user.id))

    value = parse_general_number_or_none(text)
    await state.update_data(fdv=value)

    await message.answer(await phrase_by_user("input_distribution", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_token_distribution)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_token_distribution)
async def get_token_distribution(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(token_distribution=None)
    else:
        if not is_valid_distribution_format(text):
            return await message.answer(await phrase_by_user("incorrect_distribution", message.from_user.id))
        await state.update_data(token_distribution=text)

    await message.answer(await phrase_by_user("input_max_price", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_max_price)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_max_price)
async def get_max_price(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(max_price=None)
    else:
        if not is_float(text):
            return await message.answer(await phrase_by_user("incorrect_price", message.from_user.id))
        await state.update_data(max_price=float(text))

    await message.answer("Введите минимальное значение цены токена за 2 года:")
    await state.set_state(UpdateOrCreateProject.wait_for_min_price)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_min_price)
async def get_min_price(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(min_price=None)
    else:
        if not is_float(text):
            return await message.answer(await phrase_by_user("incorrect_price", message.from_user.id))
        await state.update_data(min_price=float(text))

    await message.answer(await phrase_by_user("input_top_100_wallets", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_top100_holders)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_top100_holders)
async def get_top100_holders(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(top100_holders=None)
    else:
        if not is_percentage(text):
            return await message.answer(await phrase_by_user("incorrect_top_100_wallets", message.from_user.id))
        await state.update_data(top100_holders=float(text[:-1]))

    await message.answer(await phrase_by_user("input_tvl", message.from_user.id))
    await state.set_state(UpdateOrCreateProject.wait_for_tvl)


@create_or_update_router.message(UpdateOrCreateProject.wait_for_tvl)
async def get_tvl(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(tvl=None)
    else:
        if not is_float(text):
            return await message.answer(await phrase_by_user("incorrect_tvl", message.from_user.id))
        await state.update_data(tvl=float(text))

    data = await state.get_data()
    mode = data.get("mode", "create")

    try:
        project_data = {
            "project_info": {
                "coin_name": data.get("project_name"),
                "cmc_rank": data.get("cmc_rank"),
                "tier": None,
            },
            "basic_metrics": {
                "market_price": data.get("market_price"),
            },
            "investing_metrics": {
                "fundraise": data.get("fundraise"),
                "fund_level": data.get("investors"),
            },
            "social_metrics": {
                "twitter": data.get("twitter_followers"),
                "twitterscore": data.get("twitter_score"),
            },
            "tokenomics": {
                "circ_supply": data.get("circulating_supply"),
                "total_supply": data.get("total_supply"),
                "capitalization": data.get("capitalization"),
                "fdv": data.get("fdv"),
            },
            "funds_profit": {
                "distribution": data.get("token_distribution"),
            },
            "top_and_bottom": {
                "upper_threshold": data.get("max_price"),
                "lower_threshold": data.get("min_price"),
            },
            "market_metrics": {},
            "manipulative_metrics": {
                "top_100_wallet": data.get("top100_holders"),
            },
            "network_metrics": {
                "tvl": data.get("tvl"),
            },
            "categories": data.get("categories", []),
        }

        await save_or_update_full_project_data(project_data)

        msg = "created_project_success" if mode == "create" else "updated_project_success"
        phrase = await phrase_by_user(msg, message.from_user.id)
        await message.answer(phrase)

    except Exception as e:
        logging.info(f"⚠️ Произошла ошибка при сохранении: {e}")
    finally:
        await state.clear()
