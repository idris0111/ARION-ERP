from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import resolve
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from .models import (
    AuditLog, CashAccount, CashTransaction, Counterparty, Debt, Employee, Notification,
    Inventory, InventoryItem, MoneyTransfer, Organization, Product, Purchase, PurchaseItem, PurchaseReturn,
    PurchaseReturnItem, Sale, SaleItem, SaleReturn, SaleReturnItem, SalaryPayment,
    Stock, StockMovement, StockTransfer, StockTransferItem, Warehouse, WriteOff,
    WriteOffItem,
)
from .serializers import (
    PurchaseItemSerializer, PurchaseReturnItemSerializer, PurchaseSerializer,
    SaleItemSerializer, SaleReturnItemSerializer, SaleSerializer,
    StockTransferItemSerializer, StockTransferSerializer, WriteOffItemSerializer,
)
from .views import (
    CheckLowStockView, NotificationListView, PayDebtView, PaySalaryView,
    InventoryDetailView, MoneyTransferListCreateView, PostInventoryView,
    PostPurchaseReturnView, PostPurchaseView, PostSaleReturnView, PostSaleView,
    PostStockTransferView, PostWriteOffView, PurchaseDetailView,
    PurchaseItemDetailView, PurchaseReturnDetailView, ReadAllNotificationsView,
    ReadNotificationView, SaleDetailView, SaleReturnDetailView, StockDetailView,
    StockListView, StockTransferDetailView, UnpostInventoryView,
    UnpostPurchaseView, UnpostSaleView, UnpostStockTransferView,
    UnpostWriteOffView, UnreadNotificationListView, WriteOffDetailView, notify_roles,
)
from .reports import ProfitReportView


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
            '/api/notifications/check-low-stock/': CheckLowStockView,
        }
        for path, view_class in routes.items():
            with self.subTest(path=path):
                self.assertIs(resolve(path).func.view_class, view_class)

    def test_check_low_stock_notifies_roles_at_or_below_minimum(self):
        self.product.min_stock = 10
        self.product.save()

        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = CheckLowStockView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['low_stock_count'], 1)
        notification = Notification.objects.get(
            user=self.user,
            notification_type='STOCK',
        )
        self.assertEqual(notification.title, 'Заканчивается товар')
        self.assertIn(str(self.product), notification.message)
        self.assertIn(str(self.stock.quantity), notification.message)
        self.assertIn(str(self.warehouse), notification.message)

        Notification.objects.all().delete()
        self.stock.quantity = 11
        self.stock.save()
        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = CheckLowStockView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['low_stock_count'], 0)
        self.assertFalse(Notification.objects.exists())

    def test_document_and_item_serializer_validation(self):
        purchase = self.make_document('purchase', 0)
        sale = self.make_document('sale', 0)
        purchase_item = purchase.items.get()
        sale_item = sale.items.get()

        for serializer_class, instance in [
            (PurchaseItemSerializer, purchase_item),
            (SaleItemSerializer, sale_item),
        ]:
            for field, value, message in [
                ('quantity', 0, 'Количество должно быть больше 0'),
                ('price', -1, 'Цена не может быть отрицательной'),
            ]:
                with self.subTest(serializer=serializer_class.__name__, field=field):
                    serializer = serializer_class(
                        instance, data={field: value}, partial=True
                    )
                    self.assertFalse(serializer.is_valid())
                    self.assertEqual(str(serializer.errors[field][0]), message)

        purchase.status = 'POSTED'
        purchase.save()
        serializer = PurchaseItemSerializer(
            purchase_item, data={'quantity': 3}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('Нельзя менять проведённую закупку', str(serializer.errors))

        sale.status = 'POSTED'
        sale.save()
        serializer = SaleItemSerializer(sale_item, data={'quantity': 3}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Нельзя менять проведённую продажу', str(serializer.errors))

        second_warehouse = Warehouse.objects.create(
            organization=self.organization, name='Second warehouse'
        )
        transfer = StockTransfer.objects.create(
            organization=self.organization,
            from_warehouse=self.warehouse,
            to_warehouse=second_warehouse,
            number='TRANSFER-VALIDATION',
            date=timezone.now(),
            created_by=self.user,
        )
        transfer_item = StockTransferItem.objects.create(
            transfer=transfer, product=self.product, quantity=1
        )
        serializer = StockTransferItemSerializer(
            transfer_item, data={'quantity': 0}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            str(serializer.errors['quantity'][0]),
            'Количество должно быть больше 0',
        )
        transfer.status = 'POSTED'
        transfer.save()
        serializer = StockTransferItemSerializer(
            transfer_item, data={'quantity': 2}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('Нельзя менять проведённое перемещение', str(serializer.errors))

        write_off = WriteOff.objects.create(
            organization=self.organization,
            warehouse=self.warehouse,
            number='WRITE-OFF-VALIDATION',
            date=timezone.now(),
            reason='OTHER',
            created_by=self.user,
        )
        write_off_item = WriteOffItem.objects.create(
            write_off=write_off, product=self.product, quantity=1
        )
        serializer = WriteOffItemSerializer(
            write_off_item, data={'quantity': 0}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            str(serializer.errors['quantity'][0]),
            'Количество должно быть больше 0',
        )
        write_off.status = 'POSTED'
        write_off.save()
        serializer = WriteOffItemSerializer(
            write_off_item, data={'quantity': 2}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('Нельзя менять проведённое списание', str(serializer.errors))

        sale_return = SaleReturn.objects.create(
            number='SALE-RETURN-VALIDATION',
            sale=sale,
            warehouse=self.warehouse,
        )
        sale_return_item = SaleReturnItem.objects.create(
            sale_return=sale_return,
            product=self.product,
            quantity=1,
            price=1,
        )
        purchase_return = PurchaseReturn.objects.create(
            number='PURCHASE-RETURN-VALIDATION',
            purchase=purchase,
            warehouse=self.warehouse,
        )
        purchase_return_item = PurchaseReturnItem.objects.create(
            purchase_return=purchase_return,
            product=self.product,
            quantity=1,
            price=1,
        )
        for serializer_class, instance in [
            (SaleReturnItemSerializer, sale_return_item),
            (PurchaseReturnItemSerializer, purchase_return_item),
        ]:
            for field, value, message in [
                ('quantity', 0, 'Количество должно быть больше 0'),
                ('price', -1, 'Цена не может быть отрицательной'),
            ]:
                with self.subTest(serializer=serializer_class.__name__, field=field):
                    serializer = serializer_class(
                        instance, data={field: value}, partial=True
                    )
                    self.assertFalse(serializer.is_valid())
                    self.assertEqual(str(serializer.errors[field][0]), message)

        for serializer_class in (PurchaseSerializer, SaleSerializer):
            serializer = serializer_class(data={'paid_amount': -1}, partial=True)
            self.assertFalse(serializer.is_valid())
            self.assertEqual(
                str(serializer.errors['paid_amount'][0]),
                'Оплата не может быть отрицательной',
            )

        serializer = StockTransferSerializer(
            data={
                'from_warehouse': self.warehouse.pk,
                'to_warehouse': self.warehouse.pk,
            },
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('Склады должны быть разными', str(serializer.errors))

    def test_posted_document_detail_views_reject_changes_and_deletion(self):
        purchase = self.make_document('purchase', 0)
        sale = self.make_document('sale', 0)
        second_warehouse = Warehouse.objects.create(
            organization=self.organization, name='Second warehouse'
        )
        documents = [
            (
                PurchaseDetailView,
                purchase,
            ),
            (
                SaleDetailView,
                sale,
            ),
            (
                StockTransferDetailView,
                StockTransfer.objects.create(
                    organization=self.organization,
                    from_warehouse=self.warehouse,
                    to_warehouse=second_warehouse,
                    number='TRANSFER-PROTECT',
                    date=timezone.now(),
                    status='POSTED',
                    created_by=self.user,
                ),
            ),
            (
                WriteOffDetailView,
                WriteOff.objects.create(
                    organization=self.organization,
                    warehouse=self.warehouse,
                    number='WRITE-OFF-PROTECT',
                    date=timezone.now(),
                    reason='OTHER',
                    status='POSTED',
                    created_by=self.user,
                ),
            ),
            (
                InventoryDetailView,
                Inventory.objects.create(
                    organization=self.organization,
                    warehouse=self.warehouse,
                    number='INVENTORY-PROTECT',
                    date=timezone.now(),
                    status='POSTED',
                    created_by=self.user,
                ),
            ),
        ]
        purchase.status = 'POSTED'
        purchase.save()
        sale.status = 'POSTED'
        sale.save()
        documents.extend([
            (
                SaleReturnDetailView,
                SaleReturn.objects.create(
                    number='SALE-RETURN-PROTECT',
                    sale=sale,
                    warehouse=self.warehouse,
                    status='POSTED',
                ),
            ),
            (
                PurchaseReturnDetailView,
                PurchaseReturn.objects.create(
                    number='PURCHASE-RETURN-PROTECT',
                    purchase=purchase,
                    warehouse=self.warehouse,
                    status='POSTED',
                ),
            ),
        ])

        for view_class, document in documents:
            with self.subTest(view=view_class.__name__, method='patch'):
                request = self.factory.patch('/', {'comment': 'changed'}, format='json')
                force_authenticate(request, user=self.user)
                response = view_class.as_view()(request, pk=document.pk)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data['error'],
                    'Нельзя изменять проведённый документ',
                )
                document.refresh_from_db()
                self.assertEqual(document.comment, '')

            with self.subTest(view=view_class.__name__, method='delete'):
                request = self.factory.delete('/')
                force_authenticate(request, user=self.user)
                response = view_class.as_view()(request, pk=document.pk)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data['error'],
                    'Нельзя удалить проведённый документ',
                )
                self.assertTrue(type(document).objects.filter(pk=document.pk).exists())

    def test_draft_document_can_be_updated_and_deleted(self):
        purchase = self.make_document('purchase', 0)
        request = self.factory.patch('/', {'comment': 'changed'}, format='json')
        force_authenticate(request, user=self.user)
        response = PurchaseDetailView.as_view()(request, pk=purchase.pk)
        self.assertEqual(response.status_code, 200, response.data)
        purchase.refresh_from_db()
        self.assertEqual(purchase.comment, 'changed')

        request = self.factory.delete('/')
        force_authenticate(request, user=self.user)
        response = PurchaseDetailView.as_view()(request, pk=purchase.pk)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Purchase.objects.filter(pk=purchase.pk).exists())

    def test_stock_api_is_read_only(self):
        for request, view, kwargs in [
            (self.factory.post('/', {}), StockListView, {}),
            (self.factory.put('/', {}), StockDetailView, {'pk': self.stock.pk}),
            (self.factory.delete('/'), StockDetailView, {'pk': self.stock.pk}),
        ]:
            force_authenticate(request, user=self.user)
            response = view.as_view()(request, **kwargs)
            self.assertEqual(response.status_code, 405)

    def test_sale_cannot_exceed_stock(self):
        sale = Sale.objects.create(
            organization=self.organization, customer=self.counterparty,
            warehouse=self.warehouse, number='SALE-TOO-MUCH', date=timezone.now(),
            created_by=self.user,
        )
        SaleItem.objects.create(sale=sale, product=self.product, quantity=11, price=10)
        response = self.request_action('sale', 'post', sale)
        self.assertEqual(response.status_code, 400)
        sale.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(sale.status, 'DRAFT')
        self.assertEqual(self.stock.quantity, 10)
        self.assertFalse(StockMovement.objects.exists())

    def test_stock_transfer_post_and_unpost(self):
        destination = Warehouse.objects.create(
            organization=self.organization, name='Destination'
        )
        transfer = StockTransfer.objects.create(
            organization=self.organization, from_warehouse=self.warehouse,
            to_warehouse=destination, number='TRANSFER-1', date=timezone.now(),
            created_by=self.user,
        )
        StockTransferItem.objects.create(
            transfer=transfer, product=self.product, quantity=3
        )
        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = PostStockTransferView.as_view()(request, pk=transfer.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.stock.refresh_from_db()
        destination_stock = Stock.objects.get(warehouse=destination, product=self.product)
        self.assertEqual(self.stock.quantity, 7)
        self.assertEqual(destination_stock.quantity, 3)
        self.assertSetEqual(
            set(StockMovement.objects.values_list('movement_type', flat=True)),
            {'TRANSFER_OUT', 'TRANSFER_IN'},
        )

        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = UnpostStockTransferView.as_view()(request, pk=transfer.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.stock.refresh_from_db()
        destination_stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
        self.assertEqual(destination_stock.quantity, 0)
        self.assertFalse(StockMovement.objects.exists())

    def test_write_off_post_and_unpost(self):
        write_off = WriteOff.objects.create(
            organization=self.organization, warehouse=self.warehouse,
            number='WRITE-OFF-1', date=timezone.now(), reason='OTHER',
            created_by=self.user,
        )
        WriteOffItem.objects.create(
            write_off=write_off, product=self.product, quantity=3
        )
        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = PostWriteOffView.as_view()(request, pk=write_off.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 7)
        self.assertTrue(StockMovement.objects.filter(movement_type='WRITE_OFF').exists())

        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = UnpostWriteOffView.as_view()(request, pk=write_off.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
        self.assertFalse(StockMovement.objects.exists())

    def test_inventory_post_and_unpost(self):
        inventory = Inventory.objects.create(
            organization=self.organization, warehouse=self.warehouse,
            number='INVENTORY-1', date=timezone.now(), created_by=self.user,
        )
        item = InventoryItem.objects.create(
            inventory=inventory, product=self.product, actual_quantity=4
        )
        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = PostInventoryView.as_view()(request, pk=inventory.pk)
        self.assertEqual(response.status_code, 200, response.data)
        item.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(item.system_quantity, 10)
        self.assertEqual(item.difference, -6)
        self.assertEqual(self.stock.quantity, 4)

        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = UnpostInventoryView.as_view()(request, pk=inventory.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)

    def test_returns_change_stock_and_create_valid_movements(self):
        sale = self.make_document('sale', 0)
        purchase = self.make_document('purchase', 0)
        sale.status = 'POSTED'
        sale.save()
        purchase.status = 'POSTED'
        purchase.save()
        sale_return = SaleReturn.objects.create(
            number='SALE-RETURN-1', sale=sale, warehouse=self.warehouse
        )
        SaleReturnItem.objects.create(
            sale_return=sale_return, product=self.product, quantity=1, price=50
        )
        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = PostSaleReturnView.as_view()(request, pk=sale_return.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 11)

        purchase_return = PurchaseReturn.objects.create(
            number='PURCHASE-RETURN-1', purchase=purchase, warehouse=self.warehouse
        )
        PurchaseReturnItem.objects.create(
            purchase_return=purchase_return, product=self.product, quantity=2, price=50
        )
        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = PostPurchaseReturnView.as_view()(request, pk=purchase_return.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 9)
        for movement in StockMovement.objects.all():
            movement.full_clean()

    def test_money_transfer_and_insufficient_balance(self):
        destination = CashAccount.objects.create(
            organization=self.organization, name='Bank', account_type='BANK', balance=20
        )
        data = {
            'organization': self.organization.pk,
            'from_account': self.account.pk,
            'to_account': destination.pk,
            'amount': '50.00',
            'date': timezone.now().isoformat(),
        }
        request = self.factory.post('/', data, format='json')
        force_authenticate(request, user=self.user)
        response = MoneyTransferListCreateView.as_view()(request)
        self.assertEqual(response.status_code, 201, response.data)
        self.account.refresh_from_db()
        destination.refresh_from_db()
        self.assertEqual(self.account.balance, 150)
        self.assertEqual(destination.balance, 70)
        self.assertEqual(MoneyTransfer.objects.count(), 1)

        data['amount'] = '999.00'
        request = self.factory.post('/', data, format='json')
        force_authenticate(request, user=self.user)
        response = MoneyTransferListCreateView.as_view()(request)
        self.assertEqual(response.status_code, 400)
        self.account.refresh_from_db()
        destination.refresh_from_db()
        self.assertEqual(self.account.balance, 150)
        self.assertEqual(destination.balance, 70)
        self.assertEqual(MoneyTransfer.objects.count(), 1)

    def test_profit_report_uses_sale_movements_cost(self):
        sale = Sale.objects.create(
            organization=self.organization, customer=self.counterparty,
            warehouse=self.warehouse, number='SALE-REPORT', date=timezone.now(),
            status='POSTED', total_amount=100, created_by=self.user,
        )
        StockMovement.objects.create(
            warehouse=self.warehouse, product=self.product, movement_type='OUT',
            quantity=2, unit_cost=30, document_type='SALE', document_id=sale.pk,
        )
        request = self.factory.get('/')
        force_authenticate(request, user=self.user)
        response = ProfitReportView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['revenue'], Decimal('100'))
        self.assertEqual(response.data['cost'], Decimal('60'))
        self.assertEqual(response.data['profit'], Decimal('40'))

    def test_failed_purchase_unpost_does_not_partially_change_stock(self):
        purchase = self.make_document('purchase', 0)
        second_product = Product.objects.create(
            organization=self.organization, name='Second', sku='P2'
        )
        PurchaseItem.objects.create(
            purchase=purchase, product=second_product, quantity=2, price=10
        )
        second_stock = Stock.objects.create(
            warehouse=self.warehouse, product=second_product, quantity=1
        )
        purchase.status = 'POSTED'
        purchase.save()

        request = self.factory.post('/')
        force_authenticate(request, user=self.user)
        response = UnpostPurchaseView.as_view()(request, pk=purchase.pk)
        self.assertEqual(response.status_code, 400)
        self.stock.refresh_from_db()
        second_stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
        self.assertEqual(second_stock.quantity, 1)

    def test_posted_item_cannot_be_deleted(self):
        purchase = self.make_document('purchase', 0)
        item = purchase.items.get()
        purchase.status = 'POSTED'
        purchase.save()
        request = self.factory.delete('/')
        force_authenticate(request, user=self.user)
        response = PurchaseItemDetailView.as_view()(request, pk=item.pk)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(PurchaseItem.objects.filter(pk=item.pk).exists())

    @override_settings(ALLOWED_HOSTS=['testserver'])
    def test_swagger_schema_builds(self):
        response = APIClient().get('/swagger/?format=openapi')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/openapi+json', response['Content-Type'])

    def test_csv_and_excel_exports(self):
        client = APIClient()
        client.force_authenticate(self.user)
        for path, content_type in [
            ('/api/export/employees/', 'text/csv'),
            ('/api/export/cash-transactions/', 'text/csv'),
            (
                '/api/export/excel/employees/',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ),
            (
                '/api/export/excel/cash-transactions/',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ),
        ]:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], content_type)
                self.assertTrue(response.content)
