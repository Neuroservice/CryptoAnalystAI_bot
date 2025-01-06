from bot.utils.consts import user_languages
from bot.utils.resources.bot_phrases.bot_phrase_strings import phrase_dict


def phrase_by_user(phrase_id, user_id, current_value=None, min_value=None, max_value=None):
    language = user_languages.get(user_id)
    phrase = phrase_dict.get(language).get(phrase_id)

    if current_value is not None and min_value is not None and max_value is not None:
        phrase = phrase.format(current_value=current_value, min_value=min_value, max_value=max_value)

    return phrase


def phrase_by_language(phrase_id, language):
    return phrase_dict.get(language).get(phrase_id)

