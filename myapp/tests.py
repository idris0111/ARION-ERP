from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from .models import (
    AuditLog, CashAccount, CashTransaction, Counterparty, Debt, Organization,
    Product, Purchase, PurchaseItem, Sale, SaleItem, Stock, StockMovement, Warehouse,
)
from .views import PostPurchaseView, PostSaleView, UnpostPurchaseView, UnpostSaleView


class DocumentPaymentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='admin', role='ADMIN')
        self.factory = APIRequestFactory()
        self.organization = Organization.objects.create(name='Test')
        self.counterparty = Counterparty.objects.create(
            organization=self.organization, name='Partner', counterparty_type='BOTH'
        )
        self.warehouse = Warehouse.objects.create(organization=self.organization, name='Warehouse')
        self.product = Product.objects.create(organization=self.organization, name='Product', sku='P1')
        self.stock = Stock.objects.create(
            warehouse=self.warehouse, product=self.product, quantity=10, average_cost=20
        )
        self.account = CashAccount.objects.create(
            organization=self.organization, name='Cash', account_type='CASH', balance=200
        )
        self.document_number = 0

    def make_document(self, kind, paid_amount, with_account=True):
        self.document_number += 1
        fields = dict(
            organization=self.organization, warehouse=self.warehouse,
            number=f'DOC-{self.document_number}', date=timezone.now(),
            paid_amount=paid_amount, created_by=self.user,
            cash_account=self.account if with_account else None,
        )
        if kind == 'sale':
            document = Sale.objects.create(customer=self.counterparty, **fields)
            SaleItem.objects.create(sale=document, product=self.product, quantity=2, price=50)
        else:
            document = Purchase.objects.create(supplier=self.counterparty, **fields)
            PurchaseItem.objects.create(purchase=document, product=self.product, quantity=2, price=50)
        return document

    def request_action(self, kind, action, document):
        views = {
            ('sale', 'post'): PostSaleView,
            ('sale', 'unpost'): UnpostSaleView,
            ('purchase', 'post'): PostPurchaseView,
            ('purchase', 'unpost'): UnpostPurchaseView,
        }
        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        return views[kind, action].as_view()(request, pk=document.pk)

    def assert_failed_post_unchanged(self, document):
        document.refresh_from_db()
        self.stock.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(document.status, 'DRAFT')
        self.assertEqual(document.total_amount, 0)
        self.assertEqual(document.items.get().total, 0)
        self.assertEqual(self.stock.quantity, 10)
        self.assertEqual(self.stock.average_cost, 20)
        self.assertEqual(self.account.balance, 200)
        self.assertFalse(CashTransaction.objects.exists())
        self.assertFalse(Debt.objects.exists())
        self.assertFalse(StockMovement.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_partial_payment_unpost_and_repost(self):
        for kind, direction, debt_type in [('sale', 1, 'CUSTOMER'), ('purchase', -1, 'SUPPLIER')]:
            with self.subTest(kind=kind):
                document = self.make_document(kind, 40)
                for cycle in range(2):
                    response = self.request_action(kind, 'post', document)
                    self.assertEqual(response.status_code, 200, response.data)
                    document.refresh_from_db()
                    self.account.refresh_from_db()
                    self.stock.refresh_from_db()
                    self.assertEqual(document.status, 'POSTED')
                    self.assertEqual(document.total_amount, 100)
                    self.assertEqual(document.payment_status, 'PARTIAL')
                    self.assertEqual(self.account.balance, 200 + direction * 40)
                    self.assertEqual(self.stock.quantity, 10 - direction * 2)
                    payment = CashTransaction.objects.get(**{kind: document})
                    self.assertEqual(payment.amount, 40)
                    self.assertEqual(payment.transaction_type, 'INCOME' if kind == 'sale' else 'EXPENSE')
                    self.assertEqual(payment.status, 'POSTED')
                    self.assertEqual(payment.organization_id, self.organization.pk)
                    self.assertEqual(payment.counterparty_id, self.counterparty.pk)
                    self.assertEqual(payment.date, document.date)
                    self.assertTrue(payment.number)
                    payment.full_clean()
                    debt = Debt.objects.get(**{kind: document})
                    self.assertEqual(debt.amount, 60)
                    self.assertEqual(debt.paid_amount, 0)
                    self.assertEqual(debt.debt_type, debt_type)
                    self.assertEqual(debt.status, 'OPEN')
                    self.assertEqual(debt.organization_id, self.organization.pk)
                    debt.full_clean()
                    self.assertEqual(self.request_action(kind, 'post', document).status_code, 400)
                    self.assertEqual(CashTransaction.objects.filter(**{kind: document}).count(), 1)
                    self.assertEqual(Debt.objects.filter(**{kind: document}).count(), 1)

                    response = self.request_action(kind, 'unpost', document)
                    self.assertEqual(response.status_code, 200, response.data)
                    document.refresh_from_db()
                    self.account.refresh_from_db()
                    self.stock.refresh_from_db()
                    self.assertEqual(document.status, 'DRAFT')
                    self.assertEqual(self.account.balance, 200)
                    self.assertEqual(self.stock.quantity, 10)
                    self.assertFalse(CashTransaction.objects.exists())
                    self.assertFalse(Debt.objects.exists())
                    self.assertFalse(StockMovement.objects.exists())
                    self.assertEqual(self.request_action(kind, 'unpost', document).status_code, 400)

    def test_full_and_zero_payment(self):
        for kind in ('sale', 'purchase'):
            for paid in (0, 100):
                with self.subTest(kind=kind, paid=paid):
                    document = self.make_document(kind, paid, with_account=bool(paid))
                    response = self.request_action(kind, 'post', document)
                    self.assertEqual(response.status_code, 200, response.data)
                    document.refresh_from_db()
                    self.assertEqual(document.payment_status, 'PAID' if paid else 'UNPAID')
                    self.assertEqual(CashTransaction.objects.count(), int(bool(paid)))
                    self.assertEqual(Debt.objects.count(), int(not paid))
                    if not paid:
                        self.assertEqual(Debt.objects.get().amount, 100)
                    self.assertEqual(self.request_action(kind, 'unpost', document).status_code, 200)
                    self.account.refresh_from_db()
                    self.assertEqual(self.account.balance, 200)
                    self.assertFalse(Debt.objects.exists())
                    self.assertFalse(CashTransaction.objects.exists())

    def test_overpayment_rolls_back_posting(self):
        for kind in ('sale', 'purchase'):
            with self.subTest(kind=kind):
                document = self.make_document(kind, 101)
                response = self.request_action(kind, 'post', document)
                self.assertEqual(response.status_code, 400)
                self.assertIn('Оплата больше суммы', str(response.data))
                self.assert_failed_post_unchanged(document)

    def test_missing_account_rolls_back_posting(self):
        for kind in ('sale', 'purchase'):
            with self.subTest(kind=kind):
                document = self.make_document(kind, 40, with_account=False)
                response = self.request_action(kind, 'post', document)
                self.assertEqual(response.status_code, 400)
                self.assertIn('Выберите кассу для оплаты', str(response.data))
                self.assert_failed_post_unchanged(document)

    def test_insufficient_purchase_balance_rolls_back_posting(self):
        document = self.make_document('purchase', 100)
        self.account.balance = 50
        self.account.save()
        response = self.request_action('purchase', 'post', document)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Недостаточно денег в кассе', str(response.data))
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 50)
        self.account.balance = 200
        self.account.save()
        self.assert_failed_post_unchanged(document)

    def test_insufficient_sale_balance_rolls_back_unposting(self):
        document = self.make_document('sale', 40)
        self.assertEqual(self.request_action('sale', 'post', document).status_code, 200)
        payment_id = CashTransaction.objects.get().pk
        debt_id = Debt.objects.get().pk
        movement_id = StockMovement.objects.get().pk
        self.account.balance = Decimal('10')
        self.account.save()
        response = self.request_action('sale', 'unpost', document)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Недостаточно денег для отмены продажи', str(response.data))
        document.refresh_from_db()
        self.stock.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(document.status, 'POSTED')
        self.assertEqual(self.stock.quantity, 8)
        self.assertEqual(self.account.balance, 10)
        self.assertEqual(CashTransaction.objects.get().pk, payment_id)
        self.assertEqual(Debt.objects.get().pk, debt_id)
        self.assertEqual(StockMovement.objects.get().pk, movement_id)
        self.assertFalse(AuditLog.objects.filter(action='CANCEL').exists())
