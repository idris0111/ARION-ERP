from rest_framework import serializers
from .models import User, Profile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'password',
            'first_name',
            'last_name',
            'email',
            'phone',
            'role',
        ]
        read_only_fields = ['role']

    def create(self, validated_data):
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        Profile.objects.create(user=user)

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'phone',
            'role',
            'avatar',
            'is_verified',
            'is_active',
            'created_at',
        ]

        read_only_fields = [
            'id',
            'is_verified',
            'role',
            'is_active',
            'created_at',
        ]


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source='user.username',
        read_only=True
    )

    first_name = serializers.CharField(
        source='user.first_name',
        read_only=True
    )

    last_name = serializers.CharField(
        source='user.last_name',
        read_only=True
    )

    email = serializers.EmailField(
        source='user.email',
        read_only=True
    )

    phone = serializers.CharField(
        source='user.phone',
        read_only=True
    )

    role = serializers.CharField(
        source='user.role',
        read_only=True
    )

    class Meta:
        model = Profile
        fields = [
            'id',
            'user',
            'username',
            'first_name',
            'last_name',
            'email',
            'phone',
            'role',
            'middle_name',
            'address',
            'birth_date',
            'passport',
            'position',
            'hire_date',
            'salary',
            'is_employee',
        ]

        read_only_fields = [
            'id',
            'user',
        ]
