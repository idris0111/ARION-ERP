from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.generics import (ListCreateAPIView,RetrieveUpdateDestroyAPIView,RetrieveAPIView,ListAPIView,)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from accounts.models import User

from .models import (SaleReturn,SaleReturnItem,PurchaseReturn,PurchaseReturnItem,Organization,Branch,OrganizationMember,Department,Position,Employee,SalaryPayment,Counterparty,ContactPerson,Category,Unit,Brand,
    Product,PriceType,ProductPrice,Warehouse,Stock,StockMovement,Purchase,PurchaseItem,Sale,SaleItem,StockTransfer,StockTransferItem,
    WriteOff,WriteOffItem,Inventory,InventoryItem,CashAccount,FinanceCategory,CashTransaction,MoneyTransfer,Debt,AuditLog,Notification,
)
from .serializers import (
    SaleReturnSerializer,SaleReturnItemSerializer,PurchaseReturnSerializer,PurchaseReturnItemSerializer,
    OrganizationSerializer,BranchSerializer,OrganizationMemberSerializer,DepartmentSerializer,PositionSerializer,EmployeeSerializer,SalaryPaymentSerializer,
    CounterpartySerializer,ContactPersonSerializer,CategorySerializer,UnitSerializer,BrandSerializer,ProductSerializer,PriceTypeSerializer,ProductPriceSerializer,WarehouseSerializer,
    StockSerializer,StockMovementSerializer,PurchaseSerializer,PurchaseItemSerializer,SaleSerializer,SaleItemSerializer,StockTransferSerializer,StockTransferItemSerializer,
    WriteOffSerializer,WriteOffItemSerializer,InventorySerializer,InventoryItemSerializer,CashAccountSerializer,FinanceCategorySerializer,CashTransactionSerializer,MoneyTransferSerializer,DebtSerializer,AuditLogSerializer,NotificationSerializer,
)

from .permissions import (IsAdminOrDirector,IsAccountant,IsWarehouseWorker,IsSalesWorker,IsPurchaseWorker,IsHRWorker,IsAuditor,)


# =========================================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def create_audit(request, action, obj, description):
    AuditLog.objects.create(
        user=request.user,
        action=action,
        model_name=obj.__class__.__name__,
        object_id=obj.id,
        description=description,
        ip_address=request.META.get('REMOTE_ADDR'),
    )


def notify_roles(roles, title, message, notification_type='INFO'):
    users = User.objects.filter(role__in=roles, is_active=True)
    for user in users:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
        )


def calculate_payment_status(total_amount, paid_amount):
    if paid_amount <= 0:
        return 'UNPAID'

    if paid_amount < total_amount:
        return 'PARTIAL'

    return 'PAID'


def process_sale_payment(sale):
    if sale.paid_amount > sale.total_amount:
        raise ValidationError('Оплата больше суммы продажи')

    if sale.paid_amount > 0:
        if not sale.cash_account_id:
            raise ValidationError('Выберите кассу для оплаты')
        account = CashAccount.objects.select_for_update().get(pk=sale.cash_account_id)
        account.balance += sale.paid_amount
        account.save()
        CashTransaction.objects.create(
            organization=sale.organization,
            account=account,
            counterparty=sale.customer,
            number=f'SALE-{uuid4().hex}',
            date=sale.date,
            created_by=sale.created_by,
            transaction_type='INCOME',
            amount=sale.paid_amount,
            status='POSTED',
            sale=sale,
        )

    remaining = sale.total_amount - sale.paid_amount
    if remaining > 0:
        Debt.objects.create(
            organization=sale.organization,
            counterparty=sale.customer,
            debt_type='CUSTOMER',
            amount=remaining,
            paid_amount=0,
            status='OPEN',
            sale=sale,
        )


def process_purchase_payment(purchase):
    if purchase.paid_amount > purchase.total_amount:
        raise ValidationError('Оплата больше суммы закупки')

    if purchase.paid_amount > 0:
        if not purchase.cash_account_id:
            raise ValidationError('Выберите кассу для оплаты')
        account = CashAccount.objects.select_for_update().get(pk=purchase.cash_account_id)
        if account.balance < purchase.paid_amount:
            raise ValidationError('Недостаточно денег в кассе')
        account.balance -= purchase.paid_amount
        account.save()
        CashTransaction.objects.create(
            organization=purchase.organization,
            account=account,
            counterparty=purchase.supplier,
            number=f'PURCHASE-{uuid4().hex}',
            date=purchase.date,
            created_by=purchase.created_by,
            transaction_type='EXPENSE',
            amount=purchase.paid_amount,
            status='POSTED',
            purchase=purchase,
        )

    remaining = purchase.total_amount - purchase.paid_amount
    if remaining > 0:
        Debt.objects.create(
            organization=purchase.organization,
            counterparty=purchase.supplier,
            debt_type='SUPPLIER',
            amount=remaining,
            paid_amount=0,
            status='OPEN',
            purchase=purchase,
        )


# =========================================================
# ORGANIZATION
# =========================================================

class OrganizationListCreateView(ListCreateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAdminOrDirector]


class OrganizationDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAdminOrDirector]


class BranchListCreateView(ListCreateAPIView):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAdminOrDirector]


class BranchDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAdminOrDirector]


class OrganizationMemberListCreateView(ListCreateAPIView):
    queryset = OrganizationMember.objects.all()
    serializer_class = OrganizationMemberSerializer
    permission_classes = [IsAdminOrDirector]


class OrganizationMemberDetailView(RetrieveUpdateDestroyAPIView):
    queryset = OrganizationMember.objects.all()
    serializer_class = OrganizationMemberSerializer
    permission_classes = [IsAdminOrDirector]


# =========================================================
# EMPLOYEES
# =========================================================

class DepartmentListCreateView(ListCreateAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsHRWorker]


class DepartmentDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsHRWorker]


class PositionListCreateView(ListCreateAPIView):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [IsHRWorker]


class PositionDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [IsHRWorker]


class EmployeeListCreateView(ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRWorker]
    filterset_fields = ['organization', 'branch', 'department', 'position', 'is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']

class EmployeeDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRWorker]


class SalaryPaymentListCreateView(ListCreateAPIView):
    queryset = SalaryPayment.objects.all()
    serializer_class = SalaryPaymentSerializer
    permission_classes = [IsHRWorker]


class SalaryPaymentDetailView(RetrieveUpdateDestroyAPIView):
    queryset = SalaryPayment.objects.all()
    serializer_class = SalaryPaymentSerializer
    permission_classes = [IsHRWorker]


class PaySalaryView(APIView):
    permission_classes = [IsHRWorker]

    def post(self, request, pk):
        salary = get_object_or_404(SalaryPayment, pk=pk)
        if salary.status == 'PAID':
            return Response({'error': 'Зарплата уже выплачена'}, status=400)
        if not salary.cash_account_id:
            return Response({'error': 'Выберите кассу'}, status=400)

        with transaction.atomic():
            salary = SalaryPayment.objects.select_for_update().get(pk=salary.pk)
            if salary.status == 'PAID':
                return Response({'error': 'Зарплата уже выплачена'}, status=400)

            account = CashAccount.objects.select_for_update().get(
                pk=salary.cash_account_id
            )
            if account.balance < salary.amount:
                return Response({'error': 'Недостаточно денег в кассе'}, status=400)

            account.balance -= salary.amount
            account.save()
            CashTransaction.objects.create(
                organization=salary.employee.organization,
                account=account,
                number=f'SALARY-{uuid4().hex}',
                date=timezone.now(),
                created_by=request.user,
                transaction_type='EXPENSE',
                amount=salary.amount,
                status='POSTED',
            )
            salary.status = 'PAID'
            salary.save()
            create_audit(
                request,
                'POST',
                salary,
                f'Выплачена зарплата {salary.employee}',
            )

        return Response({
            'message': 'Зарплата выплачена',
            'amount': salary.amount,
            'cash_balance': account.balance,
        })


# =========================================================
# COUNTERPARTIES
# =========================================================

class CounterpartyListCreateView(ListCreateAPIView):
    queryset = Counterparty.objects.all()
    serializer_class = CounterpartySerializer
    permission_classes = [IsAuthenticated]


class CounterpartyDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Counterparty.objects.all()
    serializer_class = CounterpartySerializer
    permission_classes = [IsAuthenticated]


class ContactPersonListCreateView(ListCreateAPIView):
    queryset = ContactPerson.objects.all()
    serializer_class = ContactPersonSerializer
    permission_classes = [IsAuthenticated]


class ContactPersonDetailView(RetrieveUpdateDestroyAPIView):
    queryset = ContactPerson.objects.all()
    serializer_class = ContactPersonSerializer
    permission_classes = [IsAuthenticated]


# =========================================================
# CATALOG
# =========================================================

class CategoryListCreateView(ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class CategoryDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class UnitListCreateView(ListCreateAPIView):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]


class UnitDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]


class BrandListCreateView(ListCreateAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticated]


class BrandDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticated]


class ProductListCreateView(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]


class ProductDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]


class PriceTypeListCreateView(ListCreateAPIView):
    queryset = PriceType.objects.all()
    serializer_class = PriceTypeSerializer
    permission_classes = [IsAuthenticated]


class PriceTypeDetailView(RetrieveUpdateDestroyAPIView):
    queryset = PriceType.objects.all()
    serializer_class = PriceTypeSerializer
    permission_classes = [IsAuthenticated]


class ProductPriceListCreateView(ListCreateAPIView):
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer
    permission_classes = [IsAuthenticated]


class ProductPriceDetailView(RetrieveUpdateDestroyAPIView):
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer
    permission_classes = [IsAuthenticated]


# =========================================================
# WAREHOUSE
# =========================================================

class WarehouseListCreateView(ListCreateAPIView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsWarehouseWorker]


class WarehouseDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsWarehouseWorker]

class StockListView(ListAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['warehouse', 'product']
    search_fields = ['product__name', 'product__sku', 'product__barcode']
    ordering_fields = ['quantity', 'average_cost']


class StockDetailView(RetrieveAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]


class StockMovementListView(ListAPIView):
    queryset = StockMovement.objects.all().order_by('-created_at')
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]


# =========================================================
# PURCHASE
# =========================================================
class PurchaseListCreateView(ListCreateAPIView):
    queryset = Purchase.objects.all().order_by('-created_at')
    serializer_class = PurchaseSerializer
    permission_classes = [IsPurchaseWorker]
    filterset_fields = ['organization', 'warehouse', 'supplier', 'status', 'payment_status']
    search_fields = ['number']
    ordering_fields = ['created_at', 'total_amount']

class PurchaseDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [IsPurchaseWorker]


class PurchaseItemListCreateView(ListCreateAPIView):
    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer
    permission_classes = [IsPurchaseWorker]


class PurchaseItemDetailView(RetrieveUpdateDestroyAPIView):
    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer
    permission_classes = [IsPurchaseWorker]


class PostPurchaseView(APIView):
    permission_classes = [IsPurchaseWorker]

    def post(self, request, pk):
        purchase = get_object_or_404(Purchase, pk=pk)

        if purchase.status == 'POSTED':
            return Response(
                {'error': 'Закупка уже проведена'},
                status=400
            )

        items = PurchaseItem.objects.filter(purchase=purchase)

        if not items.exists():
            return Response(
                {'error': 'В закупке нет товаров'},
                status=400
            )

        with transaction.atomic():
            total_amount = Decimal('0')

            for item in items:
                item_total = (
                    item.quantity * item.price
                ) - item.discount

                item.total = item_total
                item.save()

                total_amount += item_total

                stock, created = Stock.objects.get_or_create(
                    warehouse=purchase.warehouse,
                    product=item.product,
                    defaults={
                        'quantity': 0,
                        'average_cost': 0,
                    }
                )

                old_quantity = stock.quantity
                old_cost = stock.average_cost

                new_quantity = old_quantity + item.quantity

                if new_quantity > 0:
                    stock.average_cost = (
                        (old_quantity * old_cost)
                        +
                        (item.quantity * item.price)
                    ) / new_quantity

                stock.quantity = new_quantity
                stock.save()

                StockMovement.objects.create(
                    warehouse=purchase.warehouse,
                    product=item.product,
                    movement_type='IN',
                    quantity=item.quantity,
                    unit_cost=item.price,
                    document_type='PURCHASE',
                    document_id=purchase.id,
                    comment=f'Закупка №{purchase.number}',
                )

            purchase.total_amount = total_amount

            purchase.payment_status = calculate_payment_status(
                purchase.total_amount,
                purchase.paid_amount
            )

            process_purchase_payment(purchase)
            purchase.status = 'POSTED'
            purchase.save()

            create_audit(
                request,
                'POST',
                purchase,
                f'Проведена закупка №{purchase.number}'
            )

        return Response({
            'message': 'Закупка успешно проведена',
            'purchase_id': purchase.id,
            'total_amount': purchase.total_amount,
        })


class UnpostPurchaseView(APIView):
    permission_classes = [IsPurchaseWorker]

    def post(self, request, pk):
        purchase = get_object_or_404(Purchase, pk=pk)

        if purchase.status != 'POSTED':
            return Response(
                {'error': 'Закупка не проведена'},
                status=400
            )

        items = PurchaseItem.objects.filter(purchase=purchase)

        with transaction.atomic():
            for item in items:
                stock = Stock.objects.select_for_update().filter(
                    warehouse=purchase.warehouse,
                    product=item.product
                ).first()

                if not stock:
                    return Response(
                        {'error': f'Нет остатка товара {item.product}'},
                        status=400
                    )

                if stock.quantity < item.quantity:
                    return Response(
                        {
                            'error':
                            f'Нельзя отменить закупку. '
                            f'Товара {item.product} уже недостаточно'
                        },
                        status=400
                    )

                stock.quantity -= item.quantity
                stock.save()

            StockMovement.objects.filter(
                document_type='PURCHASE',
                document_id=purchase.id
            ).delete()

            cash_transaction = CashTransaction.objects.filter(
                purchase=purchase, status='POSTED'
            ).first()
            if cash_transaction:
                account = CashAccount.objects.select_for_update().get(
                    pk=cash_transaction.account_id
                )
                account.balance += cash_transaction.amount
                account.save()
                cash_transaction.delete()

            Debt.objects.filter(purchase=purchase).delete()

            purchase.status = 'DRAFT'
            purchase.save()

            create_audit(
                request,
                'CANCEL',
                purchase,
                f'Отменено проведение закупки №{purchase.number}'
            )

        return Response({
            'message': 'Проведение закупки отменено'
        })


# =========================================================
# SALE
# =========================================================

class SaleListCreateView(ListCreateAPIView):
    queryset = Sale.objects.all().order_by('-created_at')
    serializer_class = SaleSerializer
    permission_classes = [IsSalesWorker]
    filterset_fields = ['organization', 'warehouse', 'customer', 'status', 'payment_status']
    search_fields = ['number']
    ordering_fields = ['created_at', 'total_amount']

class SaleDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsSalesWorker]


class SaleItemListCreateView(ListCreateAPIView):
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    permission_classes = [IsSalesWorker]


class SaleItemDetailView(RetrieveUpdateDestroyAPIView):
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    permission_classes = [IsSalesWorker]


class PostSaleView(APIView):
    permission_classes = [IsSalesWorker]

    def post(self, request, pk):
        sale = get_object_or_404(Sale, pk=pk)

        if sale.status == 'POSTED':
            return Response(
                {'error': 'Продажа уже проведена'},
                status=400
            )

        items = SaleItem.objects.filter(sale=sale)

        if not items.exists():
            return Response(
                {'error': 'В продаже нет товаров'},
                status=400
            )

        with transaction.atomic():
            stock_list = []

            for item in items:
                stock = Stock.objects.select_for_update().filter(
                    warehouse=sale.warehouse,
                    product=item.product
                ).first()

                if not stock:
                    return Response(
                        {
                            'error':
                            f'Товара {item.product} нет на складе'
                        },
                        status=400
                    )

                if stock.quantity < item.quantity:
                    return Response(
                        {
                            'error':
                            f'Недостаточно товара {item.product}. '
                            f'Остаток: {stock.quantity}'
                        },
                        status=400
                    )

                stock_list.append((item, stock))

            total_amount = Decimal('0')

            for item, stock in stock_list:
                item_total = (
                    item.quantity * item.price
                ) - item.discount

                item.total = item_total
                item.save()

                total_amount += item_total

                stock.quantity -= item.quantity
                stock.save()

                StockMovement.objects.create(
                    warehouse=sale.warehouse,
                    product=item.product,
                    movement_type='OUT',
                    quantity=item.quantity,
                    unit_cost=stock.average_cost,
                    document_type='SALE',
                    document_id=sale.id,
                    comment=f'Продажа №{sale.number}',
                )

            total_amount -= sale.discount

            if total_amount < 0:
                total_amount = Decimal('0')

            sale.total_amount = total_amount

            sale.payment_status = calculate_payment_status(
                sale.total_amount,
                sale.paid_amount
            )

            process_sale_payment(sale)
            sale.status = 'POSTED'
            sale.save()

            create_audit(
                request,
                'POST',
                sale,
                f'Проведена продажа №{sale.number}'
            )

        return Response({
            'message': 'Продажа успешно проведена',
            'sale_id': sale.id,
            'total_amount': sale.total_amount,
        })


class UnpostSaleView(APIView):
    permission_classes = [IsSalesWorker]

    def post(self, request, pk):
        sale = get_object_or_404(Sale, pk=pk)

        if sale.status != 'POSTED':
            return Response(
                {'error': 'Продажа не проведена'},
                status=400
            )

        items = SaleItem.objects.filter(sale=sale)

        with transaction.atomic():
            for item in items:
                stock, created = Stock.objects.get_or_create(
                    warehouse=sale.warehouse,
                    product=item.product,
                    defaults={
                        'quantity': 0,
                        'average_cost': 0,
                    }
                )

                stock.quantity += item.quantity
                stock.save()

            StockMovement.objects.filter(
                document_type='SALE',
                document_id=sale.id
            ).delete()

            cash_transaction = CashTransaction.objects.filter(
                sale=sale, status='POSTED'
            ).first()
            if cash_transaction:
                account = CashAccount.objects.select_for_update().get(
                    pk=cash_transaction.account_id
                )
                if account.balance < cash_transaction.amount:
                    raise ValidationError('Недостаточно денег для отмены продажи')
                account.balance -= cash_transaction.amount
                account.save()
                cash_transaction.delete()

            Debt.objects.filter(sale=sale).delete()

            sale.status = 'DRAFT'
            sale.save()

            create_audit(
                request,
                'CANCEL',
                sale,
                f'Отменено проведение продажи №{sale.number}'
            )

        return Response({
            'message': 'Проведение продажи отменено'
        })


# =========================================================
# STOCK TRANSFER
# =========================================================

class StockTransferListCreateView(ListCreateAPIView):
    queryset = StockTransfer.objects.all().order_by('-created_at')
    serializer_class = StockTransferSerializer
    permission_classes = [IsWarehouseWorker]


class StockTransferDetailView(RetrieveUpdateDestroyAPIView):
    queryset = StockTransfer.objects.all()
    serializer_class = StockTransferSerializer
    permission_classes = [IsWarehouseWorker]


class StockTransferItemListCreateView(ListCreateAPIView):
    queryset = StockTransferItem.objects.all()
    serializer_class = StockTransferItemSerializer
    permission_classes = [IsWarehouseWorker]


class StockTransferItemDetailView(RetrieveUpdateDestroyAPIView):
    queryset = StockTransferItem.objects.all()
    serializer_class = StockTransferItemSerializer
    permission_classes = [IsWarehouseWorker]


class PostStockTransferView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        transfer = get_object_or_404(StockTransfer, pk=pk)

        if transfer.status == 'POSTED':
            return Response(
                {'error': 'Перемещение уже проведено'},
                status=400
            )

        if transfer.from_warehouse == transfer.to_warehouse:
            return Response(
                {'error': 'Склады не могут быть одинаковыми'},
                status=400
            )

        items = StockTransferItem.objects.filter(
            transfer=transfer
        )

        if not items.exists():
            return Response(
                {'error': 'Нет товаров для перемещения'},
                status=400
            )

        with transaction.atomic():
            prepared = []

            for item in items:
                from_stock = Stock.objects.select_for_update().filter(
                    warehouse=transfer.from_warehouse,
                    product=item.product
                ).first()

                if not from_stock:
                    return Response(
                        {
                            'error':
                            f'Товара {item.product} нет на складе'
                        },
                        status=400
                    )

                if from_stock.quantity < item.quantity:
                    return Response(
                        {
                            'error':
                            f'Недостаточно товара {item.product}'
                        },
                        status=400
                    )

                prepared.append((item, from_stock))

            for item, from_stock in prepared:
                from_stock.quantity -= item.quantity
                from_stock.save()

                to_stock, created = Stock.objects.get_or_create(
                    warehouse=transfer.to_warehouse,
                    product=item.product,
                    defaults={
                        'quantity': 0,
                        'average_cost': from_stock.average_cost,
                    }
                )

                if created:
                    to_stock.average_cost = from_stock.average_cost

                to_stock.quantity += item.quantity
                to_stock.save()

                StockMovement.objects.create(
                    warehouse=transfer.from_warehouse,
                    product=item.product,
                    movement_type='TRANSFER_OUT',
                    quantity=item.quantity,
                    unit_cost=from_stock.average_cost,
                    document_type='TRANSFER',
                    document_id=transfer.id,
                    comment=f'Перемещение №{transfer.number}',
                )

                StockMovement.objects.create(
                    warehouse=transfer.to_warehouse,
                    product=item.product,
                    movement_type='TRANSFER_IN',
                    quantity=item.quantity,
                    unit_cost=from_stock.average_cost,
                    document_type='TRANSFER',
                    document_id=transfer.id,
                    comment=f'Перемещение №{transfer.number}',
                )

            transfer.status = 'POSTED'
            transfer.save()

            create_audit(
                request,
                'POST',
                transfer,
                f'Проведено перемещение №{transfer.number}'
            )

        return Response({
            'message': 'Перемещение успешно проведено'
        })


class UnpostStockTransferView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        transfer = get_object_or_404(StockTransfer, pk=pk)

        if transfer.status != 'POSTED':
            return Response(
                {'error': 'Перемещение не проведено'},
                status=400
            )

        items = StockTransferItem.objects.filter(
            transfer=transfer
        )

        with transaction.atomic():
            for item in items:
                to_stock = Stock.objects.select_for_update().filter(
                    warehouse=transfer.to_warehouse,
                    product=item.product
                ).first()

                if not to_stock:
                    return Response(
                        {'error': 'Не найден остаток на складе назначения'},
                        status=400
                    )

                if to_stock.quantity < item.quantity:
                    return Response(
                        {
                            'error':
                            f'Нельзя отменить перемещение товара '
                            f'{item.product}'
                        },
                        status=400
                    )

                to_stock.quantity -= item.quantity
                to_stock.save()

                from_stock, created = Stock.objects.get_or_create(
                    warehouse=transfer.from_warehouse,
                    product=item.product,
                    defaults={
                        'quantity': 0,
                        'average_cost': to_stock.average_cost,
                    }
                )

                from_stock.quantity += item.quantity
                from_stock.save()

            StockMovement.objects.filter(
                document_type='TRANSFER',
                document_id=transfer.id
            ).delete()

            transfer.status = 'DRAFT'
            transfer.save()

            create_audit(
                request,
                'CANCEL',
                transfer,
                f'Отменено перемещение №{transfer.number}'
            )

        return Response({
            'message': 'Проведение перемещения отменено'
        })


# =========================================================
# WRITE OFF
# =========================================================

class WriteOffListCreateView(ListCreateAPIView):
    queryset = WriteOff.objects.all().order_by('-created_at')
    serializer_class = WriteOffSerializer
    permission_classes = [IsWarehouseWorker]


class WriteOffDetailView(RetrieveUpdateDestroyAPIView):
    queryset = WriteOff.objects.all()
    serializer_class = WriteOffSerializer
    permission_classes = [IsWarehouseWorker]


class WriteOffItemListCreateView(ListCreateAPIView):
    queryset = WriteOffItem.objects.all()
    serializer_class = WriteOffItemSerializer
    permission_classes = [IsWarehouseWorker]


class WriteOffItemDetailView(RetrieveUpdateDestroyAPIView):
    queryset = WriteOffItem.objects.all()
    serializer_class = WriteOffItemSerializer
    permission_classes = [IsWarehouseWorker]


class PostWriteOffView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        write_off = get_object_or_404(WriteOff, pk=pk)

        if write_off.status == 'POSTED':
            return Response(
                {'error': 'Списание уже проведено'},
                status=400
            )

        items = WriteOffItem.objects.filter(
            write_off=write_off
        )

        if not items.exists():
            return Response(
                {'error': 'Нет товаров для списания'},
                status=400
            )

        with transaction.atomic():
            prepared = []

            for item in items:
                stock = Stock.objects.select_for_update().filter(
                    warehouse=write_off.warehouse,
                    product=item.product
                ).first()

                if not stock:
                    return Response(
                        {
                            'error':
                            f'Товара {item.product} нет на складе'
                        },
                        status=400
                    )

                if stock.quantity < item.quantity:
                    return Response(
                        {
                            'error':
                            f'Недостаточно товара {item.product}'
                        },
                        status=400
                    )

                prepared.append((item, stock))

            for item, stock in prepared:
                item.cost = stock.average_cost
                item.save()

                stock.quantity -= item.quantity
                stock.save()

                StockMovement.objects.create(
                    warehouse=write_off.warehouse,
                    product=item.product,
                    movement_type='WRITE_OFF',
                    quantity=item.quantity,
                    unit_cost=item.cost,
                    document_type='WRITE_OFF',
                    document_id=write_off.id,
                    comment=write_off.reason,
                )

            write_off.status = 'POSTED'
            write_off.save()

            create_audit(
                request,
                'POST',
                write_off,
                f'Проведено списание №{write_off.number}'
            )

        return Response({
            'message': 'Списание успешно проведено'
        })


class UnpostWriteOffView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        write_off = get_object_or_404(WriteOff, pk=pk)

        if write_off.status != 'POSTED':
            return Response(
                {'error': 'Списание не проведено'},
                status=400
            )

        items = WriteOffItem.objects.filter(
            write_off=write_off
        )

        with transaction.atomic():
            for item in items:
                stock, created = Stock.objects.get_or_create(
                    warehouse=write_off.warehouse,
                    product=item.product,
                    defaults={
                        'quantity': 0,
                        'average_cost': item.cost,
                    }
                )

                stock.quantity += item.quantity
                stock.save()

            StockMovement.objects.filter(
                document_type='WRITE_OFF',
                document_id=write_off.id
            ).delete()

            write_off.status = 'DRAFT'
            write_off.save()

            create_audit(
                request,
                'CANCEL',
                write_off,
                f'Отменено списание №{write_off.number}'
            )

        return Response({
            'message': 'Проведение списания отменено'
        })


# =========================================================
# INVENTORY
# =========================================================

class InventoryListCreateView(ListCreateAPIView):
    queryset = Inventory.objects.all().order_by('-created_at')
    serializer_class = InventorySerializer
    permission_classes = [IsWarehouseWorker]


class InventoryDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsWarehouseWorker]


class InventoryItemListCreateView(ListCreateAPIView):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsWarehouseWorker]


class InventoryItemDetailView(RetrieveUpdateDestroyAPIView):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsWarehouseWorker]


class PostInventoryView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        inventory = get_object_or_404(Inventory, pk=pk)

        if inventory.status == 'POSTED':
            return Response(
                {'error': 'Инвентаризация уже проведена'},
                status=400
            )

        items = InventoryItem.objects.filter(
            inventory=inventory
        )

        if not items.exists():
            return Response(
                {'error': 'В инвентаризации нет товаров'},
                status=400
            )

        with transaction.atomic():
            for item in items:
                stock, created = Stock.objects.get_or_create(
                    warehouse=inventory.warehouse,
                    product=item.product,
                    defaults={
                        'quantity': 0,
                        'average_cost': 0,
                    }
                )

                item.system_quantity = stock.quantity
                item.difference = (
                    item.actual_quantity
                    -
                    item.system_quantity
                )
                item.save()

                stock.quantity = item.actual_quantity
                stock.save()

                if item.difference != 0:
                    StockMovement.objects.create(
                        warehouse=inventory.warehouse,
                        product=item.product,
                        movement_type='INVENTORY',
                        quantity=abs(item.difference),
                        unit_cost=stock.average_cost,
                        document_type='INVENTORY',
                        document_id=inventory.id,
                        comment=(
                            f'Инвентаризация №{inventory.number}, '
                            f'разница {item.difference}'
                        ),
                    )

            inventory.status = 'POSTED'
            inventory.save()

            create_audit(
                request,
                'POST',
                inventory,
                f'Проведена инвентаризация №{inventory.number}'
            )

        return Response({
            'message': 'Инвентаризация успешно проведена'
        })


class UnpostInventoryView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        inventory = get_object_or_404(Inventory, pk=pk)

        if inventory.status != 'POSTED':
            return Response(
                {'error': 'Инвентаризация не проведена'},
                status=400
            )

        items = InventoryItem.objects.filter(
            inventory=inventory
        )

        with transaction.atomic():
            for item in items:
                stock, created = Stock.objects.get_or_create(
                    warehouse=inventory.warehouse,
                    product=item.product,
                    defaults={
                        'quantity': 0,
                        'average_cost': 0,
                    }
                )

                stock.quantity = item.system_quantity
                stock.save()

            StockMovement.objects.filter(
                document_type='INVENTORY',
                document_id=inventory.id
            ).delete()

            inventory.status = 'DRAFT'
            inventory.save()

            create_audit(
                request,
                'CANCEL',
                inventory,
                f'Отменена инвентаризация №{inventory.number}'
            )

        return Response({
            'message': 'Проведение инвентаризации отменено'
        })


# =========================================================
# FINANCE
# =========================================================

class CashAccountListCreateView(ListCreateAPIView):
    queryset = CashAccount.objects.all()
    serializer_class = CashAccountSerializer
    permission_classes = [IsAccountant]


class CashAccountDetailView(RetrieveUpdateDestroyAPIView):
    queryset = CashAccount.objects.all()
    serializer_class = CashAccountSerializer
    permission_classes = [IsAccountant]


class FinanceCategoryListCreateView(ListCreateAPIView):
    queryset = FinanceCategory.objects.all()
    serializer_class = FinanceCategorySerializer
    permission_classes = [IsAccountant]


class FinanceCategoryDetailView(RetrieveUpdateDestroyAPIView):
    queryset = FinanceCategory.objects.all()
    serializer_class = FinanceCategorySerializer
    permission_classes = [IsAccountant]


class CashTransactionListCreateView(ListCreateAPIView):
    queryset = CashTransaction.objects.all().order_by('-created_at')
    serializer_class = CashTransactionSerializer
    permission_classes = [IsAccountant]


class CashTransactionDetailView(RetrieveUpdateDestroyAPIView):
    queryset = CashTransaction.objects.all()
    serializer_class = CashTransactionSerializer
    permission_classes = [IsAccountant]


class PostCashTransactionView(APIView):
    permission_classes = [IsAccountant]

    def post(self, request, pk):
        cash_transaction = get_object_or_404(
            CashTransaction,
            pk=pk
        )

        if cash_transaction.status == 'POSTED':
            return Response(
                {'error': 'Операция уже проведена'},
                status=400
            )

        with transaction.atomic():
            account = CashAccount.objects.select_for_update().get(
                pk=cash_transaction.account_id
            )

            if cash_transaction.transaction_type == 'INCOME':
                account.balance += cash_transaction.amount

            elif cash_transaction.transaction_type == 'EXPENSE':
                if account.balance < cash_transaction.amount:
                    return Response(
                        {'error': 'Недостаточно денег на счёте'},
                        status=400
                    )

                account.balance -= cash_transaction.amount

            account.save()

            cash_transaction.status = 'POSTED'
            cash_transaction.save()

            create_audit(
                request,
                'POST',
                cash_transaction,
                f'Проведена денежная операция '
                f'№{cash_transaction.number}'
            )

        return Response({
            'message': 'Денежная операция проведена',
            'balance': account.balance,
        })


class UnpostCashTransactionView(APIView):
    permission_classes = [IsAccountant]

    def post(self, request, pk):
        cash_transaction = get_object_or_404(
            CashTransaction,
            pk=pk
        )

        if cash_transaction.status != 'POSTED':
            return Response(
                {'error': 'Операция не проведена'},
                status=400
            )

        with transaction.atomic():
            account = CashAccount.objects.select_for_update().get(
                pk=cash_transaction.account_id
            )

            if cash_transaction.transaction_type == 'INCOME':
                if account.balance < cash_transaction.amount:
                    return Response(
                        {
                            'error':
                            'Недостаточно денег для отмены прихода'
                        },
                        status=400
                    )

                account.balance -= cash_transaction.amount

            elif cash_transaction.transaction_type == 'EXPENSE':
                account.balance += cash_transaction.amount

            account.save()

            cash_transaction.status = 'DRAFT'
            cash_transaction.save()

            create_audit(
                request,
                'CANCEL',
                cash_transaction,
                f'Отменена денежная операция '
                f'№{cash_transaction.number}'
            )

        return Response({
            'message': 'Денежная операция отменена',
            'balance': account.balance,
        })


# =========================================================
# MONEY TRANSFER
# =========================================================

class MoneyTransferListCreateView(ListCreateAPIView):
    queryset = MoneyTransfer.objects.all().order_by('-created_at')
    serializer_class = MoneyTransferSerializer
    permission_classes = [IsAccountant]

    def perform_create(self, serializer):
        from_account = serializer.validated_data['from_account']
        to_account = serializer.validated_data['to_account']
        amount = serializer.validated_data['amount']

        if from_account == to_account:
            raise ValidationError(
                'Нельзя переводить деньги на тот же счёт'
            )

        with transaction.atomic():
            from_account = CashAccount.objects.select_for_update().get(
                pk=from_account.pk
            )

            to_account = CashAccount.objects.select_for_update().get(
                pk=to_account.pk
            )

            if from_account.balance < amount:
                raise ValidationError(
                    'Недостаточно денег для перевода'
                )

            from_account.balance -= amount
            to_account.balance += amount

            from_account.save()
            to_account.save()

            money_transfer = serializer.save()

            create_audit(
                self.request,
                'POST',
                money_transfer,
                f'Перевод денег {amount}'
            )


class MoneyTransferDetailView(RetrieveAPIView):
    queryset = MoneyTransfer.objects.all()
    serializer_class = MoneyTransferSerializer
    permission_classes = [IsAccountant]


# =========================================================
# DEBTS
# =========================================================

class DebtListCreateView(ListCreateAPIView):
    queryset = Debt.objects.all().order_by('-created_at')
    serializer_class = DebtSerializer
    permission_classes = [IsAccountant]


class DebtDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Debt.objects.all()
    serializer_class = DebtSerializer
    permission_classes = [IsAccountant]


class PayDebtView(APIView):
    permission_classes = [IsAccountant]

    def post(self, request, pk):
        debt = get_object_or_404(Debt, pk=pk)
        amount = request.data.get('amount')
        cash_account_id = request.data.get('cash_account')

        if not amount or not cash_account_id:
            return Response({'error': 'Укажите amount и cash_account'}, status=400)

        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Неверная сумма'}, status=400)

        if not amount.is_finite():
            return Response({'error': 'Неверная сумма'}, status=400)

        if amount <= 0:
            return Response({'error': 'Сумма должна быть больше 0'}, status=400)

        remaining = debt.amount - debt.paid_amount
        if amount > remaining:
            return Response({'error': f'Остаток долга {remaining}'}, status=400)

        with transaction.atomic():
            debt = Debt.objects.select_for_update().get(pk=debt.pk)
            remaining = debt.amount - debt.paid_amount
            if amount > remaining:
                return Response({'error': f'Остаток долга {remaining}'}, status=400)

            account = get_object_or_404(
                CashAccount.objects.select_for_update(),
                pk=cash_account_id,
            )

            if debt.debt_type == 'CUSTOMER':
                account.balance += amount
                transaction_type = 'INCOME'
            elif debt.debt_type == 'SUPPLIER':
                if account.balance < amount:
                    return Response({'error': 'Недостаточно денег в кассе'}, status=400)
                account.balance -= amount
                transaction_type = 'EXPENSE'
            else:
                return Response({'error': 'Неверный тип долга'}, status=400)

            account.save()
            CashTransaction.objects.create(
                organization=debt.organization,
                account=account,
                counterparty=debt.counterparty,
                number=f'DEBT-{uuid4().hex}',
                date=timezone.now(),
                created_by=request.user,
                transaction_type=transaction_type,
                amount=amount,
                status='POSTED',
            )

            debt.paid_amount += amount
            if debt.paid_amount >= debt.amount:
                debt.status = 'PAID'
            else:
                debt.status = 'PARTIAL'
            debt.save()

            create_audit(request, 'UPDATE', debt, f'Оплата долга {amount}')

        return Response({
            'message': 'Долг оплачен',
            'amount': debt.amount,
            'paid_amount': debt.paid_amount,
            'remaining': debt.amount - debt.paid_amount,
            'status': debt.status,
            'cash_balance': account.balance,
        })


# =========================================================
# NOTIFICATIONS
# =========================================================

class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class UnreadNotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            is_read=False,
        ).order_by('-created_at')


class ReadNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            user=request.user,
        )
        notification.is_read = True
        notification.save()
        return Response({'message': 'Уведомление прочитано'})


class ReadAllNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).update(is_read=True)
        return Response({'message': 'Все уведомления прочитаны'})


# =========================================================
# AUDIT LOG
# =========================================================

class AuditLogListView(ListAPIView):
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuditor]


class AuditLogDetailView(RetrieveAPIView):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuditor]


class SaleReturnListCreateView(ListCreateAPIView):
    queryset = SaleReturn.objects.all().order_by('-created_at')
    serializer_class = SaleReturnSerializer
    permission_classes = [IsSalesWorker]

class SaleReturnDetailView(RetrieveUpdateDestroyAPIView):
    queryset = SaleReturn.objects.all()
    serializer_class = SaleReturnSerializer
    permission_classes = [IsSalesWorker]

class SaleReturnItemListCreateView(ListCreateAPIView):
    queryset = SaleReturnItem.objects.all()
    serializer_class = SaleReturnItemSerializer
    permission_classes = [IsSalesWorker]

class PurchaseReturnListCreateView(ListCreateAPIView):
    queryset = PurchaseReturn.objects.all().order_by('-created_at')
    serializer_class = PurchaseReturnSerializer
    permission_classes = [IsPurchaseWorker]

class PurchaseReturnDetailView(RetrieveUpdateDestroyAPIView):
    queryset = PurchaseReturn.objects.all()
    serializer_class = PurchaseReturnSerializer
    permission_classes = [IsPurchaseWorker]

class PurchaseReturnItemListCreateView(ListCreateAPIView):
    queryset = PurchaseReturnItem.objects.all()
    serializer_class = PurchaseReturnItemSerializer
    permission_classes = [IsPurchaseWorker]


class PostSaleReturnView(APIView):
    permission_classes = [IsSalesWorker]
    def post(self,request,pk):
        sale_return = get_object_or_404(SaleReturn,pk=pk)
        if sale_return.status == 'POSTED':
            return Response({'error':'Возврат уже проведён'},status=400)
        items = SaleReturnItem.objects.filter(sale_return=sale_return)
        if not items.exists():
            return Response({'error':'Нет товаров'},status=400)
        with transaction.atomic():
            for item in items:
                stock,created = Stock.objects.get_or_create(warehouse=sale_return.warehouse,product=item.product,defaults={'quantity':0,'average_cost':0})
                stock.quantity += item.quantity
                stock.save()
                StockMovement.objects.create(warehouse=sale_return.warehouse,product=item.product,movement_type='RETURN_IN',quantity=item.quantity,unit_cost=stock.average_cost,document_type='SALE_RETURN',document_id=sale_return.id,comment=f'Возврат продажи {sale_return.number}')
            sale_return.status = 'POSTED'
            sale_return.save()
        return Response({'message':'Возврат продажи проведён'})


class PostPurchaseReturnView(APIView):
    permission_classes = [IsPurchaseWorker]
    def post(self,request,pk):
        purchase_return = get_object_or_404(PurchaseReturn,pk=pk)
        if purchase_return.status == 'POSTED':
            return Response({'error':'Возврат уже проведён'},status=400)
        items = PurchaseReturnItem.objects.filter(purchase_return=purchase_return)
        if not items.exists():
            return Response({'error':'Нет товаров'},status=400)
        with transaction.atomic():
            prepared = []
            for item in items:
                stock = Stock.objects.select_for_update().filter(warehouse=purchase_return.warehouse,product=item.product).first()
                if not stock or stock.quantity < item.quantity:
                    return Response({'error':f'Недостаточно товара {item.product}'},status=400)
                prepared.append((item,stock))
            for item,stock in prepared:
                stock.quantity -= item.quantity
                stock.save()
                StockMovement.objects.create(warehouse=purchase_return.warehouse,product=item.product,movement_type='RETURN_OUT',quantity=item.quantity,unit_cost=stock.average_cost,document_type='PURCHASE_RETURN',document_id=purchase_return.id,comment=f'Возврат поставщику {purchase_return.number}')
            purchase_return.status = 'POSTED'
            purchase_return.save()
        return Response({'message':'Возврат поставщику проведён'})
