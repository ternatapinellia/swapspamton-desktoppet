# -*- coding: utf-8 -*-
"""SPT DeskPet dialogue compatibility layer.

index.py keeps using get_dialogues(lang, key).
Chinese and English text are provided by SPT_dialogue_pack.py.
"""

from SPT_dialogue_pack import (
    start, start_EN,
    click, click_EN,
    random, random_EN,
    note, note_EN,
    product, product_EN,
    flirt, flirt_EN,
    reminder, reminder_EN,
    drink, drink_EN,
    lunch, lunch_EN,
    dinner, dinner_EN,
    sleep, sleep_EN,
    close, close_EN,
)

_DRINK = drink
_LUNCH = lunch
_DINNER = dinner
_SLEEP = sleep

_DRINK_EN = drink_EN
_LUNCH_EN = lunch_EN
_DINNER_EN = dinner_EN
_SLEEP_EN = sleep_EN

_DIALOGUE_MAP_ZH = {
    "start": start,
    "click": click,
    "random": random,
    "note_saved": note,
    "note_error": [
        "【便签错误】保存失败。别担心，我已经准备好继续嘲笑这个故障了。",
        "保存失败。看来连文件系统都想和你作对。",
    ],
    "note_repeat": note,
    "product": product,
    "flirt": flirt,
    "drink": _DRINK,
    "lunch": _LUNCH,
    "dinner": _DINNER,
    "sleep": _SLEEP,
    "close": close,
}

_DIALOGUE_MAP_EN = {
    "start": start_EN,
    "click": click_EN,
    "random": random_EN,
    "note_saved": note_EN,
    "note_error": [
        "【NOTE ERROR】Save failed. Don't worry. I am already prepared to laugh at this malfunction.",
        "Save failed. Apparently even the file storage wants to oppose you.",
    ],
    "note_repeat": note_EN,
    "product": product_EN,
    "flirt": flirt_EN,
    "drink": _DRINK_EN,
    "lunch": _LUNCH_EN,
    "dinner": _DINNER_EN,
    "sleep": _SLEEP_EN,
    "close": close_EN,
}

def get_dialogues(lang, key):
    """Return dialogue lines for the key expected by index.py."""
    mapping = _DIALOGUE_MAP_EN if lang == "en" else _DIALOGUE_MAP_ZH
    return list(mapping.get(key, ["..."]))

DIALOG_ZH = _DIALOGUE_MAP_ZH
DIALOG_EN = _DIALOGUE_MAP_EN
