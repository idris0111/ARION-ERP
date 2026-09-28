from rest_framework import serializers

from myapp.models import BreakRoomSettings, BreakSession, Pet, PetAppearance, PetMessage, PetSettings, SoundPreset
from .catalog import SOUNDS
from .pet_options import APPEARANCE, SPECIES


class BreakRoomSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreakRoomSettings
        fields = ('enabled', 'show_pet_on_dashboard', 'reminders', 'pet_sound',
                  'pet_animations', 'nature_autoplay', 'default_duration',
                  'focus_mode', 'reduced_motion', 'volume')

    def validate_default_duration(self, value):
        if value not in (2, 5, 10, 15):
            raise serializers.ValidationError('Choose 2, 5, 10 or 15 minutes.')
        return value

    def validate_volume(self, value):
        if value > 100:
            raise serializers.ValidationError('Volume must be between 0 and 100.')
        return value


class PetAppearanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetAppearance
        fields = tuple(APPEARANCE) + ('ears', 'tail')


class PetSerializer(serializers.ModelSerializer):
    appearance = PetAppearanceSerializer(required=False)

    def validate_animal_type(self, value):
        if value not in SPECIES:
            raise serializers.ValidationError('Unknown species.')
        return value

    class Meta:
        model = Pet
        fields = ('id', 'name', 'animal_type', 'personality', 'communication_style',
                  'color', 'eyes', 'ears', 'accessory', 'clothes', 'background',
                  'mood', 'level', 'experience', 'is_active', 'appearance', 'created_at', 'updated_at')
        read_only_fields = ('id', 'mood', 'level', 'experience', 'created_at', 'updated_at')

    def validate(self, attrs):
        appearance = attrs.get('appearance')
        if appearance:
            species = attrs.get('animal_type', getattr(self.instance, 'animal_type', 'cat'))
            if species not in SPECIES:
                raise serializers.ValidationError({'animal_type': 'Unknown species.'})
            for key, value in appearance.items():
                choices = ['classic', *SPECIES[species]['ears' if key == 'ears' else 'tails']] if key in ('ears', 'tail') else APPEARANCE.get(key)
                if choices is not None and value not in choices:
                    raise serializers.ValidationError({'appearance': {key: 'Unsupported option.'}})
        return attrs

    def create(self, validated_data):
        appearance = validated_data.pop('appearance', {})
        pet = super().create(validated_data)
        PetAppearance.objects.create(pet=pet, **appearance)
        return pet

    def update(self, instance, validated_data):
        appearance = validated_data.pop('appearance', None)
        pet = super().update(instance, validated_data)
        if appearance is not None:
            row, _ = PetAppearance.objects.get_or_create(pet=pet)
            for key, value in appearance.items():
                setattr(row, key, value)
            row.save()
        return pet


class PetSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetSettings
        fields = ('pet_enabled', 'show_mini_pet', 'show_on_all_pages', 'auto_reactions',
                  'animation_enabled', 'sound_enabled', 'reduced_motion',
                  'focus_mode_hides_pet', 'default_mode', 'preferred_position',
                  'reminder_frequency', 'quality')

    def validate_default_mode(self, value):
        if value not in ('mini', 'panel'):
            raise serializers.ValidationError('Choose mini or panel.')
        return value

    def validate_quality(self, value):
        if value not in ('high', 'balanced', 'performance'):
            raise serializers.ValidationError('Unknown quality.')
        return value

    def validate_reminder_frequency(self, value):
        if value not in ('NEVER', 'RARELY', 'SOMETIMES', 'OFTEN'):
            raise serializers.ValidationError('Unknown frequency.')
        return value

    def validate_preferred_position(self, value):
        if not isinstance(value, dict) or set(value) - {'x', 'y'} or any(
            not isinstance(coord, (int, float)) or isinstance(coord, bool) or not 0 <= coord <= 10000
            for coord in value.values()
        ):
            raise serializers.ValidationError('Expected x and y coordinates.')
        return value


class PetMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetMessage
        fields = ('id', 'role', 'message', 'created_at')
        read_only_fields = fields


class SoundPresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoundPreset
        fields = ('id', 'name', 'sounds', 'master_volume', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_sounds(self, value):
        valid = {key for key, *_ in SOUNDS}
        if not isinstance(value, dict) or any(key not in valid or not isinstance(level, int) or isinstance(level, bool) or not 0 <= level <= 100 for key, level in value.items()):
            raise serializers.ValidationError('Use sound IDs with volumes from 0 to 100.')
        return value

    def validate_master_volume(self, value):
        if value > 100:
            raise serializers.ValidationError('Volume must be between 0 and 100.')
        return value


class BreakSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreakSession
        fields = ('id', 'break_type', 'started_at', 'ended_at', 'duration_seconds')
        read_only_fields = ('id', 'started_at', 'ended_at', 'duration_seconds')
