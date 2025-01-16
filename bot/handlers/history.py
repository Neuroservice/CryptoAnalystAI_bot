import logging
import re
import traceback
import zipfile
from io import BytesIO

import matplotlib
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import BufferedInputFile
from fpdf import FPDF
from sqlalchemy import select

from bot.database.models import Calculation
from bot.handlers.start import user_languages
from bot.utils.consts import (
    logo_path,
    async_session,
    patterns,
    ai_help_ru,
    ai_help_ru_split,
    ai_help_en,
    ai_help_en_split,
    times_new_roman_path,
    times_new_roman_bold_path,
    times_new_roman_italic_path
)
from bot.utils.project_data import calculate_expected_x
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.resources.files_worker.pdf_worker import PDF
from bot.utils.validations import extract_old_calculations

history_router = Router()
matplotlib.use('Agg')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoryState(StatesGroup):
    choosing_project = State()
    choosing_analysis_type = State()
    choosing_file_format = State()
    waiting_for_data = State()
    waiting_for_basic_data = State()


@history_router.message(lambda message: message.text == 'История расчетов' or message.text == 'Calculation History')
async def history_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    language = 'RU' if user_languages.get(user_id) == 'RU' else 'ENG'

    await message.answer(phrase_by_user("wait_for_zip", user_id))

    try:
        query = (
            select(Calculation)
            .filter_by(user_id=user_id)
            .order_by(Calculation.date.desc())
            .limit(5)
        )
        result = await async_session.execute(query)
        last_calculations = result.scalars().all()

        if not last_calculations:
            phrase_by_user("no_calculations", message.from_user.id)
            return

        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_archive:
            for i, calculation in enumerate(last_calculations, start=1):
                pdf = FPDF(orientation='P')
                pdf.add_page()
                await create_pdf_file(zip_archive, calculation, async_session, user_id, language)
                pdf_output = BytesIO()
                pdf.output(pdf_output)
                pdf_output.seek(0)

        zip_buffer.seek(0)

        await message.answer_document(BufferedInputFile(zip_buffer.read(), filename=f"{phrase_by_user('calculations_history', message.from_user.id)}"))

    except Exception:
        error_details = traceback.format_exc()
        await message.answer(f"{phrase_by_user('error_common', message.from_user.id)} {error_details}")
    finally:
        await async_session.close()


async def create_pdf_file(zip_file, calc, session, user_id, language):
    readable_date = calc.date.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"calculation_{readable_date}.pdf"
    current_date = calc.date.strftime("%d.%m.%Y")

    pdf = PDF(logo_path=logo_path, orientation='P')
    pdf.set_margins(left=20, top=10, right=20)
    pdf.add_page()
    pdf.add_font("TimesNewRoman", '', times_new_roman_path, uni=True)
    pdf.add_font("TimesNewRoman", 'B', times_new_roman_bold_path, uni=True)
    pdf.add_font("TimesNewRoman", 'I', times_new_roman_italic_path, uni=True)

    agent_answer = calc.agent_answer if calc.agent_answer else "Ответ модели отсутствует"
    pdf.set_font("TimesNewRoman", size=12)
    flags_answer = agent_answer

    if language == "RU":
        match = re.search(r"Общая оценка проекта\s*([\d.]+)\s*баллов?\s*\((.+?)\)", flags_answer)
    else:
        match = re.search(r"Overall project evaluation\s*([\d.]+)\s*points\s*\((.+?)\)", flags_answer)

    if match:
        project_score = float(match.group(1))
        project_rating = match.group(2)
        print(f"Итоговые баллы: {project_score}")
        print(f"Оценка проекта: {project_rating}")
    else:
        project_score = "Данных по баллам не поступило" if language == "RU" else "No data on scores were received"
        project_rating = "Нет данных по оценке баллов проекта" if language == "RU" else "No data available on project scoring"
        print("Не удалось найти итоговые баллы и/или оценку.")

    selected_patterns = patterns["RU"] if language == "RU" else patterns["EN"]
    text_to_parse = flags_answer

    pdf.set_font("TimesNewRoman", size=12)
    pdf.cell(0, 6, f"{'Анализ проекта' if language == 'RU' else 'Project analysis'}", 0, 1, 'L')
    pdf.cell(0, 6, current_date, 0, 1, 'L')
    pdf.ln(6)

    for pattern in selected_patterns:
        match = re.search(pattern, text_to_parse, re.IGNORECASE | re.DOTALL)
        if match:
            start, end = match.span()
            header = match.group(1)

            content_start = end
            next_header_match = None
            for next_pattern in selected_patterns:
                next_header_match = re.search(next_pattern, text_to_parse[end:], re.IGNORECASE)
                if next_header_match:
                    break

            content_end = next_header_match.start() + end if next_header_match else len(text_to_parse)
            content = text_to_parse[content_start:content_end].strip()

            if re.search(ai_help_ru, content, re.DOTALL):
                parts = re.split(ai_help_ru_split, content, maxsplit=1)
                before_text = parts[0].strip()

                pdf.set_font("TimesNewRoman", style="B", size=12)
                pdf.multi_cell(0, 6, header, 0)

                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", size=12)
                if header == "«Ред» флаги и «грин» флаги:":
                    lines = before_text.splitlines()
                    cleaned_lines = []
                    for line in lines:
                        stripped_line = " ".join(line.split())
                        if stripped_line.startswith("-"):
                            cleaned_lines.append(stripped_line)
                        elif cleaned_lines and not cleaned_lines[-1].endswith(":"):
                            cleaned_lines[-1] += f" {stripped_line}"
                        else:
                            cleaned_lines.append(stripped_line)
                    before_text = "\n".join(cleaned_lines)

                if "Отрицательные характеристики:" in before_text:
                    before_text = before_text.replace("Отрицательные характеристики:","\nОтрицательные характеристики:")
                pdf.multi_cell(0, 6, before_text, 0)

                pdf.ln(0.1)

                # Текст с курсивом (фраза и ссылка)
                pdf.set_font("TimesNewRoman", style="I", size=12)
                pdf.multi_cell(0, 6,f"\n\n***Если Вам не понятна терминология, изложенная в отчете, Вы можете воспользоваться нашим ИИ консультантом.",0)
                pdf.ln(0.1)
                # Устанавливаем цвет для ссылки (синий)
                pdf.set_text_color(0, 0, 255)
                pdf.multi_cell(0, 6, "https://t.me/FasolkaAI_bot", 0)

                pdf.set_text_color(0, 0, 0)
                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", style="I", size=12)
                pdf.multi_cell(0, 6,f"\n\n***Сформированный ИИ агентом отчет не является финансовым советом или рекомендацией к покупке токена.",0)
                pdf.ln(0.1)

                # Возвращаем цвет текста к обычному черному
            elif re.search(ai_help_en, content, re.DOTALL):
                parts = re.split(ai_help_en_split, content, maxsplit=1)
                before_text = parts[0].strip()

                pdf.set_font("TimesNewRoman", style="B", size=12)
                pdf.multi_cell(0, 6, header, 0)

                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", size=12)
                if header == "«Red» flags and «green» flags:":
                    lines = before_text.splitlines()
                    cleaned_lines = []
                    for line in lines:
                        stripped_line = " ".join(line.split())
                        if stripped_line.startswith("-"):
                            cleaned_lines.append(stripped_line)
                        elif cleaned_lines and not cleaned_lines[-1].endswith(":"):
                            cleaned_lines[-1] += f" {stripped_line}"
                        else:
                            cleaned_lines.append(stripped_line)
                    before_text = "\n".join(cleaned_lines)

                if "Negative Characteristics:" in before_text:
                    before_text = before_text.replace("Negative Characteristics:", "\nNegative Characteristics:")

                pdf.multi_cell(0, 6, before_text, 0)

                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", style="I", size=12)
                pdf.multi_cell(0, 6,f"\n\n***If you do not understand the terminology in the report, you can use our AI consultant.",0)
                pdf.ln(0.1)
                pdf.set_text_color(0, 0, 255)
                pdf.multi_cell(0, 6, "https://t.me/FasolkaAI_bot", 0)

                pdf.set_text_color(0, 0, 0)
                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", style="I", size=12)
                pdf.multi_cell(0, 6,f"\n\n***The report generated by the AI agent is not financial advice or a recommendation to buy a token.", 0)
                pdf.ln(0.1)
            else:
                pdf.set_font("TimesNewRoman", style="B", size=12)
                pdf.multi_cell(0, 6, header, 0)

                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", size=12)
                content_cleaned = content

                if header in ["Описание проекта:", "Оценка прибыльности инвесторов:", "Project description:", "Evaluating investor profitability:", ]:
                    content_cleaned = " ".join(content.split())

                content_cleaned = extract_old_calculations(content_cleaned, language)
                pdf.multi_cell(0, 6, content_cleaned, 0)

                pdf.ln(6)

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    zip_file.writestr(file_name, pdf_output.read())


async def prepare_row_data(similar_projects, basic_metrics, project, base_tokenomics, user_id):
    row_data = []
    for index, (similar_project, tokenomics_data) in enumerate(similar_projects, start=1):
        for tokenomic in tokenomics_data:
            logging.info(f"{basic_metrics.entry_price, basic_metrics}")
            calculation_result = calculate_expected_x(
                entry_price=basic_metrics.entry_price if basic_metrics.entry_price != 0 else basic_metrics.market_price,
                total_supply=base_tokenomics.total_supply,
                fdv=tokenomic.fdv,
            )

            if "error" in calculation_result:
                raise ValueError(calculation_result["error"])

            fair_price = calculation_result['fair_price']
            fair_price = f"{fair_price:.5f}" if isinstance(fair_price, (int, float)) else "Ошибка в расчетах" if user_languages.get(user_id) == 'RU' else "Error on market"
            expected_x = f"{calculation_result['expected_x']:.5f}"

            row_data.append([
                index,
                project.coin_name,
                similar_project.coin_name,
                basic_metrics.market_price,
                expected_x,
                fair_price
            ])
    return row_data


