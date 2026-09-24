from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('ERP info', {
            'fields': (
                'role',
                'phone',
                'avatar',
                'is_verified',
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('ERP info', {
            'fields': (
                'role',
                'phone',
            )
        }),
    )

    list_display = [
        'id',
        'username',
        'first_name',
        'last_name',
        'role',
        'phone',
        'is_active',
        'is_staff',
    ]

    list_filter = [
        'role',
        'is_active',
        'is_staff',
        'is_verified',
    ]

    search_fields = [
        'username',
        'first_name',
        'last_name',
        'phone',
        'email',
    ]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'position',
        'hire_date',
        'salary',
        'is_employee',
    ]

    list_filter = [
        'is_employee',
        'position',
    ]

    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'position',
        'passport',
    ]