"""Private reply adapter. A future provider can replace this without changing views."""

from .pet_service import reply_to_pet as fallback_reply


def reply_to_pet(pet, message):
    answer = fallback_reply(pet, message)
    answer['animation'] = 'sit' if answer['mood'] in ('calm', 'supportive') else 'talk'
    return answer
