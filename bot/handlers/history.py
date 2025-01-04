import logging
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
    color_palette, SessionLocal, async_session
)
from bot.utils.keyboards.history_keyboards import file_format_keyboard
from bot.utils.metrics import create_project_data_row, generate_cells_content
from bot.utils.project_data import get_full_info, calculate_expected_x, get_project_data
from bot.utils.resources.bot_phrases.bot_phrase_handler import phrase_by_user
from bot.utils.resources.files_worker.pdf_worker import PDF, generate_pie_chart
from bot.utils.resources.headers.headers import ru_results_headers, eng_results_headers, ru_additional_headers, \
    eng_additional_headers
from bot.utils.resources.headers.headers_handler import calculation_header_by_user, write_headers
from bot.utils.validations import save_execute

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


# @history_router.message(lambda message: message.text == 'История расчетов' or message.text == 'Calculation History')
# async def file_format_chosen(message: types.Message, state: FSMContext):
#     await history_command(async_session, message, state)


# @history_router.message(HistoryState.choosing_file_format)
@history_router.message(lambda message: message.text == 'История расчетов' or message.text == 'Calculation History')
async def history_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    await message.answer(phrase_by_user("wait_for_zip", user_id))

    file_format = message.text.lower()
    await state.update_data(file_format=file_format)

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
                await create_pdf_file(zip_archive, calculation, async_session, user_id)
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


async def create_pdf_file(zip_file, calc, session, user_id):
    cells_content = None
    row_data = []
    formatted_lines = []
    skip_empty_line = False
    readable_date = calc.date.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"calculation_{readable_date}.pdf"

    pdf = PDF(logo_path=logo_path, orientation='L')
    pdf.add_page()
    pdf.add_font("DejaVu", '', dejavu_path, uni=True)
    # pdf.add_font("DejaVu", '', dejavu_path, uni=True)
    headers = calculation_header_by_user(user_id)

    agent_answer = calc.agent_answer if calc.agent_answer else "Ответ модели отсутствует"
    pdf.set_font("DejaVu", size=8)
    lines = agent_answer.split('\n')

    for line in lines:
        if line.startswith("**Положительные характеристики:**") or line.startswith("**Отрицательные характеристики:**"):
            formatted_lines.append(line)
            skip_empty_line = True
        elif skip_empty_line and not line.strip():
            continue
        else:
            formatted_lines.append(line.strip())
            skip_empty_line = False

    formatted_answer = "\n".join(formatted_lines)
    pdf.multi_cell(0, 10, f"{phrase_by_user('model_answer_for_calculations', user_id)}\n{formatted_answer}\n", align='L')
    pdf.set_font("DejaVu", size=10)

    base_project, basic_metrics, similar_projects, base_tokenomics = await get_project_data(calc, session)
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
    ) = await get_full_info(session, base_project.category, base_project.coin_name)

    result_index = 1
    for index, (project, tokenomics_data) in enumerate(tokenomics_data_list, start=1):
        for tokenomics in tokenomics_data:
            if base_project.coin_name != project.coin_name:
                fdv = tokenomics.fdv if tokenomics.fdv is not None else 0
                calculation_result = calculate_expected_x(
                    entry_price=basic_metrics.market_price,
                    total_supply=base_tokenomics.total_supply,
                    fdv=fdv,
                )

                if "error" in calculation_result:
                    raise ValueError(calculation_result["error"])

                fair_price = f"{calculation_result['fair_price']:.5f}" if isinstance(calculation_result['fair_price'], (int, float)) else "Ошибка в расчетах"
                expected_x = f"{calculation_result['expected_x']:.5f}"

                row_data.append([
                    result_index,
                    base_project.coin_name,
                    project.coin_name,
                    expected_x,
                    fair_price
                ])
                result_index += 1

    for header in headers:
        if header == ('Вариант' or 'Option'):
            pdf.cell(30, 10, header, 1)
        elif header == ('Расчеты относительно монеты' or 'Calculations relative to coin'):
            pdf.cell(55, 10, header, 1)
        elif header == ('Ожидаемая цена монеты, $' or 'Expected market price, $'):
            pdf.cell(50, 10, header, 1)
        else:
            pdf.cell(45, 10, header, 1)
    pdf.ln()

    for row in row_data:
        for col_num, value in enumerate(row):
            if headers[col_num] == ('Вариант' or 'Option'):
                pdf.cell(30, 10, str(value), 1)
            elif headers[col_num] == ('Расчеты относительно монеты' or 'Calculations relative to coin'):
                pdf.cell(55, 10, str(value), 1)
            elif headers[col_num] == ('Ожидаемая цена монеты, $' or 'Expected market price, $'):
                pdf.cell(50, 10, str(value), 1)
            else:
                pdf.cell(45, 10, str(value), 1)
        pdf.ln()
    pdf.ln()

    if user_languages.get(user_id) == 'RU':
        headers_mapping = ru_results_headers
    else:
        headers_mapping = eng_results_headers

    investor_data_list = []
    for header_set in headers_mapping:
        for header in header_set:
            if header == ('Тир фондов' or 'Fund Tier'):
                pdf.cell(230, 10, header, 1)
            elif header == ('Сфера' or 'Sphere'):
                pdf.cell(80, 10, header, 1)
            elif header == 'FDV':
                pdf.cell(70, 10, header, 1)
            else:
                pdf.cell(40, 10, header, 1)
        pdf.ln()

        for index, (project, tokenomics_data) in enumerate(tokenomics_data_list, start=1):
            for tokenomics in tokenomics_data:
                funds_profit = next((fp for fp in funds_profit_data_list if fp[0] == project), None)

                cells_content = generate_cells_content(
                    basic_metrics_data_list,
                    invested_metrics_data_list,
                    social_metrics_data_list,
                    market_metrics_data_list,
                    manipulative_metrics_data_list,
                    network_metrics_data_list,
                    top_and_bottom_data_list,
                    project,
                    header_set,
                    headers_mapping,
                    tokenomics,
                    cells_content
                )

                if len(cells_content) != len(header_set):
                    print(f"Ошибка: количество значений {len(cells_content)} не соответствует заголовкам {len(header_set)}.")
                    continue

                cell_widths = []
                for i, content in enumerate(cells_content):
                    if i < len(header_set) and header_set[i] == 'Тир фондов':
                        cell_widths.append(230)
                    elif i < len(header_set) and header_set[i] == 'Сфера':
                        cell_widths.append(80)
                    elif i < len(header_set) and header_set[i] == 'FDV':
                        cell_widths.append(70)
                    else:
                        cell_widths.append(40)

                max_lines = 1
                for i, content in enumerate(cells_content):
                    content_width = pdf.get_string_width(content)
                    lines = (content_width // cell_widths[i]) + 1
                    if lines > max_lines:
                        max_lines = lines

                cell_height = max_lines * 10
                for i, content in enumerate(cells_content):
                    if pdf.get_string_width(content) > cell_widths[i]:
                        pdf.multi_cell(cell_widths[i], 10, content, 1)
                        current_y = pdf.get_y()
                        pdf.set_xy(pdf.get_x(), current_y - 10)
                    else:
                        pdf.cell(cell_widths[i], cell_height, content, 1)

            pdf.ln()
            if len(funds_profit) > 1 and len(funds_profit[1]) > 0 and funds_profit[1][0].distribution and (project.coin_name, funds_profit[1][0].distribution) not in investor_data_list:
                investor_data_list.append((project.coin_name, funds_profit[1][0].distribution))

        pdf.ln()

    pdf.add_page()
    page_width = pdf.w
    diagram_per_page = 4
    diagrams_on_page = 0
    chart_width = 110
    x_pos_left = (page_width / 4) - (chart_width / 2)
    x_pos_right = (3 * page_width / 4) - (chart_width / 2)

    for i, (coin_name, distribution_data) in enumerate(investor_data_list):
        if diagrams_on_page == diagram_per_page:
            pdf.add_page()
            diagrams_on_page = 0

        y_pos = 30 + (diagrams_on_page // 2) * 90

        if i % 2 == 0:
            x_pos = x_pos_left
        else:
            x_pos = x_pos_right

        pdf.set_font("DejaVu", size=12)
        pdf.set_xy(x_pos, y_pos - 10)
        pdf.cell(90, 10, f"{phrase_by_user('tokens_distribution', user_id)} {coin_name}", 0, 1, 'C')

        pie_chart_img = generate_pie_chart(distribution_data)
        pdf.image(pie_chart_img, x=x_pos, y=y_pos, w=chart_width, h=85)

        diagrams_on_page += 1

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
