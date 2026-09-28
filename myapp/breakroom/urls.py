from django.urls import path

from .views import (BreakRoomOrganizationView, BreakRoomSettingsView, BreakSessionDetailView,
                    BreakSessionsView, PetChatView, PetCreateView, PetMeView,
                    PetMessagesView, PetOptionsView, PetAppearanceOptionsView,
                    PetSettingsView, PetInteractView, ScenesView,
                    SoundPresetDetailView, SoundPresetsView, SoundsView)

urlpatterns = [
    path('break-room/settings/', BreakRoomSettingsView.as_view()),
    path('break-room/organization/', BreakRoomOrganizationView.as_view()),
    path('break-room/scenes/', ScenesView.as_view()),
    path('break-room/sounds/', SoundsView.as_view()),
    path('break-room/presets/', SoundPresetsView.as_view()),
    path('break-room/presets/<int:pk>/', SoundPresetDetailView.as_view()),
    path('break-room/sessions/', BreakSessionsView.as_view()),
    path('break-room/sessions/<int:pk>/', BreakSessionDetailView.as_view()),
    path('pets/me/', PetMeView.as_view()),
    path('pets/options/', PetOptionsView.as_view()),
    path('pets/appearance-options/', PetAppearanceOptionsView.as_view()),
    path('pets/settings/', PetSettingsView.as_view()),
    path('pets/interact/', PetInteractView.as_view()),
    path('pets/', PetCreateView.as_view()),
    path('pets/chat/', PetChatView.as_view()),
    path('pets/messages/', PetMessagesView.as_view()),
]
