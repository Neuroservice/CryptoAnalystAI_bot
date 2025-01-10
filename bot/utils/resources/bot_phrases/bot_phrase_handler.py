from bot.utils.consts import user_languages
from bot.utils.resources.bot_phrases.bot_phrase_strings import phrase_dict


def phrase_by_user(phrase_id, user_id, **kwargs):
    language = user_languages.get(user_id)
    phrase = phrase_dict.get(language, {}).get(phrase_id)

    if phrase and kwargs:
        try:
            phrase = phrase.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing placeholder in kwargs for phrase '{phrase_id}': {e}")

    return phrase


def phrase_by_language(phrase_id, language):
    return phrase_dict.get(language).get(phrase_id)

