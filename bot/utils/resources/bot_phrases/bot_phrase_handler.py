from bot.utils.consts import user_languages
from bot.utils.resources.bot_phrases.bot_phrase_strings import phrase_dict


def phrase_by_user(phrase_id, user_id):
    language = user_languages.get(user_id)
    return phrase_dict.get(language).get(phrase_id)


def phrase_by_language(phrase_id, language):
    return phrase_dict.get(language).get(phrase_id)

