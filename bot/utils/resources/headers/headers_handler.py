from bot.utils.consts import user_languages
from bot.utils.resources.headers.headers import (
    ru_calculation_headers,
    eng_calculation_headers,
    ru_results_headers,
    eng_results_headers
)


def calculation_header_by_user(user_id):
    language = user_languages.get(user_id)
    return ru_calculation_headers if language == "RU" else eng_calculation_headers


def results_header_by_user(user_id):
    language = user_languages.get(user_id)
    return ru_results_headers if language == "RU" else eng_results_headers


def write_headers(worksheet, header_format, row_start, user_id):
    headers = calculation_header_by_user(user_id)

    for col_num, header in enumerate(headers):
        worksheet.write(row_start, col_num, header, header_format)
