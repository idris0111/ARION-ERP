from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Organization, OrganizationMember, Pet, PetMessage


class BreakRoomApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name='Break Room company')
        self.owner = get_user_model().objects.create_user(username='break-owner', role='MANAGER')
        self.other = get_user_model().objects.create_user(username='break-other', role='MANAGER')
        for user in (self.owner, self.other):
            OrganizationMember.objects.create(user=user, organization=self.organization, role='MANAGER')
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
        self.headers = {'HTTP_X_ORGANIZATION_ID': str(self.organization.pk)}

    def test_disabled_company_blocks_content_but_allows_personal_settings(self):
        self.organization.break_room_enabled = False
        self.organization.save(update_fields=['break_room_enabled'])

        settings = self.client.get('/api/break-room/settings/', **self.headers)
        self.assertEqual(settings.status_code, 200)
        self.assertFalse(settings.data['policy']['enabled'])
        self.assertEqual(self.client.get('/api/break-room/scenes/', **self.headers).status_code, 403)
        self.assertEqual(self.client.get('/api/pets/me/', **self.headers).status_code, 403)

    def test_pet_messages_are_private_and_can_be_cleared(self):
        pet = Pet.objects.create(user=self.owner, name='Milo', animal_type='cat')
        PetMessage.objects.create(pet=pet, user=self.owner, role='user', message='Private message')
        self.client.force_authenticate(user=self.other)
        self.assertIsNone(self.client.get('/api/pets/me/', **self.headers).data)
        self.assertEqual(self.client.get('/api/pets/messages/', **self.headers).status_code, 404)
        self.assertEqual(self.client.delete('/api/pets/messages/', **self.headers).status_code, 204)
        self.assertEqual(PetMessage.objects.filter(pet=pet).count(), 1)

        self.client.force_authenticate(user=self.owner)
        self.assertEqual(len(self.client.get('/api/pets/messages/', **self.headers).data), 1)
        self.assertEqual(self.client.delete('/api/pets/messages/', **self.headers).status_code, 204)
        self.assertFalse(PetMessage.objects.filter(pet=pet).exists())

    def test_game_policy_blocks_game_sessions_only(self):
        self.organization.break_room_games_enabled = False
        self.organization.save(update_fields=['break_room_games_enabled'])
        game = self.client.post('/api/break-room/sessions/', {'break_type': 'game'}, **self.headers)
        self.assertEqual(game.status_code, 403)
        nature = self.client.post('/api/break-room/sessions/', {'break_type': 'nature'}, **self.headers)
        self.assertEqual(nature.status_code, 201)
        ended = self.client.patch(f"/api/break-room/sessions/{nature.data['id']}/", {}, **self.headers)
        self.assertEqual(ended.status_code, 200)
        self.assertIsNotNone(ended.data['ended_at'])

    def test_pet_creator_appearance_and_settings_are_private(self):
        options = self.client.get('/api/pets/options/', **self.headers)
        self.assertEqual(options.status_code, 200)
        self.assertIn('fox', options.data['species'])
        created = self.client.post('/api/pets/', {
            'name': 'Lumi', 'animal_type': 'fox', 'personality': 'playful',
            'appearance': {'primary_color': 'peach', 'ears': 'pointed', 'tail': 'fluffy'},
        }, format='json', **self.headers)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['appearance']['tail'], 'fluffy')

        invalid = self.client.patch('/api/pets/me/', {
            'appearance': {'ears': 'floppy'},
        }, format='json', **self.headers)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.client.patch('/api/pets/settings/', {
            'quality': 'performance', 'show_mini_pet': True,
        }, format='json', **self.headers).status_code, 200)
        self.assertEqual(self.client.patch('/api/pets/settings/', {
            'pet_enabled': False,
        }, format='json', **self.headers).status_code, 200)
        self.assertEqual(self.client.get('/api/pets/me/', **self.headers).status_code, 403)
        self.assertEqual(self.client.patch('/api/pets/settings/', {
            'pet_enabled': True,
        }, format='json', **self.headers).status_code, 200)

        self.client.force_authenticate(user=self.other)
        self.assertIsNone(self.client.get('/api/pets/me/', **self.headers).data)
        self.assertFalse(self.client.get('/api/pets/settings/', **self.headers).data['show_mini_pet'])

        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.post('/api/pets/interact/', {
            'interaction_type': 'pet',
        }, format='json', **self.headers).data['animation'], 'happy')
        self.assertEqual(self.client.delete('/api/pets/me/', **self.headers).status_code, 204)
        self.assertIsNone(self.client.get('/api/pets/me/', **self.headers).data)
