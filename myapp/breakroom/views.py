from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.models import BreakRoomSettings, BreakSession, Organization, Pet, PetAppearance, PetInteraction, PetMessage, PetSettings, SoundPreset
from myapp.permissions import IsAdminOrDirector
from myapp.tenancy import selected_organization_id
from .catalog import scene_data, sound_data
from .permissions import CanUseGames, CanUsePet, CanViewBreakRoom, break_room_policy
from .pet_ai_service import reply_to_pet
from .pet_options import APPEARANCE, INTERACTIONS, PERSONALITIES, SPECIES, STYLES
from .serializers import (BreakRoomSettingsSerializer, BreakSessionSerializer,
                          PetMessageSerializer, PetSerializer, PetSettingsSerializer, SoundPresetSerializer)


class BreakRoomSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings, _ = BreakRoomSettings.objects.get_or_create(user=request.user)
        return Response({**BreakRoomSettingsSerializer(settings).data, 'policy': break_room_policy(request)})

    def patch(self, request):
        settings, _ = BreakRoomSettings.objects.get_or_create(user=request.user)
        serializer = BreakRoomSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({**serializer.data, 'policy': break_room_policy(request)})


class BreakRoomOrganizationView(APIView):
    permission_classes = [IsAdminOrDirector]

    def patch(self, request):
        organization_id = selected_organization_id(request)
        if organization_id is None:
            raise ValidationError('Выберите организацию.')
        organization = Organization.objects.filter(pk=organization_id).first()
        if organization is None:
            raise NotFound('Организация не найдена.')
        fields = ('break_room_enabled', 'break_room_games_enabled', 'break_room_pet_enabled')
        values = {key: value for key, value in request.data.items() if key in fields}
        if not values or any(not isinstance(value, bool) for value in values.values()):
            raise ValidationError('Передайте логические настройки Break Room.')
        for key, value in values.items():
            setattr(organization, key, value)
        organization.save(update_fields=list(values))
        return Response(break_room_policy(request))


class ScenesView(APIView):
    permission_classes = [CanViewBreakRoom]

    def get(self, request):
        return Response(scene_data())


class SoundsView(APIView):
    permission_classes = [CanViewBreakRoom]

    def get(self, request):
        return Response(sound_data())


class PetMeView(APIView):
    permission_classes = [CanUsePet]

    def get(self, request):
        pet = Pet.objects.filter(user=request.user).first()
        if pet:
            PetAppearance.objects.get_or_create(pet=pet)
        return Response(PetSerializer(pet).data if pet else None)

    def patch(self, request):
        pet = Pet.objects.filter(user=request.user).first()
        if pet is None:
            raise NotFound('Питомец не найден.')
        PetAppearance.objects.get_or_create(pet=pet)
        serializer = PetSerializer(pet, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        Pet.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PetCreateView(APIView):
    permission_classes = [CanUsePet]

    def post(self, request):
        if Pet.objects.filter(user=request.user).exists():
            raise ValidationError('У вас уже есть питомец.')
        serializer = PetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PetOptionsView(APIView):
    permission_classes = [CanUsePet]

    def get(self, request):
        return Response({'species': SPECIES, 'personalities': PERSONALITIES, 'styles': STYLES})


class PetAppearanceOptionsView(APIView):
    permission_classes = [CanUsePet]

    def get(self, request):
        return Response(APPEARANCE)


class PetSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings, _ = PetSettings.objects.get_or_create(user=request.user)
        return Response(PetSettingsSerializer(settings).data)

    def patch(self, request):
        settings, _ = PetSettings.objects.get_or_create(user=request.user)
        serializer = PetSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PetInteractView(APIView):
    permission_classes = [CanUsePet]

    def post(self, request):
        pet = Pet.objects.filter(user=request.user).first()
        if pet is None:
            raise NotFound('Pet not found.')
        kind = request.data.get('interaction_type')
        if kind not in INTERACTIONS:
            raise ValidationError({'interaction_type': 'Unknown interaction.'})
        mood, animation, message = INTERACTIONS[kind]
        PetInteraction.objects.create(pet=pet, interaction_type=kind)
        old_ids = list(PetInteraction.objects.filter(pet=pet).order_by('-id').values_list('id', flat=True)[100:])
        if old_ids:
            PetInteraction.objects.filter(id__in=old_ids).delete()
        pet.mood = mood
        pet.save(update_fields=['mood', 'updated_at'])
        return Response({'message': message, 'mood': mood, 'animation': animation})


class PetMessagesView(APIView):
    permission_classes = [CanUsePet]

    def get(self, request):
        pet = Pet.objects.filter(user=request.user).first()
        if pet is None:
            raise NotFound('Питомец не найден.')
        messages = list(PetMessage.objects.filter(pet=pet, user=request.user).order_by('-created_at', '-id')[:60])
        return Response(PetMessageSerializer(reversed(messages), many=True).data)

    def delete(self, request):
        PetMessage.objects.filter(user=request.user, pet__user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PetChatView(APIView):
    permission_classes = [CanUsePet]

    def post(self, request):
        pet = Pet.objects.filter(user=request.user).first()
        if pet is None:
            raise NotFound('Питомец не найден.')
        message = request.data.get('message')
        if not isinstance(message, str) or not message.strip() or len(message.strip()) > 500:
            raise ValidationError({'message': 'Введите сообщение до 500 символов.'})
        answer = reply_to_pet(pet, message.strip())
        with transaction.atomic():
            PetMessage.objects.create(pet=pet, user=request.user, role='user', message=message.strip())
            PetMessage.objects.create(pet=pet, user=request.user, role='pet', message=answer['message'])
            pet.mood = answer['mood']
            pet.save(update_fields=['mood', 'updated_at'])
            old_ids = list(PetMessage.objects.filter(pet=pet).order_by('-id').values_list('id', flat=True)[80:])
            if old_ids:
                PetMessage.objects.filter(id__in=old_ids).delete()
        return Response(answer)


class SoundPresetsView(APIView):
    permission_classes = [CanViewBreakRoom]

    def get(self, request):
        return Response(SoundPresetSerializer(SoundPreset.objects.filter(user=request.user), many=True).data)

    def post(self, request):
        if SoundPreset.objects.filter(user=request.user).count() >= 12:
            raise ValidationError('Можно сохранить не более 12 наборов звуков.')
        serializer = SoundPresetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SoundPresetDetailView(APIView):
    permission_classes = [CanViewBreakRoom]

    def delete(self, request, pk):
        deleted, _ = SoundPreset.objects.filter(pk=pk, user=request.user).delete()
        if not deleted:
            raise NotFound('Набор не найден.')
        return Response(status=status.HTTP_204_NO_CONTENT)


class BreakSessionsView(APIView):
    permission_classes = [CanViewBreakRoom]

    def get(self, request):
        today = timezone.localdate()
        sessions = BreakSession.objects.filter(user=request.user, started_at__date=today, ended_at__isnull=False)
        return Response({'sessions_today': sessions.count(), 'seconds_today': sessions.aggregate(total=Sum('duration_seconds'))['total'] or 0})

    def post(self, request):
        serializer = BreakSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        break_type = serializer.validated_data['break_type']
        policy = break_room_policy(request)
        if break_type == 'game' and not policy['games_enabled'] or break_type == 'pet' and not policy['pet_enabled']:
            raise PermissionDenied('Этот раздел отключён для организации.')
        session = serializer.save(user=request.user)
        return Response(BreakSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class BreakSessionDetailView(APIView):
    permission_classes = [CanViewBreakRoom]

    def patch(self, request, pk):
        session = BreakSession.objects.filter(pk=pk, user=request.user).first()
        if session is None:
            raise NotFound('Перерыв не найден.')
        if session.ended_at is None:
            session.ended_at = timezone.now()
            session.duration_seconds = min(3600, max(0, int((session.ended_at - session.started_at).total_seconds())))
            session.save(update_fields=['ended_at', 'duration_seconds'])
        return Response(BreakSessionSerializer(session).data)
