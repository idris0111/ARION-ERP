"""Optional media URLs may be configured later without changing the UI contract."""

SCENES = [
    ('alpine', 'Alpine Mountains', 'Clear air and distant peaks', 'mountains'),
    ('forest', 'Green Forest', 'A quiet path between tall trees', 'forest'),
    ('rainforest', 'Rainy Forest', 'Soft rain beneath the canopy', 'forest'),
    ('ocean', 'Ocean', 'A calm horizon and rolling water', 'ocean'),
    ('beach', 'Beach', 'Warm light along the shore', 'ocean'),
    ('waterfall', 'Waterfall', 'Water moving over smooth stone', 'forest'),
    ('lake', 'Lake', 'Still reflections at the waterline', 'mountains'),
    ('snow', 'Snow Mountains', 'A quiet winter landscape', 'mountains'),
    ('night', 'Night Forest', 'Cool air under a dark sky', 'forest'),
    ('desert', 'Desert Sunset', 'A slow evening in warm colors', 'mountains'),
    ('garden', 'Japanese Garden', 'A peaceful place to pause', 'forest'),
    ('river', 'River', 'A gentle current through greenery', 'forest'),
    ('clouds', 'Clouds', 'Space to look up and breathe', 'mountains'),
    ('animals', 'Wildlife', 'A quiet moment with nature', 'forest'),
    ('fireplace', 'Fireplace', 'A warm place to unwind', 'forest'),
]

SOUNDS = [
    ('rain', 'Rain', 'CloudRain'), ('thunder', 'Thunder', 'CloudLightning'),
    ('forest', 'Forest', 'Trees'), ('birds', 'Birds', 'Bird'),
    ('ocean', 'Ocean', 'Waves'), ('river', 'River', 'Waves'),
    ('fireplace', 'Fireplace', 'Flame'), ('wind', 'Wind', 'Wind'),
    ('night', 'Night', 'Moon'), ('cafe', 'Cafe', 'Coffee'),
    ('white-noise', 'White noise', 'Radio'),
]


def scene_data():
    return [dict(id=key, name=name, description=description, image_key=image_key,
                 image_url='', video_url='', audio_url='', thumbnail_url='')
            for key, name, description, image_key in SCENES]


def sound_data():
    return [dict(id=key, name=name, icon=icon, audio_url='') for key, name, icon in SOUNDS]
