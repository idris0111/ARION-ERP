from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from .models import (
    AuditLog, CashAccount, CashTransaction, Counterparty, Debt, Employee, Notification,
    Organization, Product, Purchase, PurchaseItem, Sale, SaleItem, SalaryPayment, Stock,
    StockMovement, Warehouse,
)
from .views import (
    NotificationListView, PayDebtView, PaySalaryView, PostPurchaseView, PostSaleView,
    ReadAllNotificationsView, ReadNotificationView, UnpostPurchaseView, UnpostSaleView,
    UnreadNotificationListView, notify_roles,
)


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

    def pay_debt(self, debt, amount=None, cash_account=None):
        data = {}
        if amount is not None:
            data['amount'] = amount
        if cash_account is not None:
            data['cash_account'] = cash_account.pk
        request = self.factory.post('/', data, format='json')
        force_authenticate(request, user=self.user)
        return PayDebtView.as_view()(request, pk=debt.pk)

    def make_debt(self, debt_type, amount=100):
        return Debt.objects.create(
            organization=self.organization,
            counterparty=self.counterparty,
            debt_type=debt_type,
            amount=amount,
            status='OPEN',
        )

    def make_salary(self, amount=100, with_account=True):
        employee = Employee.objects.create(
            organization=self.organization,
            first_name='Test',
            last_name='Employee',
            hire_date=timezone.localdate(),
        )
        return SalaryPayment.objects.create(
            employee=employee,
            cash_account=self.account if with_account else None,
            amount=amount,
            month=timezone.localdate().replace(day=1),
        )

    def pay_salary(self, salary):
        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        return PaySalaryView.as_view()(request, pk=salary.pk)

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
                    notification = Notification.objects.filter(
                        user=self.user,
                        notification_type=kind.upper(),
                    ).latest('created_at')
                    self.assertIn(document.number, notification.message)
                    self.assertIn(str(document.total_amount), notification.message)
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

    def test_customer_debt_payment_moves_money_and_updates_debt(self):
        debt = self.make_debt('CUSTOMER')

        response = self.pay_debt(debt, 40, self.account)
        self.assertEqual(response.status_code, 200, response.data)
        debt.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(debt.paid_amount, 40)
        self.assertEqual(debt.status, 'PARTIAL')
        self.assertEqual(self.account.balance, 240)
        self.assertEqual(response.data['remaining'], Decimal('60'))
        payment = CashTransaction.objects.get()
        self.assertEqual(payment.transaction_type, 'INCOME')
        self.assertEqual(payment.amount, 40)
        self.assertEqual(payment.organization, self.organization)
        self.assertEqual(payment.counterparty, self.counterparty)
        self.assertEqual(payment.created_by, self.user)
        payment.full_clean()
        self.assertFalse(Notification.objects.filter(notification_type='DEBT').exists())

        response = self.pay_debt(debt, 60, self.account)
        self.assertEqual(response.status_code, 200, response.data)
        debt.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(debt.paid_amount, 100)
        self.assertEqual(debt.status, 'PAID')
        self.assertEqual(self.account.balance, 300)
        self.assertEqual(CashTransaction.objects.count(), 2)
        self.assertEqual(AuditLog.objects.filter(action='UPDATE').count(), 2)
        notification = Notification.objects.get(notification_type='DEBT')
        self.assertEqual(notification.title, 'Долг погашен')
        self.assertIn(str(debt.id), notification.message)

    def test_supplier_debt_payment_moves_money(self):
        debt = self.make_debt('SUPPLIER')
        response = self.pay_debt(debt, 100, self.account)
        self.assertEqual(response.status_code, 200, response.data)
        debt.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(debt.status, 'PAID')
        self.assertEqual(self.account.balance, 100)
        payment = CashTransaction.objects.get()
        self.assertEqual(payment.transaction_type, 'EXPENSE')
        self.assertEqual(payment.amount, 100)

    def test_supplier_debt_insufficient_balance_changes_nothing(self):
        debt = self.make_debt('SUPPLIER', amount=300)
        response = self.pay_debt(debt, 300, self.account)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Недостаточно денег', str(response.data))
        debt.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(debt.paid_amount, 0)
        self.assertEqual(debt.status, 'OPEN')
        self.assertEqual(self.account.balance, 200)
        self.assertFalse(CashTransaction.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_debt_payment_validation(self):
        debt = self.make_debt('CUSTOMER')
        cases = [
            ({}, 'Укажите amount и cash_account'),
            ({'amount': 'abc', 'cash_account': self.account.pk}, 'Неверная сумма'),
            ({'amount': 'NaN', 'cash_account': self.account.pk}, 'Неверная сумма'),
            ({'amount': 0, 'cash_account': self.account.pk}, 'Укажите amount и cash_account'),
            ({'amount': -1, 'cash_account': self.account.pk}, 'Сумма должна быть больше 0'),
            ({'amount': 101, 'cash_account': self.account.pk}, 'Остаток долга 100.00'),
        ]
        for data, error in cases:
            with self.subTest(data=data):
                request = self.factory.post('/', data, format='json')
                force_authenticate(request, user=self.user)
                response = PayDebtView.as_view()(request, pk=debt.pk)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data['error'], error)

        debt.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(debt.paid_amount, 0)
        self.assertEqual(self.account.balance, 200)
        self.assertFalse(CashTransaction.objects.exists())

    def test_salary_payment_moves_money_and_marks_paid(self):
        salary = self.make_salary(50)
        response = self.pay_salary(salary)

        self.assertEqual(response.status_code, 200, response.data)
        salary.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(salary.status, 'PAID')
        self.assertEqual(self.account.balance, 150)
        self.assertEqual(response.data['cash_balance'], Decimal('150'))
        payment = CashTransaction.objects.get()
        self.assertEqual(payment.organization, self.organization)
        self.assertEqual(payment.account, self.account)
        self.assertEqual(payment.transaction_type, 'EXPENSE')
        self.assertEqual(payment.amount, 50)
        self.assertEqual(payment.status, 'POSTED')
        self.assertEqual(payment.created_by, self.user)
        self.assertTrue(payment.number.startswith('SALARY-'))
        payment.full_clean()
        self.assertTrue(
            AuditLog.objects.filter(
                action='POST', model_name='SalaryPayment', object_id=salary.pk
            ).exists()
        )
        notification = Notification.objects.get(notification_type='SALARY')
        self.assertEqual(notification.title, 'Зарплата выплачена')
        self.assertIn(str(salary.employee), notification.message)
        self.assertIn(str(salary.amount), notification.message)

        response = self.pay_salary(salary)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Зарплата уже выплачена')
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 150)
        self.assertEqual(CashTransaction.objects.count(), 1)

    def test_salary_payment_requires_cash_account(self):
        salary = self.make_salary(50, with_account=False)
        response = self.pay_salary(salary)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Выберите кассу')
        salary.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(salary.status, 'DRAFT')
        self.assertEqual(self.account.balance, 200)
        self.assertFalse(CashTransaction.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_salary_payment_insufficient_balance_changes_nothing(self):
        salary = self.make_salary(250)
        response = self.pay_salary(salary)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Недостаточно денег в кассе')
        salary.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(salary.status, 'DRAFT')
        self.assertEqual(self.account.balance, 200)
        self.assertFalse(CashTransaction.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_notify_roles_creates_notifications_for_active_matching_users(self):
        matching_user = get_user_model().objects.create_user(
            username='director', role='DIRECTOR'
        )
        get_user_model().objects.create_user(
            username='inactive', role='ADMIN', is_active=False
        )
        get_user_model().objects.create_user(username='employee', role='EMPLOYEE')

        notify_roles(
            ['ADMIN', 'DIRECTOR'],
            'Payment received',
            'A customer paid an invoice',
            'SALE',
        )

        self.assertEqual(Notification.objects.count(), 2)
        self.assertSetEqual(
            set(Notification.objects.values_list('user_id', flat=True)),
            {self.user.pk, matching_user.pk},
        )
        notification = Notification.objects.get(user=matching_user)
        self.assertEqual(notification.notification_type, 'SALE')
        self.assertEqual(notification.title, 'Payment received')
        self.assertFalse(notification.is_read)

    def test_notification_views_only_access_current_user_notifications(self):
        other_user = get_user_model().objects.create_user(username='other')
        older = Notification.objects.create(
            user=self.user, title='Older', message='First', is_read=True
        )
        newer = Notification.objects.create(
            user=self.user, title='Newer', message='Second'
        )
        other = Notification.objects.create(
            user=other_user, title='Private', message='Other user'
        )

        request = self.factory.get('/')
        force_authenticate(request, user=self.user)
        response = NotificationListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(
            [item['id'] for item in response.data['results']],
            [newer.pk, older.pk],
        )

        request = self.factory.get('/')
        force_authenticate(request, user=self.user)
        response = UnreadNotificationListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], newer.pk)

        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = ReadNotificationView.as_view()(request, pk=other.pk)
        self.assertEqual(response.status_code, 404)
        other.refresh_from_db()
        self.assertFalse(other.is_read)

        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = ReadNotificationView.as_view()(request, pk=newer.pk)
        self.assertEqual(response.status_code, 200)
        newer.refresh_from_db()
        self.assertTrue(newer.is_read)

        extra = Notification.objects.create(
            user=self.user, title='Extra', message='Unread'
        )
        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = ReadAllNotificationsView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        extra.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(extra.is_read)
        self.assertFalse(other.is_read)

    def test_notification_urls_resolve_to_expected_views(self):
        routes = {
            '/api/notifications/': NotificationListView,
            '/api/notifications/unread/': UnreadNotificationListView,
            '/api/notifications/1/read/': ReadNotificationView,
            '/api/notifications/read-all/': ReadAllNotificationsView,
        }
        for path, view_class in routes.items():
            with self.subTest(path=path):
                self.assertIs(resolve(path).func.view_class, view_class)
