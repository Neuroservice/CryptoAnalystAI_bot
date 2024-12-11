from bot.utils.consts import user_languages
from bot.utils.resources.buttons.button_strings import button_strings_dict


def button_text_by_language(button_text_id, language):
    return button_strings_dict.get(language).get(button_text_id)


def button_text_by_user(button_text_id, user_id):
    user_language = user_languages.get(user_id)
    return button_strings_dict.get(user_language).get(button_text_id)
