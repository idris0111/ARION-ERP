from rest_framework.permissions import BasePermission

from myapp.models import BreakRoomSettings, Organization, OrganizationMember, PetSettings
from myapp.tenancy import selected_organization_id


def break_room_policy(request):
    selected = selected_organization_id(request)
    if selected is None:
        selected = OrganizationMember.objects.filter(user=request.user, is_active=True).values_list('organization_id', flat=True).first()
    organization = Organization.objects.filter(pk=selected).first() if selected else None
    personal = BreakRoomSettings.objects.filter(user=request.user).first()
    enabled = (organization.break_room_enabled if organization else True) and (personal.enabled if personal else True)
    return {
        'organization_id': selected,
        'organization_enabled': organization.break_room_enabled if organization else True,
        'organization_games_enabled': organization.break_room_games_enabled if organization else True,
        'organization_pet_enabled': organization.break_room_pet_enabled if organization else True,
        'enabled': enabled,
        'games_enabled': enabled and (organization.break_room_games_enabled if organization else True),
        'pet_enabled': enabled and (organization.break_room_pet_enabled if organization else True),
    }


class CanViewBreakRoom(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and break_room_policy(request)['enabled'])


class CanUseGames(CanViewBreakRoom):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and break_room_policy(request)['games_enabled'])


class CanUsePet(CanViewBreakRoom):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and break_room_policy(request)['pet_enabled']
                    and not PetSettings.objects.filter(user=request.user, pet_enabled=False).exists())
