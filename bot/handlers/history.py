import logging
import traceback
import zipfile
import matplotlib

from io import BytesIO
from aiogram import Router, types
from aiogram.types import BufferedInputFile
from fpdf import FPDF

from bot.database.db_operations import get_all, get_user_from_redis_or_db
from bot.database.models import Calculation
from bot.utils.common.consts import CALC_HISTORY_TEXT_RU, CALC_HISTORY_TEXT_ENG
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.resources.files_worker.pdf_worker import create_pdf_file
from bot.utils.common.sessions import session_local, redis_client

history_router = Router()
matplotlib.use("Agg")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@history_router.message(
    lambda message: message.text == CALC_HISTORY_TEXT_RU
    or message.text == CALC_HISTORY_TEXT_ENG
)
async def history_command(message: types.Message):
    """
    Хендлер для обработки пункта главного меню 'История расчетов'.
    Создает архив с последними 5 расчетами и предлагает скачать его пользователю.
    """

    user_id = message.from_user.id
    user_data = await get_user_from_redis_or_db(user_id)
    language = user_data.get("language", "ENG")

    await message.answer(
        await phrase_by_user("wait_for_zip", user_id, session_local)
    )

    try:
        last_calculations = await get_all(model=Calculation, user_id=user_id)

        # Сортируем расчеты и берем последние 5
        last_calculations = sorted(
            last_calculations, key=lambda calc: calc.date, reverse=True
        )[:5]

        if not last_calculations:
            await phrase_by_user(
                "no_calculations", message.from_user.id, session_local
            )
            return

        zip_buffer = BytesIO()

        with zipfile.ZipFile(
            zip_buffer, "w", zipfile.ZIP_DEFLATED
        ) as zip_archive:
            for i, calculation in enumerate(last_calculations, start=1):
                pdf = FPDF(orientation="P")
                readable_date = calculation.date.strftime("%Y-%m-%d_%H-%M-%S")
                file_name = f"calculation_{readable_date}.pdf"
                pdf.add_page()
                pdf_output = BytesIO()
                pdf.output(pdf_output)
                pdf_output.seek(0)
                pdf_output, extracted_text = create_pdf_file(
                    calculation, language
                )
                zip_archive.writestr(file_name, pdf_output.getvalue())

        zip_buffer.seek(0)

        await message.answer_document(
            BufferedInputFile(
                zip_buffer.read(),
                filename=f"{await phrase_by_user('calculations_history', message.from_user.id, session_local)}",
            )
        )

    except Exception:
        error_details = traceback.format_exc()
        await message.answer(
            f"{await phrase_by_user('error_common', message.from_user.id, session_local)} {error_details}"
        )
