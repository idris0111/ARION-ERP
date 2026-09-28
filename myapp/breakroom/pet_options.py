"""Server-owned choices for the modular pet renderer and creator."""

SPECIES = {
    'cat': {'label': 'Cat', 'ears': ['classic', 'pointed'], 'tails': ['classic', 'fluffy']},
    'dog': {'label': 'Dog', 'ears': ['classic', 'floppy'], 'tails': ['classic', 'short']},
    'fox': {'label': 'Fox', 'ears': ['pointed'], 'tails': ['fluffy']},
    'panda': {'label': 'Panda', 'ears': ['round'], 'tails': ['short']},
    'rabbit': {'label': 'Rabbit', 'ears': ['long', 'soft'], 'tails': ['short']},
    'bear': {'label': 'Bear', 'ears': ['round'], 'tails': ['short']},
    'wolf': {'label': 'Wolf', 'ears': ['pointed'], 'tails': ['fluffy']},
}

APPEARANCE = {
    'body_style': ['classic', 'compact', 'tall'],
    'primary_color': ['sand', 'cloud', 'cocoa', 'peach', 'sage', 'slate', 'cream', 'charcoal'],
    'secondary_color': ['cream', 'sand', 'cloud', 'cocoa', 'peach', 'sage', 'slate', 'charcoal'],
    'eye_color': ['warm', 'blue', 'green', 'amber'],
    'face_markings': ['', 'mask', 'blaze', 'freckles'],
    'body_markings': ['', 'spots', 'stripe'],
    'clothes': ['', 'hoodie', 'sweater', 'shirt', 'jacket', 'scarf'],
    'accessory': ['', 'collar', 'bow', 'glasses', 'hat', 'bell', 'necklace', 'headphones'],
    'room': ['cozy', 'forest', 'mountains', 'beach', 'night', 'minimal'],
}

PERSONALITIES = ['friendly', 'funny', 'calm', 'energetic', 'motivating', 'smart', 'playful']
STYLES = ['short', 'normal', 'talkative']
INTERACTIONS = {
    'pet': ('happy', 'happy', 'Мне приятно, что ты рядом.'),
    'joke': ('playful', 'playful', 'Почему облако не спешит? Оно любит плыть по своему расписанию.'),
    'support': ('supportive', 'calm', 'Давай сделаем короткую паузу. Я рядом.'),
    'motivate': ('happy', 'happy', 'Один спокойный шаг за раз. У тебя получится.'),
    'rest': ('calm', 'sit', 'Можем выбрать природу, звуки или дыхание.'),
    'play': ('playful', 'playful', 'Небольшая игра поможет переключиться.'),
}
