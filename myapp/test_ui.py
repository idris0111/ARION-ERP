from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import resolve
from rest_framework.test import APIClient

from .models import Organization, OrganizationMember, Product
from .ui_views import erp_ui


class ErpUiRoutingTests(SimpleTestCase):
    def test_react_shell_routes(self):
        with TemporaryDirectory() as directory:
            index = Path(directory) / 'frontend' / 'dist' / 'index.html'
            index.parent.mkdir(parents=True)
            index.write_text('<!doctype html><title>NEXORA ERP</title>', encoding='utf-8')
            with override_settings(BASE_DIR=Path(directory)):
                for path in (
                    '/', '/m/products', '/m/products/new', '/m/products/12',
                    '/m/products/12/edit', '/m/sale-returns', '/m/sale-returns/12',
                    '/pos/', '/inventory/', '/reports/',
                ):
                    with self.subTest(path=path):
                        self.assertIs(resolve(path).func, erp_ui)
                        self.assertContains(self.client.get(path), 'NEXORA ERP')


class SelectedOrganizationTests(TestCase):
    def test_selected_company_filters_list_and_report(self):
        user = get_user_model().objects.create_user(username='company-user', role='MANAGER')
        first = Organization.objects.create(name='First')
        second = Organization.objects.create(name='Second')
        OrganizationMember.objects.create(user=user, organization=first, role='MANAGER')
        OrganizationMember.objects.create(user=user, organization=second, role='MANAGER')
        Product.objects.create(organization=first, name='First item', sku='ONE')
        Product.objects.create(organization=second, name='Second item', sku='TWO')
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/products/', HTTP_X_ORGANIZATION_ID=str(first.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['sku'] for item in response.data['results']], ['ONE'])
        response = client.get('/api/dashboard/', HTTP_X_ORGANIZATION_ID=str(first.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['products'], 1)

        third = Organization.objects.create(name='Not a member')
        response = client.get('/api/products/', HTTP_X_ORGANIZATION_ID=str(third.id))
        self.assertEqual(response.status_code, 403)
