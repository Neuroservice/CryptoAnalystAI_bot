import logging
import re
import traceback
import zipfile
from io import BytesIO

import matplotlib
import xlsxwriter
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import BufferedInputFile
from fpdf import FPDF
from sqlalchemy import select

from bot.database.models import Calculation, User
from bot.handlers.start import user_languages
from bot.utils.consts import (
    column_widths,
    logo_path,
    dejavu_path,
    color_palette, SessionLocal, async_session, patterns, ai_help_ru, ai_help_ru_split, ai_help_en, ai_help_en_split,
    dejavu_bold_path, dejavu_italic_path
)
from bot.utils.keyboards.history_keyboards import file_format_keyboard
from bot.utils.metrics import create_project_data_row, generate_cells_content
from bot.utils.project_data import get_full_info, calculate_expected_x, get_project_data
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.resources.files_worker.pdf_worker import PDF, generate_pie_chart
from bot.utils.resources.headers.headers import ru_results_headers, eng_results_headers, ru_additional_headers, \
    eng_additional_headers
from bot.utils.resources.headers.headers_handler import calculation_header_by_user, write_headers
from bot.utils.validations import save_execute, extract_old_calculations

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
    pdf.add_font("DejaVu", '', dejavu_path, uni=True)
    pdf.add_font("DejaVu", 'B', dejavu_bold_path, uni=True)
    pdf.add_font("DejaVu", 'I', dejavu_italic_path, uni=True)

    agent_answer = calc.agent_answer if calc.agent_answer else "Ответ модели отсутствует"
    pdf.set_font("DejaVu", size=12)
    flags_answer = agent_answer

    if language == "RU":
        match = re.search(r"Общая оценка проекта\s*([\d.]+)\s*баллов?\s*\((.+?)\)", flags_answer)
    else:
        match = re.search(r"Overall project evaluation\s*([\d.]+)\s*points\s*\((.+?)\)", flags_answer)

    if match:
        project_score = float(match.group(1))  # Извлекаем баллы
        project_rating = match.group(2)  # Извлекаем оценку
        print(f"Итоговые баллы: {project_score}")
        print(f"Оценка проекта: {project_rating}")
    else:
        project_score = "Данных по баллам не поступило" if language == "RU" else "No data on scores were received"
        project_rating = "Нет данных по оценке баллов проекта" if language == "RU" else "No data available on project scoring"
        print("Не удалось найти итоговые баллы и/или оценку.")

    selected_patterns = patterns["RU"] if language == "RU" else patterns["EN"]

    # Обработка текста для PDF
    text_to_parse = flags_answer  # Исходный текст для обработки

    # Добавление в PDF
    pdf.set_font("DejaVu", size=12)
    pdf.cell(0, 6, f"{'Анализ проекта' if language == 'RU' else 'Project analysis'}", 0, 1, 'L')
    pdf.cell(0, 6, current_date, 0, 1, 'L')
    pdf.ln(6)

    for pattern in selected_patterns:
        match = re.search(pattern, text_to_parse, re.IGNORECASE | re.DOTALL)
        if match:
            # Извлекаем заголовок
            start, end = match.span()
            header = match.group(1)

            # Извлекаем содержимое под заголовком
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

                # Добавляем заголовок жирным
                pdf.set_font("DejaVu", style="B", size=12)
                pdf.multi_cell(0, 6, header, 0)

                pdf.ln(0.1)

                # Обычный текст до фразы
                pdf.set_font("DejaVu", size=12)
                if header == "«Ред» флаги и «грин» флаги:":
                    lines = before_text.splitlines()
                    cleaned_lines = []
                    for line in lines:
                        stripped_line = " ".join(line.split())  # Убираем лишние пробелы внутри строки
                        if stripped_line.startswith("-"):  # Если строка начинается с пункта списка
                            cleaned_lines.append(stripped_line)
                        elif cleaned_lines and not cleaned_lines[-1].endswith(
                                ":"):  # Присоединяем к предыдущей строке
                            cleaned_lines[-1] += f" {stripped_line}"
                        else:
                            cleaned_lines.append(stripped_line)
                    before_text = "\n".join(cleaned_lines)

                if "Отрицательные характеристики:" in before_text:
                    before_text = before_text.replace("Отрицательные характеристики:","\nОтрицательные характеристики:")
                pdf.multi_cell(0, 6, before_text, 0)

                pdf.ln(0.1)

                # Текст с курсивом (фраза и ссылка)
                pdf.set_font("DejaVu", style="I", size=12)
                pdf.multi_cell(0, 6,
                               f"\n\n***Если Вам не понятна терминология, изложенная в отчете, Вы можете воспользоваться нашим ИИ консультантом.",
                               0)
                pdf.ln(0.1)
                # Устанавливаем цвет для ссылки (синий)
                pdf.set_text_color(0, 0, 255)
                pdf.multi_cell(0, 6, "https://t.me/FasolkaAI_bot", 0)

                # Возвращаем цвет текста к обычному черному
            elif re.search(ai_help_en, content, re.DOTALL):
                parts = re.split(ai_help_en_split, content, maxsplit=1)
                before_text = parts[0].strip()

                pdf.set_font("DejaVu", style="B", size=12)
                pdf.multi_cell(0, 6, header, 0)

                pdf.ln(0.1)

                # Обычный текст до фразы
                pdf.set_font("DejaVu", size=12)
                if header == "«Red» flags and «green» flags:":
                    lines = before_text.splitlines()
                    cleaned_lines = []
                    for line in lines:
                        stripped_line = " ".join(line.split())  # Убираем лишние пробелы внутри строки
                        print("stripped_line: ", stripped_line)
                        if stripped_line.startswith("-"):  # Если строка начинается с пункта списка
                            cleaned_lines.append(stripped_line)
                        elif cleaned_lines and not cleaned_lines[-1].endswith(
                                ":"):  # Присоединяем к предыдущей строке
                            cleaned_lines[-1] += f" {stripped_line}"
                        else:
                            cleaned_lines.append(stripped_line)
                    before_text = "\n".join(cleaned_lines)

                if "Negative Characteristics:" in before_text:
                    before_text = before_text.replace("Negative Characteristics:", "\nNegative Characteristics:")

                pdf.multi_cell(0, 6, before_text, 0)

                pdf.ln(0.1)

                # Текст с курсивом (фраза и ссылка)
                pdf.set_font("DejaVu", style="I", size=12)
                # Сначала выводим обычный текст
                pdf.multi_cell(0, 6,
                               f"\n\n***If you do not understand the terminology in the report, you can use our AI consultant.",
                               0)
                pdf.ln(0.1)
                # Устанавливаем цвет для ссылки (синий)
                pdf.set_text_color(0, 0, 255)
                pdf.multi_cell(0, 6, "https://t.me/FasolkaAI_bot", 0)

                # Возвращаем цвет текста к обычному черному
                pdf.set_text_color(0, 0, 0)
            else:
                print("header", header)
                print("content", content)
                # Добавляем заголовок жирным
                pdf.set_font("DejaVu", style="B", size=12)
                pdf.multi_cell(0, 6, header, 0)

                pdf.ln(0.1)

                # Добавляем основной текст
                pdf.set_font("DejaVu", size=12)
                content_cleaned = content

                if header in ["Описание проекта:", "Оценка прибыльности инвесторов:", "Project description:",
                              "Evaluating investor profitability:", ]:
                    content_cleaned = " ".join(content.split())

                content_cleaned = extract_old_calculations(content_cleaned, language)
                pdf.multi_cell(0, 6, content_cleaned, 0)

                pdf.ln(6)

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    zip_file.writestr(file_name, pdf_output.read())

@save_execute
async def create_excel_file(zip_file, calc, session, user_id):
    readable_date = calc.date.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"calculation_{readable_date}.xlsx"

    excel_buffer = BytesIO()
    workbook = xlsxwriter.Workbook(excel_buffer)
    worksheet = workbook.add_worksheet()

    header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
    data_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
    number_format = workbook.add_format({'num_format': '0.00', 'align': 'center'})
    set_column_formats(worksheet, data_format)

    agent_answer = calc.agent_answer if calc.agent_answer else "Ответ модели отсутствует"
    text_format = workbook.add_format({'text_wrap': True, 'align': 'top', 'valign': 'top'})
    worksheet.merge_range('A1:H30', agent_answer, text_format)

    row_start = 32
    write_headers(worksheet, header_format, row_start, user_id)

    base_project, basic_metrics, similar_projects, base_tokenomics = await get_project_data(calc, session)
    row_data = await prepare_row_data(similar_projects, basic_metrics, base_project, base_tokenomics, user_id)
    end_row = write_data_to_worksheet(worksheet, row_data, data_format, number_format, row_start + 1)
    merge_cells(worksheet, row_data, data_format, row_start + 1)

    empty_row = end_row + 1
    funds_diagrams = empty_row
    worksheet.write(empty_row, 0, '', data_format)

    default_data = []
    fund_distribution_list = []
    fund_distribution_dict = {}

    if user_languages.get(user_id) == 'RU':
        additional_headers = ru_additional_headers
    else:
        additional_headers = eng_additional_headers

    for col_num, header in enumerate(additional_headers):
        worksheet.write(empty_row + 1, col_num, header, header_format)

    (
     projects,
     tokenomics_data_list,
     basic_metrics_data_list,
     invested_metrics_data_list,
     social_metrics_data_list,
     funds_profit_data_list,
     top_and_bottom_data_list,
     market_metrics_data_list,
     manipulative_metrics_data_list,
     network_metrics_data_list
    ) = await get_full_info(session, base_project.category, user_coin_name=base_project.coin_name)

    result_index = 1
    for index, (project, tokenomics_data) in enumerate(tokenomics_data_list, start=1):
        for tokenomics in tokenomics_data:
            if base_project.coin_name != project.coin_name:
                basic_metrics = next((bm for bm in basic_metrics_data_list if bm[0] == project), None)
                investing_metrics = next((im for im in invested_metrics_data_list if im[0] == project), None)
                social_metrics = next((sm for sm in social_metrics_data_list if sm[0] == project), None)
                funds_profit = next((fp for fp in funds_profit_data_list if fp[0] == project), None)
                market_metrics = next((mm for mm in market_metrics_data_list if mm[0] == project), None)
                manipulative_metrics = next((man for man in manipulative_metrics_data_list if man[0] == project), None)
                network_metrics = next((nm for nm in network_metrics_data_list if nm[0] == project), None)
                top_and_bottom = next((km for km in top_and_bottom_data_list if km[0] == project), None)
                default_data.append(create_project_data_row(
                    project,
                    tokenomics,
                    basic_metrics,
                    investing_metrics,
                    social_metrics,
                    market_metrics,
                    manipulative_metrics,
                    network_metrics,
                    top_and_bottom
                ))

                if len(funds_profit) > 1 and len(funds_profit[1]) > 0:
                    fund_distribution_list.append((project.coin_name, str(funds_profit[1][0].distribution) if funds_profit[1][0].distribution else "-"))
                else:
                    fund_distribution_list.append((project.coin_name, "-"))

                result_index += 1

    for row_num, row in enumerate(default_data, start=empty_row + 2):
        for col_num, value in enumerate(row):
            worksheet.write(row_num, col_num, value, data_format)
        funds_diagrams += 1

    for item in fund_distribution_list:
        coin_name = item[0]
        distribution_str = item[1]

        if coin_name not in fund_distribution_dict:
            fund_distribution_dict[coin_name] = []

        fund_distribution_dict[coin_name].append(distribution_str)

    start_row = funds_diagrams + 5
    spacing = 9
    max_charts_in_row = 3
    chart_width = 4
    chart_height = 15
    current_chart_index = 0
    data_row_start = 60

    x_scale = 1.2
    y_scale = 1.2

    for coin_name, distributions in fund_distribution_dict.items():
        chart_data = {
            "labels": [],
            "values": []
        }

        for distribution in distributions:
            parts = distribution.split(')')
            if parts:
                for part in parts:
                    if part:
                        tokemonics_parts = part.split('(')
                        if len(tokemonics_parts) > 1:
                            label = tokemonics_parts[0].strip()
                            value = tokemonics_parts[1].replace('%', '').strip()
                            chart_data["labels"].append(label)
                            try:
                                chart_data["values"].append(float(value))
                            except ValueError:
                                chart_data["values"].append(0.0)

        if chart_data["values"]:
            chart = workbook.add_chart({'type': 'pie'})
            chart.set_size({'width': 300, 'height': 400})
            data_start_row = data_row_start
            data_end_row = data_row_start + len(chart_data["values"]) - 1

            for i, value in enumerate(chart_data["values"]):
                worksheet.write(data_row_start + i, 1, value)
                worksheet.write(data_row_start + i, 0, chart_data["labels"][i])

            percentage_labels = [f"{label} ({value}%)" for label, value in zip(chart_data["labels"], chart_data["values"])]

            for i, label in enumerate(percentage_labels):
                worksheet.write(data_row_start + i, 0, label)

            chart.add_series({
                'name': f'Allocation {coin_name}',
                'categories': f'={worksheet.get_name()}!$A${data_start_row + 1}:$A${data_end_row + 1}',
                'values': f'={worksheet.get_name()}!$B${data_start_row + 1}:$B${data_end_row + 1}',
                'data_labels': {'value': False},
                'points': [{'fill': {'color': color_palette[i % len(color_palette)]}} for i in range(len(chart_data["values"]))],
            })

            chart.set_legend({
                'position': 'right',
                'layout': {'overlay': True},
                'font': {'size': 8},
                'margin': {'top': 0, 'right': 0, 'bottom': 0, 'left': 0},
            })

            chart.set_title({
                'name': f'Distribution of Funds for {coin_name}',
                'name_font': {'size': 10}
            })
            chart.set_style(10)

            row_position = start_row + (current_chart_index // max_charts_in_row) * (chart_height + spacing)
            col_position = (current_chart_index % max_charts_in_row) * chart_width

            worksheet.insert_chart(row_position, col_position, chart, {'x_scale': x_scale, 'y_scale': y_scale})
            current_chart_index += 1
            data_row_start = data_end_row + spacing

        else:
            logging.info(f"No data to create chart for {coin_name}.")

    workbook.close()
    excel_buffer.seek(0)
    zip_file.writestr(file_name, excel_buffer.read())


def set_column_formats(worksheet, data_format):
    for col_num, width in enumerate(column_widths):
        worksheet.set_column(col_num, col_num, width, data_format)


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


def write_data_to_worksheet(worksheet, row_data, data_format, number_format, start_row):
    end_row = start_row
    for row_num, row in enumerate(row_data, start=start_row):
        for col_num, value in enumerate(row):
            if col_num == 0:
                worksheet.write(row_num, col_num, value, data_format)
            elif isinstance(value, (int, float)):
                worksheet.write(row_num, col_num, value, number_format)
            else:
                worksheet.write(row_num, col_num, value, data_format)
        end_row += 1

    return end_row


def merge_cells(worksheet, row_data, data_format, end_row):
    last_values = {i: None for i in range(len(row_data[0]))}
    start_rows = {i: end_row for i in range(len(row_data[0]))}

    for row_num in range(end_row, len(row_data) + end_row):
        for col_num in range(len(row_data[0])):
            if row_num - end_row < len(row_data):
                current_value = row_data[row_num - end_row][col_num]
            else:
                continue

            if last_values[col_num] is None:
                last_values[col_num] = current_value
                start_rows[col_num] = row_num
            elif current_value == last_values[col_num]:
                continue
            else:
                if start_rows[col_num] < row_num - 1:
                    worksheet.merge_range(start_rows[col_num], col_num, row_num - 1, col_num, last_values[col_num], data_format)

                last_values[col_num] = current_value
                start_rows[col_num] = row_num

    for col_num in range(len(row_data[0])):
        if start_rows[col_num] < len(row_data) + end_row:
            worksheet.merge_range(start_rows[col_num], col_num, len(row_data) + end_row - 1, col_num, last_values[col_num], data_format)
