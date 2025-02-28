import re
from typing import List, Dict

import fitz

from io import BytesIO
from PIL import Image, ImageDraw
from fpdf import FPDF

from bot.database.models import Calculation
from bot.utils.resources.bot_phrases.bot_phrase_handler import (
    phrase_by_language,
)
from bot.utils.validations import extract_old_calculations
from bot.utils.common.consts import (
    TIMES_NEW_ROMAN_PATH,
    TIMES_NEW_ROMAN_BOLD_PATH,
    TIMES_NEW_ROMAN_ITALIC_PATH,
    LOGO_PATH,
    PATTERNS,
    AI_HELP_RU,
    AI_HELP_RU_SPLIT,
    AI_HELP_EN,
    AI_HELP_EN_SPLIT,
    FASOLKA_TG,
    PROJECT_ANALYSIS,
)


class PDF(FPDF):
    def __init__(self, logo_path=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logo_path = logo_path
        self.footer_logo_path = None
        if self.logo_path:
            self.footer_logo_path = self._create_round_logo(self.logo_path)

    def _create_round_logo(self, path: str):
        """
        Обрезает изображение в форме круга и сохраняет его временно.
        """

        img = Image.open(path).convert("RGBA")
        size = min(img.size)
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        circular_img = Image.new("RGBA", (size, size))
        circular_img.paste(img, (0, 0, size, size), mask)
        # temp_path = "media/temp_footer_logo.png"
        temp_path = "/app/bot/media/temp_footer_logo.png"
        return temp_path

    def header(self):
        """
        Добавление логотипа в верхний левый угол каждой страницы.
        """

        if self.footer_logo_path:
            self.image(self.footer_logo_path, x=193, y=5, w=10)


async def generate_pdf(
    funds_profit: str,
    tier_answer: str,
    language: str,
    formatted_metrics_text: str,
    profit_text: str,
    red_green_flags: str,
    top_and_bottom_answer: str,
    calculations: List[Dict[str, str]],
    project_evaluation: str,
    overal_final_score: float,
    project_rating_text: str,
    current_date: str,
    token_description: str,
    categories: List[str],
    lower_name: str,
    coin_name: str,
):
    """
    Генерация PDF файла с проектными данными и метриками.
    """

    pdf = PDF(logo_path=LOGO_PATH, orientation="P")
    pdf.set_margins(left=20, top=10, right=20)
    pdf.add_page()
    pdf.add_font("TimesNewRoman", "", TIMES_NEW_ROMAN_PATH, uni=True)
    pdf.add_font("TimesNewRoman", "B", TIMES_NEW_ROMAN_BOLD_PATH, uni=True)
    pdf.add_font("TimesNewRoman", "I", TIMES_NEW_ROMAN_ITALIC_PATH, uni=True)
    pdf.set_font("TimesNewRoman", size=12)

    pdf.cell(
        0,
        6,
        phrase_by_language(
            "project_analysis",
            language,
            lower_name=lower_name,
            ticker=coin_name,
        ),
        0,
        1,
        "L",
    )
    pdf.cell(0, 6, current_date, 0, 1, "L")
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.cell(
        0, 6, phrase_by_language("project_description", language), 0, 1, "L"
    )
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(0.1)
    pdf.multi_cell(0, 6, token_description, 0)
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.cell(0, 6, phrase_by_language("project_category", language), 0, 1, "L")
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(0.1)
    categories_str = ", ".join(categories)
    pdf.multi_cell(0, 6, categories_str, 0)
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.multi_cell(
        0,
        6,
        phrase_by_language("project_metrics", language, tier=tier_answer),
        0,
    )
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(0.1)
    pdf.multi_cell(0, 6, formatted_metrics_text, 0)
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.multi_cell(0, 6, phrase_by_language("token_distribution", language), 0)
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(0.1)
    pdf.multi_cell(0, 6, funds_profit, 0)
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.multi_cell(
        0, 6, phrase_by_language("funds_profit_scores", language), 0
    )
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(0.1)
    pdf.multi_cell(0, 6, profit_text, 0)
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.multi_cell(0, 6, phrase_by_language("top_bottom_2_years", language), 0)
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(0.1)
    pdf.multi_cell(0, 6, top_and_bottom_answer, 0)
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.multi_cell(
        0, 6, phrase_by_language("comparing_calculations", language), 0
    )
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(0.1)
    pdf.multi_cell(0, 6, calculations, 0)
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.cell(
        0,
        6,
        f"{phrase_by_language('overall_evaluation', language)}",
        0,
        0,
        "L",
    )
    # pdf.cell(0, 6, f"{f'Оценка проекта:' if language == 'RU' else f'Overall evaluation:'}", 0, 0, 'L')
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(0.1)
    pdf.multi_cell(0, 6, project_evaluation, 0)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.cell(
        0,
        6,
        phrase_by_language(
            "overall_project_evaluation",
            language,
            score=overal_final_score,
            rating_text=project_rating_text,
        ),
        0,
        1,
        "L",
    )
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="B", size=12)
    pdf.cell(0, 6, phrase_by_language("flags", language), 0, 1, "L")
    pdf.ln(0.1)
    pdf.set_font("TimesNewRoman", size=12)
    pdf.multi_cell(0, 6, red_green_flags, 0)
    pdf.ln(6)

    pdf.set_font("TimesNewRoman", style="I", size=12)
    pdf.multi_cell(0, 6, f"{phrase_by_language('ai_help', language)}", 0)
    pdf.ln(0.1)
    pdf.set_font("TimesNewRoman", size=12, style="IU")
    pdf.set_text_color(0, 0, 255)
    pdf.cell(0, 6, FASOLKA_TG, 0, 1, "L", link=FASOLKA_TG)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(0.1)

    pdf.set_font("TimesNewRoman", style="I", size=12)
    pdf.multi_cell(
        0, 6, f"\n{phrase_by_language('ai_answer_caution', language)}", 0
    )
    pdf.ln(0.1)

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    pdf_data = pdf_output.read()

    doc = fitz.open(stream=pdf_data, filetype="pdf")
    extracted_text = "".join([page.get_text("text") for page in doc])

    return pdf_output, extracted_text


def create_pdf_file(calc: Calculation, language: str, answer: str = None):
    """
    Создает PDF-файл с деталями анализа проекта.
    """

    current_date = calc.date.strftime("%d.%m.%Y")

    pdf = PDF(logo_path=LOGO_PATH, orientation="P")
    pdf.set_margins(left=20, top=10, right=20)
    pdf.add_page()
    pdf.add_font("TimesNewRoman", "", TIMES_NEW_ROMAN_PATH, uni=True)
    pdf.add_font("TimesNewRoman", "B", TIMES_NEW_ROMAN_BOLD_PATH, uni=True)
    pdf.add_font("TimesNewRoman", "I", TIMES_NEW_ROMAN_ITALIC_PATH, uni=True)

    agent_answer = (
        calc.agent_answer if calc.agent_answer else "Ответ модели отсутствует"
    )
    pdf.set_font("TimesNewRoman", size=12)

    selected_patterns = PATTERNS["RU"] if language == "RU" else PATTERNS["EN"]

    text_to_parse = agent_answer

    if answer:
        text_to_parse = answer

    project_analysis_pattern = re.compile(PROJECT_ANALYSIS, re.IGNORECASE)
    first_line_match = re.search(project_analysis_pattern, text_to_parse)

    if first_line_match:
        first_line = first_line_match.group(0)
        pdf.set_font("TimesNewRoman", size=12)
        pdf.cell(0, 6, first_line, 0, 1, "L")
        pdf.cell(0, 6, current_date, 0, 1, "L")
        pdf.ln(6)

    for pattern in selected_patterns:
        match = re.search(pattern, text_to_parse, re.IGNORECASE | re.DOTALL)
        if match:
            start, end = match.span()
            header = match.group(1)

            content_start = end
            next_header_match = None
            for next_pattern in selected_patterns:
                next_header_match = re.search(
                    next_pattern, text_to_parse[end:], re.IGNORECASE
                )
                if next_header_match:
                    break

            content_end = (
                next_header_match.start() + end
                if next_header_match
                else len(text_to_parse)
            )
            content = text_to_parse[content_start:content_end].strip()

            if re.search(AI_HELP_RU, content, re.DOTALL):
                parts = re.split(AI_HELP_RU_SPLIT, content, maxsplit=1)
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
                        elif cleaned_lines and not cleaned_lines[-1].endswith(
                            ":"
                        ):
                            cleaned_lines[-1] += f" {stripped_line}"
                        else:
                            cleaned_lines.append(stripped_line)
                    before_text = "\n".join(cleaned_lines)

                if "Отрицательные характеристики:" in before_text:
                    before_text = before_text.replace(
                        "Отрицательные характеристики:",
                        "\nОтрицательные характеристики:",
                    )

                pdf.multi_cell(0, 6, before_text, 0)

                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", style="I", size=12)
                pdf.multi_cell(
                    0, 6, f"\n\n{phrase_by_language('ai_help', language)}", 0
                )

                pdf.ln(0.1)

                pdf.set_text_color(0, 0, 255)
                pdf.set_font("TimesNewRoman", style="IU", size=12)
                pdf.multi_cell(0, 6, FASOLKA_TG, 0)

                pdf.set_text_color(0, 0, 0)
                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", style="I", size=12)
                pdf.multi_cell(
                    0,
                    6,
                    f"\n\n{phrase_by_language('ai_answer_caution', language)}",
                    0,
                )
                pdf.ln(0.1)
            elif re.search(AI_HELP_EN, content, re.DOTALL):
                parts = re.split(AI_HELP_EN_SPLIT, content, maxsplit=1)
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
                        elif cleaned_lines and not cleaned_lines[-1].endswith(
                            ":"
                        ):
                            cleaned_lines[-1] += f" {stripped_line}"
                        else:
                            cleaned_lines.append(stripped_line)
                    before_text = "\n".join(cleaned_lines)

                if "Negative Characteristics:" in before_text:
                    before_text = before_text.replace(
                        "Negative Characteristics:",
                        "\nNegative Characteristics:",
                    )

                pdf.multi_cell(0, 6, before_text, 0)

                pdf.ln(0.1)

                # Текст с курсивом (фраза и ссылка)
                pdf.set_font("TimesNewRoman", style="I", size=12)
                # Сначала выводим обычный текст
                pdf.multi_cell(
                    0, 6, f"\n\n{phrase_by_language('ai_help', language)}", 0
                )
                pdf.ln(0.1)
                # Устанавливаем цвет для ссылки (синий)
                pdf.set_text_color(0, 0, 255)
                pdf.set_font("TimesNewRoman", style="IU", size=12)
                pdf.multi_cell(0, 6, FASOLKA_TG, 0)

                # Возвращаем цвет текста к обычному черному
                pdf.set_text_color(0, 0, 0)
                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", style="I", size=12)
                pdf.multi_cell(
                    0,
                    6,
                    f"\n\n{phrase_by_language('ai_answer_caution', language)}",
                    0,
                )
                pdf.ln(0.1)
            else:
                pdf.set_font("TimesNewRoman", style="B", size=12)
                pdf.multi_cell(0, 6, header, 0)

                pdf.ln(0.1)

                pdf.set_font("TimesNewRoman", size=12)
                content_cleaned = content

                if header in [
                    "Описание проекта:",
                    "Оценка прибыльности инвесторов:",
                    "Project description:",
                    "Evaluating investor profitability:",
                ]:
                    content_cleaned = " ".join(content.split())

                content_cleaned = extract_old_calculations(
                    content_cleaned, language
                )
                pdf.multi_cell(0, 6, content_cleaned, 0)

                pdf.ln(6)

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    pdf_data = pdf_output.read()

    doc = fitz.open(stream=pdf_data, filetype="pdf")
    extracted_text = "".join([page.get_text("text") for page in doc])

    return pdf_output, extracted_text
