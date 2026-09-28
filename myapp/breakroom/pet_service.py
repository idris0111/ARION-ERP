"""Private pet replies. Replace reply_to_pet() with an AI adapter if desired."""
from django.utils import timezone


def reply_to_pet(pet, message):
    text = message.casefold()
    if any(word in text for word in ('плохо', 'тяжело', 'устал', 'устала', 'sad', 'tired', 'bad day')):
        answer, mood = ('Похоже, день непростой. Давай сделаем короткую паузу: можно включить дождь или просто спокойно посидеть.', 'calm')
    elif any(word in text for word in ('шут', 'joke', 'funny')):
        answer, mood = ('Почему облако не спешит? Оно любит плыть по своему расписанию.', 'happy')
    elif any(word in text for word in ('мотивац', 'motivat', 'работ', 'задач')):
        answer, mood = ('Ты уже многое сделал сегодня. Один спокойный шаг за раз — хороший темп.', 'happy')
    elif any(word in text for word in ('отдых', 'relax', 'break', 'дыш')):
        answer, mood = ('Давай отдохнём пару минут. Медленный вдох, затем мягкий выдох.', 'calm')
    elif any(word in text for word in ('как дела', 'how are you')):
        answer, mood = ('Рад тебя видеть. Я рядом, если захочешь сделать паузу.', 'curious')
    else:
        hour = timezone.localtime().hour
        greeting = 'Доброе утро' if hour < 12 else 'Добрый день' if hour < 18 else 'Добрый вечер'
        answer, mood = (f'{greeting}! Я {pet.name}. Как проходит твой день?', 'curious')
    if pet.personality == 'funny' and mood != 'calm':
        answer += ' Обещаю не отвлекать от важных дел.'
    elif pet.personality == 'motivating' and mood != 'calm':
        answer += ' У тебя получится.'
    elif pet.personality == 'calm':
        answer = answer.replace('!', '.')
    elif pet.personality == 'playful' and mood != 'calm':
        answer += ' Давай улыбнёмся и выберем маленькое приключение.'
    elif pet.personality == 'energetic' and mood != 'calm':
        answer += ' У нас всё получится, шаг за шагом!'
    elif pet.personality == 'smart' and mood != 'calm':
        answer += ' Если хочешь, разберём это по одному небольшому шагу.'
    if pet.communication_style == 'short':
        answer = answer.split('. ')[0].rstrip('.') + '.'
    elif pet.communication_style == 'talkative':
        answer += ' Можем выбрать тихую сцену или поговорить ещё немного.'
    return {'message': answer, 'mood': mood}
