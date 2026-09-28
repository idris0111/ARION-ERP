from decimal import Decimal
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import ExchangeRate
from .exchange_rate_service import fetch_provider_rates


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class ExchangeRateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='rate-user')

    def test_endpoint_requires_authentication(self):
        self.assertEqual(self.client.get('/api/exchange-rates/').status_code, 401)

    @patch('myapp.exchange_rate_service.urlopen')
    def test_provider_request_identifies_the_backend(self, urlopen):
        urlopen.return_value = BytesIO(b'[{"base":"TJS","quote":"USD","rate":0.11},{"base":"TJS","quote":"EUR","rate":0.10},{"base":"TJS","quote":"CNY","rate":0.80}]')
        self.assertEqual(fetch_provider_rates()['USD'], Decimal('0.11'))
        self.assertIn('NexoraERP', urlopen.call_args.args[0].get_header('User-agent'))

    @patch('myapp.exchange_rate_service.fetch_provider_rates')
    def test_persists_rates_and_uses_database_on_provider_failure(self, fetch):
        fetch.return_value = {'USD': Decimal('0.11'), 'EUR': Decimal('0.10'), 'CNY': Decimal('0.80')}
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/exchange-rates/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data['rates']['USD']), Decimal('0.11'))
        self.assertEqual(ExchangeRate.objects.count(), 3)

        ExchangeRate.objects.update(updated_at=timezone.now()-timedelta(hours=4))
        fetch.side_effect = OSError('provider unavailable')
        response = self.client.get('/api/exchange-rates/')
        self.assertEqual(response.data['rates']['USD'], '0.1100000000')
        self.assertTrue(response.data['stale'])
