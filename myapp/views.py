from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import transaction
from django.db.models import Q,Sum
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
    StockReservation,DebtPayment,Account,JournalEntry,JournalEntryLine,DealStage,Lead,Deal,CRMTask,CRMActivity,
)
from .serializers import (
    SaleReturnSerializer,SaleReturnItemSerializer,PurchaseReturnSerializer,PurchaseReturnItemSerializer,
    OrganizationSerializer,BranchSerializer,OrganizationMemberSerializer,DepartmentSerializer,PositionSerializer,EmployeeSerializer,SalaryPaymentSerializer,
    CounterpartySerializer,ContactPersonSerializer,CategorySerializer,UnitSerializer,BrandSerializer,ProductSerializer,PriceTypeSerializer,ProductPriceSerializer,WarehouseSerializer,
    StockSerializer,StockMovementSerializer,PurchaseSerializer,PurchaseItemSerializer,SaleSerializer,SaleItemSerializer,StockTransferSerializer,StockTransferItemSerializer,
    WriteOffSerializer,WriteOffItemSerializer,InventorySerializer,InventoryItemSerializer,CashAccountSerializer,FinanceCategorySerializer,CashTransactionSerializer,MoneyTransferSerializer,DebtSerializer,AuditLogSerializer,NotificationSerializer,
)
from .advanced_serializers import (AccountSerializer,CRMActivitySerializer,CRMTaskSerializer,DealSerializer,DealStageSerializer,
    DebtPaymentSerializer,JournalEntryLineSerializer,JournalEntrySerializer,LeadSerializer,StockReservationSerializer,)

from .permissions import (IsAdminOrDirector,IsAccountant,IsWarehouseWorker,IsSalesWorker,IsPurchaseWorker,IsHRWorker,IsAuditor,)
from .cache_utils import (
    delete_cached, get_cached, invalidate_purchase_cache, invalidate_sales_cache,
    invalidate_stock_cache, set_cached,
)
from .accounting import (cancel_entries,entry_totals,post_cash_transaction_entry,post_debt_payment_entry,
    post_purchase_entry,post_salary_entry,post_sale_entry,post_transfer_entry,)
from .tenancy import OrganizationScopedMixin,ensure_organization_access,get_object_organization_id,organization_cache_scope,scope_queryset


# =========================================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def create_audit(request, action, obj, description):
    AuditLog.objects.create(
        organization_id=get_object_organization_id(obj),
        user=request.user,
        action=action,
        model_name=obj.__class__.__name__,
        object_id=obj.id,
        description=description,
        ip_address=request.META.get('REMOTE_ADDR'),
    )


def notify_roles(roles, title, message, notification_type='INFO', organization=None):
    users = User.objects.filter(role__in=roles, is_active=True)
    if organization is not None:
        users = users.filter(
            Q(organization_memberships__organization=organization,organization_memberships__is_active=True)|
            ~Q(organization_memberships__is_active=True)
        ).distinct()
    for user in users:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
        )


def get_scoped_object(request,model,**kwargs):
    return get_object_or_404(scope_queryset(model.objects.all(),request.user),**kwargs)


class PostedDocumentProtectMixin:
    protected_statuses = ('POSTED','CANCELLED')

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.status in self.protected_statuses:
            return Response(
                {'error': 'Нельзя изменять проведённый документ'},
                status=400,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.status in self.protected_statuses:
            return Response(
                {'error': 'Нельзя удалить проведённый документ'},
                status=400,
            )
        return super().destroy(request, *args, **kwargs)


class PostedItemProtectMixin:
    document_field = None

    def _is_posted(self, obj):
        return getattr(obj,self.document_field).status != 'DRAFT'

    def update(self, request, *args, **kwargs):
        if self._is_posted(self.get_object()):
            return Response({'error': 'Нельзя менять позицию проведённого документа'}, status=400)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self._is_posted(self.get_object()):
            return Response({'error': 'Нельзя удалить позицию проведённого документа'}, status=400)
        return super().destroy(request, *args, **kwargs)


def calculate_payment_status(total_amount, paid_amount):
    if paid_amount <= 0:
        return 'UNPAID'

    if paid_amount < total_amount:
        return 'PARTIAL'

    return 'PAID'


def process_sale_payment(sale):
    if sale.paid_amount < 0:
        raise ValidationError('Оплата не может быть отрицательной')
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
    if purchase.paid_amount < 0:
        raise ValidationError('Оплата не может быть отрицательной')
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

class OrganizationListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAdminOrDirector]

    def perform_create(self,serializer):
        organization = serializer.save()
        OrganizationMember.objects.get_or_create(
            organization=organization,user=self.request.user,
            defaults={'role':'OWNER','is_active':True},
        )


class OrganizationDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAdminOrDirector]


class BranchListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAdminOrDirector]


class BranchDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAdminOrDirector]


class OrganizationMemberListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = OrganizationMember.objects.all()
    serializer_class = OrganizationMemberSerializer
    permission_classes = [IsAdminOrDirector]


class OrganizationMemberDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = OrganizationMember.objects.all()
    serializer_class = OrganizationMemberSerializer
    permission_classes = [IsAdminOrDirector]


# =========================================================
# EMPLOYEES
# =========================================================

class DepartmentListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsHRWorker]


class DepartmentDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsHRWorker]


class PositionListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [IsHRWorker]


class PositionDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [IsHRWorker]


class EmployeeListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRWorker]
    filterset_fields = ['organization', 'branch', 'department', 'position', 'status']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']

class EmployeeDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRWorker]


class SalaryPaymentListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = SalaryPayment.objects.all()
    serializer_class = SalaryPaymentSerializer
    permission_classes = [IsHRWorker]


class SalaryPaymentDetailView(PostedDocumentProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    protected_statuses = ('PAID',)
    queryset = SalaryPayment.objects.all()
    serializer_class = SalaryPaymentSerializer
    permission_classes = [IsHRWorker]


class PaySalaryView(APIView):
    permission_classes = [IsHRWorker]

    def post(self, request, pk):
        salary = get_scoped_object(request,SalaryPayment,pk=pk)
        if salary.status == 'PAID':
            return Response({'error': 'Зарплата уже выплачена'}, status=400)
        if not salary.cash_account_id:
            return Response({'error': 'Выберите кассу'}, status=400)
        if salary.amount <= 0:
            return Response({'error': 'Сумма должна быть больше 0'}, status=400)

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
            cash_transaction = CashTransaction.objects.create(
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
            salary.paid_at = timezone.now()
            salary.save()
            post_salary_entry(salary,request.user)
            create_audit(
                request,
                'POST',
                salary,
                f'Выплачена зарплата {salary.employee}',
            )
            notify_roles(
                ['ADMIN', 'DIRECTOR', 'HR'],
                'Зарплата выплачена',
                f'Выплачена зарплата сотруднику {salary.employee}: {salary.amount}',
                'SALARY',
                organization=salary.employee.organization,
            )

        return Response({
            'message': 'Зарплата выплачена',
            'amount': salary.amount,
            'cash_balance': account.balance,
        })


# =========================================================
# COUNTERPARTIES
# =========================================================

class CounterpartyListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Counterparty.objects.all()
    serializer_class = CounterpartySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['organization','counterparty_type','person_type','is_active']
    search_fields = ['name','inn','phone','email']
    ordering_fields = ['name','created_at','opening_balance']


class CounterpartyDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Counterparty.objects.all()
    serializer_class = CounterpartySerializer
    permission_classes = [IsAuthenticated]


class ContactPersonListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = ContactPerson.objects.all()
    serializer_class = ContactPersonSerializer
    permission_classes = [IsAuthenticated]


class ContactPersonDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = ContactPerson.objects.all()
    serializer_class = ContactPersonSerializer
    permission_classes = [IsAuthenticated]


# =========================================================
# CATALOG
# =========================================================

class CategoryListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class CategoryDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class UnitListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]


class UnitDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]


class BrandListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticated]


class BrandDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticated]


class ProductListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Product.objects.all().order_by('id')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['organization','category','brand','unit','is_service','is_active']
    search_fields = ['name','sku','barcode','description']
    ordering_fields = ['name','purchase_price','sale_price','created_at']

    def list(self, request, *args, **kwargs):
        params = request.query_params.urlencode()
        scope = organization_cache_scope(request.user)
        parts = [value for value in (scope,params) if value]
        cache_key = 'products_list' if not parts else f"products_list_{'_'.join(parts)}"
        data = get_cached(cache_key)
        if data is None:
            response = super().list(request, *args, **kwargs)
            data = response.data
            set_cached(cache_key, data, 60, 'products_list')
        return Response(data)

    def perform_create(self, serializer):
        product = serializer.save()
        delete_cached('products_list', f'product_{product.pk}', 'dashboard', 'stocks', 'stock_report', 'top_products')


class ProductDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        self.get_object()
        cache_key = f"product_{kwargs['pk']}"
        data = get_cached(cache_key)
        if data is None:
            response = super().retrieve(request, *args, **kwargs)
            data = response.data
            set_cached(cache_key, data, 60)
        return Response(data)

    def perform_update(self, serializer):
        product = serializer.save()
        delete_cached('products_list', f'product_{product.pk}', 'dashboard', 'stocks', 'stock_report', 'top_products')

    def perform_destroy(self, instance):
        product_id = instance.pk
        instance.delete()
        delete_cached('products_list', f'product_{product_id}', 'dashboard', 'stocks', 'stock_report', 'top_products')


class PriceTypeListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = PriceType.objects.all()
    serializer_class = PriceTypeSerializer
    permission_classes = [IsAuthenticated]


class PriceTypeDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = PriceType.objects.all()
    serializer_class = PriceTypeSerializer
    permission_classes = [IsAuthenticated]


class ProductPriceListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer
    permission_classes = [IsAuthenticated]


class ProductPriceDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer
    permission_classes = [IsAuthenticated]


# =========================================================
# WAREHOUSE
# =========================================================

class WarehouseListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsWarehouseWorker]


class WarehouseDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsWarehouseWorker]

class StockListView(OrganizationScopedMixin, ListAPIView):
    queryset = Stock.objects.all().order_by('id')
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['warehouse', 'product']
    search_fields = ['product__name', 'product__sku', 'product__barcode']
    ordering_fields = ['quantity', 'average_cost']

    def list(self, request, *args, **kwargs):
        params = request.query_params.urlencode()
        scope = organization_cache_scope(request.user)
        parts = [value for value in (scope,params) if value]
        cache_key = 'stocks' if not parts else f"stocks_{'_'.join(parts)}"
        data = get_cached(cache_key)
        if data is None:
            response = super().list(request, *args, **kwargs)
            data = response.data
            set_cached(cache_key, data, 15, 'stocks')
        return Response(data)


class StockDetailView(OrganizationScopedMixin, RetrieveAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]


class StockMovementListView(OrganizationScopedMixin, ListAPIView):
    queryset = StockMovement.objects.all().order_by('-created_at')
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['warehouse','product','movement_type','document_type','document_id']
    ordering_fields = ['created_at','quantity','unit_cost']


# =========================================================
# PURCHASE
# =========================================================
class PurchaseListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Purchase.objects.all().order_by('-created_at')
    serializer_class = PurchaseSerializer
    permission_classes = [IsPurchaseWorker]
    filterset_fields = ['organization', 'warehouse', 'supplier', 'status', 'payment_status']
    search_fields = ['number']
    ordering_fields = ['created_at', 'total_amount']

class PurchaseDetailView(PostedDocumentProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [IsPurchaseWorker]


class PurchaseItemListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer
    permission_classes = [IsPurchaseWorker]


class PurchaseItemDetailView(PostedItemProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    document_field = 'purchase'
    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer
    permission_classes = [IsPurchaseWorker]


class PostPurchaseView(APIView):
    permission_classes = [IsPurchaseWorker]

    def post(self, request, pk):
        purchase = get_scoped_object(request,Purchase,pk=pk)

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
            purchase = Purchase.objects.select_for_update().get(pk=purchase.pk)
            if purchase.status == 'POSTED':
                return Response({'error': 'Закупка уже проведена'}, status=400)
            total_amount = Decimal('0')

            for item in items:
                item_total = (
                    item.quantity * item.price
                ) - item.discount

                item.total = item_total
                item.save()

                total_amount += item_total

                stock, created = Stock.objects.select_for_update().get_or_create(
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
            post_purchase_entry(purchase)

            create_audit(
                request,
                'POST',
                purchase,
                f'Проведена закупка №{purchase.number}'
            )
            notify_roles(
                ['ADMIN', 'DIRECTOR', 'PURCHASE_MANAGER'],
                'Новая закупка',
                f'Закупка №{purchase.number} проведена на сумму {purchase.total_amount}',
                'PURCHASE',
                organization=purchase.organization,
            )

        invalidate_purchase_cache()
        return Response({
            'message': 'Закупка успешно проведена',
            'purchase_id': purchase.id,
            'total_amount': purchase.total_amount,
        })


class UnpostPurchaseView(APIView):
    permission_classes = [IsPurchaseWorker]
    cancel_document = False

    def post(self, request, pk):
        purchase = get_scoped_object(request,Purchase,pk=pk)

        if purchase.status != 'POSTED':
            return Response(
                {'error': 'Закупка не проведена'},
                status=400
            )

        items = PurchaseItem.objects.filter(purchase=purchase)

        with transaction.atomic():
            purchase = Purchase.objects.select_for_update().get(pk=purchase.pk)
            if purchase.status != 'POSTED':
                return Response({'error': 'Закупка не проведена'}, status=400)

            prepared = []
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

                if stock.available_quantity < item.quantity:
                    return Response(
                        {
                            'error':
                            f'Нельзя отменить закупку. '
                            f'Товара {item.product} уже недостаточно'
                        },
                        status=400
                    )

                prepared.append((item, stock))

            for item, stock in prepared:
                new_quantity = stock.quantity - item.quantity
                if new_quantity > 0:
                    stock.average_cost = (
                        stock.quantity * stock.average_cost
                        - item.quantity * item.price
                    ) / new_quantity
                else:
                    stock.average_cost = Decimal('0')
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

            purchase.status = 'CANCELLED' if self.cancel_document else 'DRAFT'
            purchase.save()
            cancel_entries('PURCHASE',purchase.pk)

            create_audit(
                request,
                'CANCEL',
                purchase,
                f'Отменено проведение закупки №{purchase.number}'
            )

        invalidate_purchase_cache()
        return Response({
            'message': 'Проведение закупки отменено'
        })


# =========================================================
# SALE
# =========================================================

class SaleListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Sale.objects.all().order_by('-created_at')
    serializer_class = SaleSerializer
    permission_classes = [IsSalesWorker]
    filterset_fields = ['organization', 'warehouse', 'customer', 'status', 'payment_status']
    search_fields = ['number']
    ordering_fields = ['created_at', 'total_amount']

class SaleDetailView(PostedDocumentProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsSalesWorker]


class SaleItemListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    permission_classes = [IsSalesWorker]


class SaleItemDetailView(PostedItemProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    document_field = 'sale'
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    permission_classes = [IsSalesWorker]


class PostSaleView(APIView):
    permission_classes = [IsSalesWorker]

    def post(self, request, pk):
        sale = get_scoped_object(request,Sale,pk=pk)

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
            sale = Sale.objects.select_for_update().get(pk=sale.pk)
            if sale.status == 'POSTED':
                return Response({'error': 'Продажа уже проведена'}, status=400)
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

                if stock.available_quantity < item.quantity:
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
            post_sale_entry(sale)

            create_audit(
                request,
                'POST',
                sale,
                f'Проведена продажа №{sale.number}'
            )
            notify_roles(
                ['ADMIN', 'DIRECTOR', 'SALES_MANAGER'],
                'Новая продажа',
                f'Продажа №{sale.number} проведена на сумму {sale.total_amount}',
                'SALE',
                organization=sale.organization,
            )

        invalidate_sales_cache()
        return Response({
            'message': 'Продажа успешно проведена',
            'sale_id': sale.id,
            'total_amount': sale.total_amount,
        })


class UnpostSaleView(APIView):
    permission_classes = [IsSalesWorker]
    cancel_document = False

    def post(self, request, pk):
        sale = get_scoped_object(request,Sale,pk=pk)

        if sale.status != 'POSTED':
            return Response(
                {'error': 'Продажа не проведена'},
                status=400
            )

        items = SaleItem.objects.filter(sale=sale)

        with transaction.atomic():
            sale = Sale.objects.select_for_update().get(pk=sale.pk)
            if sale.status != 'POSTED':
                return Response({'error': 'Продажа не проведена'}, status=400)
            for item in items:
                stock, created = Stock.objects.select_for_update().get_or_create(
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

            sale.status = 'CANCELLED' if self.cancel_document else 'DRAFT'
            sale.save()
            cancel_entries('SALE',sale.pk)

            create_audit(
                request,
                'CANCEL',
                sale,
                f'Отменено проведение продажи №{sale.number}'
            )

        invalidate_sales_cache()
        return Response({
            'message': 'Проведение продажи отменено'
        })


# =========================================================
# STOCK TRANSFER
# =========================================================

class CancelSaleView(UnpostSaleView):
    cancel_document = True


class CancelPurchaseView(UnpostPurchaseView):
    cancel_document = True


class StockTransferListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = StockTransfer.objects.all().order_by('-created_at')
    serializer_class = StockTransferSerializer
    permission_classes = [IsWarehouseWorker]


class StockTransferDetailView(PostedDocumentProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = StockTransfer.objects.all()
    serializer_class = StockTransferSerializer
    permission_classes = [IsWarehouseWorker]


class StockTransferItemListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = StockTransferItem.objects.all()
    serializer_class = StockTransferItemSerializer
    permission_classes = [IsWarehouseWorker]


class StockTransferItemDetailView(PostedItemProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    document_field = 'transfer'
    queryset = StockTransferItem.objects.all()
    serializer_class = StockTransferItemSerializer
    permission_classes = [IsWarehouseWorker]


class PostStockTransferView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        transfer = get_scoped_object(request,StockTransfer,pk=pk)

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
            transfer = StockTransfer.objects.select_for_update().get(pk=transfer.pk)
            if transfer.status == 'POSTED':
                return Response({'error': 'Перемещение уже проведено'}, status=400)
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

                if from_stock.available_quantity < item.quantity:
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

                to_stock, created = Stock.objects.select_for_update().get_or_create(
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

        invalidate_stock_cache()
        return Response({
            'message': 'Перемещение успешно проведено'
        })


class UnpostStockTransferView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        transfer = get_scoped_object(request,StockTransfer,pk=pk)

        if transfer.status != 'POSTED':
            return Response(
                {'error': 'Перемещение не проведено'},
                status=400
            )

        items = StockTransferItem.objects.filter(
            transfer=transfer
        )

        with transaction.atomic():
            transfer = StockTransfer.objects.select_for_update().get(pk=transfer.pk)
            if transfer.status != 'POSTED':
                return Response({'error': 'Перемещение не проведено'}, status=400)

            prepared = []
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

                if to_stock.available_quantity < item.quantity:
                    return Response(
                        {
                            'error':
                            f'Нельзя отменить перемещение товара '
                            f'{item.product}'
                        },
                        status=400
                    )

                prepared.append((item, to_stock))

            for item, to_stock in prepared:
                to_stock.quantity -= item.quantity
                to_stock.save()

                from_stock, created = Stock.objects.select_for_update().get_or_create(
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

        invalidate_stock_cache()
        return Response({
            'message': 'Проведение перемещения отменено'
        })


# =========================================================
# WRITE OFF
# =========================================================

class WriteOffListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = WriteOff.objects.all().order_by('-created_at')
    serializer_class = WriteOffSerializer
    permission_classes = [IsWarehouseWorker]


class WriteOffDetailView(PostedDocumentProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = WriteOff.objects.all()
    serializer_class = WriteOffSerializer
    permission_classes = [IsWarehouseWorker]


class WriteOffItemListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = WriteOffItem.objects.all()
    serializer_class = WriteOffItemSerializer
    permission_classes = [IsWarehouseWorker]


class WriteOffItemDetailView(PostedItemProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    document_field = 'write_off'
    queryset = WriteOffItem.objects.all()
    serializer_class = WriteOffItemSerializer
    permission_classes = [IsWarehouseWorker]


class PostWriteOffView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        write_off = get_scoped_object(request,WriteOff,pk=pk)

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
            write_off = WriteOff.objects.select_for_update().get(pk=write_off.pk)
            if write_off.status == 'POSTED':
                return Response({'error': 'Списание уже проведено'}, status=400)
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

                if stock.available_quantity < item.quantity:
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

        invalidate_stock_cache()
        return Response({
            'message': 'Списание успешно проведено'
        })


class UnpostWriteOffView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        write_off = get_scoped_object(request,WriteOff,pk=pk)

        if write_off.status != 'POSTED':
            return Response(
                {'error': 'Списание не проведено'},
                status=400
            )

        items = WriteOffItem.objects.filter(
            write_off=write_off
        )

        with transaction.atomic():
            write_off = WriteOff.objects.select_for_update().get(pk=write_off.pk)
            if write_off.status != 'POSTED':
                return Response({'error': 'Списание не проведено'}, status=400)
            for item in items:
                stock, created = Stock.objects.select_for_update().get_or_create(
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

        invalidate_stock_cache()
        return Response({
            'message': 'Проведение списания отменено'
        })


# =========================================================
# INVENTORY
# =========================================================

class InventoryListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Inventory.objects.all().order_by('-created_at')
    serializer_class = InventorySerializer
    permission_classes = [IsWarehouseWorker]


class InventoryDetailView(PostedDocumentProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsWarehouseWorker]


class InventoryItemListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsWarehouseWorker]


class InventoryItemDetailView(PostedItemProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    document_field = 'inventory'
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsWarehouseWorker]


class PostInventoryView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        inventory = get_scoped_object(request,Inventory,pk=pk)

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
            inventory = Inventory.objects.select_for_update().get(pk=inventory.pk)
            if inventory.status == 'POSTED':
                return Response({'error': 'Инвентаризация уже проведена'}, status=400)
            for item in items:
                stock, created = Stock.objects.select_for_update().get_or_create(
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

        invalidate_stock_cache()
        return Response({
            'message': 'Инвентаризация успешно проведена'
        })


class UnpostInventoryView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request, pk):
        inventory = get_scoped_object(request,Inventory,pk=pk)

        if inventory.status != 'POSTED':
            return Response(
                {'error': 'Инвентаризация не проведена'},
                status=400
            )

        items = InventoryItem.objects.filter(
            inventory=inventory
        )

        with transaction.atomic():
            inventory = Inventory.objects.select_for_update().get(pk=inventory.pk)
            if inventory.status != 'POSTED':
                return Response({'error': 'Инвентаризация не проведена'}, status=400)
            for item in items:
                stock, created = Stock.objects.select_for_update().get_or_create(
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

        invalidate_stock_cache()
        return Response({
            'message': 'Проведение инвентаризации отменено'
        })


# =========================================================
# FINANCE
# =========================================================

class CashAccountListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = CashAccount.objects.all()
    serializer_class = CashAccountSerializer
    permission_classes = [IsAccountant]


class CashAccountDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = CashAccount.objects.all()
    serializer_class = CashAccountSerializer
    permission_classes = [IsAccountant]


class FinanceCategoryListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = FinanceCategory.objects.all()
    serializer_class = FinanceCategorySerializer
    permission_classes = [IsAccountant]


class FinanceCategoryDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = FinanceCategory.objects.all()
    serializer_class = FinanceCategorySerializer
    permission_classes = [IsAccountant]


class CashTransactionListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = CashTransaction.objects.all().order_by('-created_at')
    serializer_class = CashTransactionSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['organization','account','category','counterparty','transaction_type','status']
    search_fields = ['number','purpose']
    ordering_fields = ['date','amount','created_at']


class CashTransactionDetailView(PostedDocumentProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = CashTransaction.objects.all()
    serializer_class = CashTransactionSerializer
    permission_classes = [IsAccountant]


class PostCashTransactionView(APIView):
    permission_classes = [IsAccountant]

    def post(self, request, pk):
        cash_transaction = get_scoped_object(request,CashTransaction,pk=pk)

        if cash_transaction.status == 'POSTED':
            return Response(
                {'error': 'Операция уже проведена'},
                status=400
            )
        if cash_transaction.amount <= 0:
            return Response({'error': 'Сумма должна быть больше 0'}, status=400)

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
            post_cash_transaction_entry(cash_transaction,request.user)

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
        cash_transaction = get_scoped_object(request,CashTransaction,pk=pk)

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
            cancel_entries('CASH_TRANSACTION',cash_transaction.pk)

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

class MoneyTransferListCreateView(OrganizationScopedMixin, ListCreateAPIView):
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

            money_transfer = serializer.save(created_by=self.request.user)
            post_transfer_entry(money_transfer,self.request.user)

            create_audit(
                self.request,
                'POST',
                money_transfer,
                f'Перевод денег {amount}'
            )


class MoneyTransferDetailView(OrganizationScopedMixin, RetrieveAPIView):
    queryset = MoneyTransfer.objects.all()
    serializer_class = MoneyTransferSerializer
    permission_classes = [IsAccountant]


# =========================================================
# DEBTS
# =========================================================

class DebtListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = Debt.objects.all().order_by('-created_at')
    serializer_class = DebtSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['organization','counterparty','debt_type','status','due_date']
    ordering_fields = ['created_at','due_date','amount','paid_amount']


class DebtDetailView(OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = Debt.objects.all()
    serializer_class = DebtSerializer
    permission_classes = [IsAccountant]


class PayDebtView(APIView):
    permission_classes = [IsAccountant]

    def post(self, request, pk):
        debt = get_scoped_object(request,Debt,pk=pk)
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
            ensure_organization_access(request.user,account,debt)
            if account.organization_id != debt.organization_id:
                return Response({'error':'Касса относится к другой организации'},status=400)

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
            cash_transaction = CashTransaction.objects.create(
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
            debt_payment = DebtPayment.objects.create(
                debt=debt,cash_account=account,cash_transaction=cash_transaction,
                amount=amount,created_by=request.user,
            )
            post_debt_payment_entry(debt_payment,request.user)

            create_audit(request, 'UPDATE', debt, f'Оплата долга {amount}')
            if debt.status == 'PAID':
                notify_roles(
                    ['ADMIN', 'DIRECTOR', 'ACCOUNTANT'],
                    'Долг погашен',
                    f'Долг №{debt.id} полностью погашен',
                    'DEBT',
                    organization=debt.organization,
                )

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

class NotificationListView(OrganizationScopedMixin, ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class UnreadNotificationListView(OrganizationScopedMixin, ListAPIView):
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


class CheckLowStockView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self, request):
        stocks = scope_queryset(Stock.objects.select_related('product','warehouse'),request.user)
        count = 0
        for stock in stocks:
            if stock.quantity <= stock.product.min_stock:
                notify_roles(
                    ['ADMIN', 'DIRECTOR', 'WAREHOUSE_MANAGER', 'STOREKEEPER'],
                    'Заканчивается товар',
                    f'{stock.product} — остаток {stock.quantity} на складе {stock.warehouse}',
                    'STOCK',
                    organization=stock.warehouse.organization,
                )
                count += 1
        return Response({
            'message': 'Проверка завершена',
            'low_stock_count': count,
        })


# =========================================================
# AUDIT LOG
# =========================================================

class AuditLogListView(OrganizationScopedMixin, ListAPIView):
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuditor]


class AuditLogDetailView(OrganizationScopedMixin, RetrieveAPIView):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuditor]


class SaleReturnListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = SaleReturn.objects.all().order_by('-created_at')
    serializer_class = SaleReturnSerializer
    permission_classes = [IsSalesWorker]

class SaleReturnDetailView(PostedDocumentProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = SaleReturn.objects.all()
    serializer_class = SaleReturnSerializer
    permission_classes = [IsSalesWorker]

class SaleReturnItemListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = SaleReturnItem.objects.all()
    serializer_class = SaleReturnItemSerializer
    permission_classes = [IsSalesWorker]

class PurchaseReturnListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = PurchaseReturn.objects.all().order_by('-created_at')
    serializer_class = PurchaseReturnSerializer
    permission_classes = [IsPurchaseWorker]

class PurchaseReturnDetailView(PostedDocumentProtectMixin, OrganizationScopedMixin, RetrieveUpdateDestroyAPIView):
    queryset = PurchaseReturn.objects.all()
    serializer_class = PurchaseReturnSerializer
    permission_classes = [IsPurchaseWorker]

class PurchaseReturnItemListCreateView(OrganizationScopedMixin, ListCreateAPIView):
    queryset = PurchaseReturnItem.objects.all()
    serializer_class = PurchaseReturnItemSerializer
    permission_classes = [IsPurchaseWorker]


class PostSaleReturnView(APIView):
    permission_classes = [IsSalesWorker]
    def post(self,request,pk):
        sale_return = get_scoped_object(request,SaleReturn,pk=pk)
        if sale_return.status == 'POSTED':
            return Response({'error':'Возврат уже проведён'},status=400)
        items = SaleReturnItem.objects.filter(sale_return=sale_return)
        if not items.exists():
            return Response({'error':'Нет товаров'},status=400)
        with transaction.atomic():
            sale_return = SaleReturn.objects.select_for_update().get(pk=sale_return.pk)
            if sale_return.status == 'POSTED':
                return Response({'error':'Возврат уже проведён'},status=400)
            if sale_return.sale.status != 'POSTED':
                return Response({'error':'Продажа не проведена'},status=400)
            if sale_return.warehouse_id != sale_return.sale.warehouse_id:
                return Response({'error':'Склад возврата должен совпадать со складом продажи'},status=400)
            requested_items = items.values('product_id').annotate(total=Sum('quantity'))
            for requested in requested_items:
                sold = SaleItem.objects.filter(sale=sale_return.sale,product_id=requested['product_id']).aggregate(total=Sum('quantity'))['total'] or 0
                returned = SaleReturnItem.objects.filter(sale_return__sale=sale_return.sale,sale_return__status='POSTED',product_id=requested['product_id']).aggregate(total=Sum('quantity'))['total'] or 0
                if requested['total'] > sold-returned:
                    product = Product.objects.get(pk=requested['product_id'])
                    return Response({'error':f'Количество возврата товара {product} превышает проданное'},status=400)
            for item in items:
                stock,created = Stock.objects.select_for_update().get_or_create(warehouse=sale_return.warehouse,product=item.product,defaults={'quantity':0,'average_cost':0})
                stock.quantity += item.quantity
                stock.save()
                StockMovement.objects.create(warehouse=sale_return.warehouse,product=item.product,movement_type='RETURN_IN',quantity=item.quantity,unit_cost=stock.average_cost,document_type='SALE_RETURN',document_id=sale_return.id,comment=f'Возврат продажи {sale_return.number}')
            sale_return.status = 'POSTED'
            sale_return.save()
            create_audit(request,'POST',sale_return,f'Проведён возврат продажи №{sale_return.number}')
        invalidate_stock_cache()
        return Response({'message':'Возврат продажи проведён'})


class PostPurchaseReturnView(APIView):
    permission_classes = [IsPurchaseWorker]
    def post(self,request,pk):
        purchase_return = get_scoped_object(request,PurchaseReturn,pk=pk)
        if purchase_return.status == 'POSTED':
            return Response({'error':'Возврат уже проведён'},status=400)
        items = PurchaseReturnItem.objects.filter(purchase_return=purchase_return)
        if not items.exists():
            return Response({'error':'Нет товаров'},status=400)
        with transaction.atomic():
            purchase_return = PurchaseReturn.objects.select_for_update().get(pk=purchase_return.pk)
            if purchase_return.status == 'POSTED':
                return Response({'error':'Возврат уже проведён'},status=400)
            if purchase_return.purchase.status != 'POSTED':
                return Response({'error':'Закупка не проведена'},status=400)
            if purchase_return.warehouse_id != purchase_return.purchase.warehouse_id:
                return Response({'error':'Склад возврата должен совпадать со складом закупки'},status=400)
            requested_items = items.values('product_id').annotate(total=Sum('quantity'))
            for requested in requested_items:
                purchased = PurchaseItem.objects.filter(purchase=purchase_return.purchase,product_id=requested['product_id']).aggregate(total=Sum('quantity'))['total'] or 0
                returned = PurchaseReturnItem.objects.filter(purchase_return__purchase=purchase_return.purchase,purchase_return__status='POSTED',product_id=requested['product_id']).aggregate(total=Sum('quantity'))['total'] or 0
                if requested['total'] > purchased-returned:
                    product = Product.objects.get(pk=requested['product_id'])
                    return Response({'error':f'Количество возврата товара {product} превышает закупленное'},status=400)
            prepared = []
            for item in items:
                stock = Stock.objects.select_for_update().filter(warehouse=purchase_return.warehouse,product=item.product).first()
                if not stock or stock.available_quantity < item.quantity:
                    return Response({'error':f'Недостаточно товара {item.product}'},status=400)
                prepared.append((item,stock))
            for item,stock in prepared:
                stock.quantity -= item.quantity
                stock.save()
                StockMovement.objects.create(warehouse=purchase_return.warehouse,product=item.product,movement_type='RETURN_OUT',quantity=item.quantity,unit_cost=stock.average_cost,document_type='PURCHASE_RETURN',document_id=purchase_return.id,comment=f'Возврат поставщику {purchase_return.number}')
            purchase_return.status = 'POSTED'
            purchase_return.save()
            create_audit(request,'POST',purchase_return,f'Проведён возврат поставщику №{purchase_return.number}')
        invalidate_stock_cache()
        return Response({'message':'Возврат поставщику проведён'})


class ProductArchiveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request,pk):
        product = get_scoped_object(request,Product,pk=pk)
        product.is_active = False
        product.archived_at = timezone.now()
        product.save(update_fields=['is_active','archived_at'])
        delete_cached('products_list',f'product_{product.pk}')
        create_audit(request,'UPDATE',product,'Товар архивирован')
        return Response({'message':'Товар архивирован'})


class StockReservationListCreateView(OrganizationScopedMixin,ListCreateAPIView):
    queryset = StockReservation.objects.all().order_by('-created_at')
    serializer_class = StockReservationSerializer
    permission_classes = [IsWarehouseWorker]
    filterset_fields = ['organization','warehouse','product','status']

    def perform_create(self,serializer):
        data = serializer.validated_data
        with transaction.atomic():
            stock = get_object_or_404(Stock.objects.select_for_update(),warehouse=data['warehouse'],product=data['product'])
            ensure_organization_access(self.request.user,stock)
            if stock.available_quantity < data['quantity']:
                raise ValidationError(f'Доступно только {stock.available_quantity}')
            stock.reserved_quantity += data['quantity']
            stock.save(update_fields=['reserved_quantity','updated_at'])
            reservation = serializer.save(created_by=self.request.user)
            create_audit(self.request,'CREATE',reservation,f'Резерв {reservation.quantity}')
        invalidate_stock_cache()


class ReleaseStockReservationView(APIView):
    permission_classes = [IsWarehouseWorker]

    def post(self,request,pk):
        reservation = get_scoped_object(request,StockReservation,pk=pk)
        if reservation.status != 'ACTIVE':
            return Response({'error':'Резерв уже снят'},status=400)
        with transaction.atomic():
            reservation = StockReservation.objects.select_for_update().get(pk=reservation.pk)
            stock = Stock.objects.select_for_update().get(warehouse=reservation.warehouse,product=reservation.product)
            stock.reserved_quantity = max(Decimal('0'),stock.reserved_quantity-reservation.quantity)
            stock.save(update_fields=['reserved_quantity','updated_at'])
            reservation.status = 'RELEASED'
            reservation.released_at = timezone.now()
            reservation.save(update_fields=['status','released_at'])
            create_audit(request,'CANCEL',reservation,'Резерв снят')
        invalidate_stock_cache()
        return Response({'message':'Резерв снят','available_quantity':stock.available_quantity})


class DebtPaymentListView(OrganizationScopedMixin,ListAPIView):
    queryset = DebtPayment.objects.all().order_by('-created_at')
    serializer_class = DebtPaymentSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['debt','cash_account']


class AccountListCreateView(OrganizationScopedMixin,ListCreateAPIView):
    queryset = Account.objects.all().order_by('code')
    serializer_class = AccountSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['organization','account_type','is_active']
    search_fields = ['code','name']


class AccountDetailView(OrganizationScopedMixin,RetrieveUpdateDestroyAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAccountant]


class JournalEntryListCreateView(OrganizationScopedMixin,ListCreateAPIView):
    queryset = JournalEntry.objects.prefetch_related('lines').order_by('-date','-id')
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['organization','status','document_type']
    search_fields = ['description']

    def perform_create(self,serializer):
        serializer.save(created_by=self.request.user)


class JournalEntryDetailView(PostedDocumentProtectMixin,OrganizationScopedMixin,RetrieveUpdateDestroyAPIView):
    protected_statuses = ('POSTED','CANCELLED')
    queryset = JournalEntry.objects.prefetch_related('lines')
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAccountant]


class JournalEntryLineListCreateView(OrganizationScopedMixin,ListCreateAPIView):
    queryset = JournalEntryLine.objects.all()
    serializer_class = JournalEntryLineSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['journal_entry','account']


class JournalEntryLineDetailView(PostedItemProtectMixin,OrganizationScopedMixin,RetrieveUpdateDestroyAPIView):
    document_field = 'journal_entry'
    queryset = JournalEntryLine.objects.all()
    serializer_class = JournalEntryLineSerializer
    permission_classes = [IsAccountant]


class PostJournalEntryView(APIView):
    permission_classes = [IsAccountant]

    def post(self,request,pk):
        entry = get_scoped_object(request,JournalEntry,pk=pk)
        if entry.status != 'DRAFT':
            return Response({'error':'Проводка не является черновиком'},status=400)
        debit,credit = entry_totals(entry)
        if not entry.lines.exists() or debit <= 0 or debit != credit:
            return Response({'error':f'Проводка не сбалансирована: дебет {debit}, кредит {credit}'},status=400)
        if entry.lines.exclude(account__organization=entry.organization).exists():
            return Response({'error':'Счета относятся к другой организации'},status=400)
        entry.status = 'POSTED'
        entry.save(update_fields=['status'])
        create_audit(request,'POST',entry,'Проводка проведена')
        return Response({'message':'Проводка проведена','debit':debit,'credit':credit})


class CancelJournalEntryView(APIView):
    permission_classes = [IsAccountant]

    def post(self,request,pk):
        entry = get_scoped_object(request,JournalEntry,pk=pk)
        if entry.status != 'POSTED':
            return Response({'error':'Проводка не проведена'},status=400)
        entry.status = 'CANCELLED'
        entry.save(update_fields=['status'])
        create_audit(request,'CANCEL',entry,'Проводка отменена')
        return Response({'message':'Проводка отменена'})


class DealStageListCreateView(OrganizationScopedMixin,ListCreateAPIView):
    queryset = DealStage.objects.all()
    serializer_class = DealStageSerializer
    permission_classes = [IsSalesWorker]
    filterset_fields = ['organization','is_closed']


class DealStageDetailView(OrganizationScopedMixin,RetrieveUpdateDestroyAPIView):
    queryset = DealStage.objects.all()
    serializer_class = DealStageSerializer
    permission_classes = [IsSalesWorker]


class LeadListCreateView(OrganizationScopedMixin,ListCreateAPIView):
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer
    permission_classes = [IsSalesWorker]
    filterset_fields = ['organization','status','source','responsible']
    search_fields = ['name','phone','email']
    ordering_fields = ['created_at','expected_amount','probability']


class LeadDetailView(OrganizationScopedMixin,RetrieveUpdateDestroyAPIView):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsSalesWorker]


class ConvertLeadView(APIView):
    permission_classes = [IsSalesWorker]

    def post(self,request,pk):
        lead = get_scoped_object(request,Lead,pk=pk)
        if lead.status == 'CONVERTED':
            return Response({'error':'Лид уже конвертирован'},status=400)
        with transaction.atomic():
            customer = Counterparty.objects.create(
                organization=lead.organization,name=lead.name,counterparty_type='CUSTOMER',
                person_type='COMPANY',phone=lead.phone,email=lead.email,
            )
            deal = Deal.objects.create(
                organization=lead.organization,title=request.data.get('title') or lead.name,
                customer=customer,lead=lead,responsible=lead.responsible,
                expected_amount=lead.expected_amount,probability=lead.probability,
            )
            lead.customer = customer
            lead.status = 'CONVERTED'
            lead.save(update_fields=['customer','status','updated_at'])
            create_audit(request,'UPDATE',lead,f'Лид конвертирован в клиента {customer.pk} и сделку {deal.pk}')
        return Response({'message':'Лид конвертирован','customer':customer.pk,'deal':deal.pk})


class DealListCreateView(OrganizationScopedMixin,ListCreateAPIView):
    queryset = Deal.objects.all().order_by('-created_at')
    serializer_class = DealSerializer
    permission_classes = [IsSalesWorker]
    filterset_fields = ['organization','customer','lead','stage','responsible','status']
    search_fields = ['title','customer__name']
    ordering_fields = ['created_at','expected_amount','probability']


class DealDetailView(OrganizationScopedMixin,RetrieveUpdateDestroyAPIView):
    queryset = Deal.objects.all()
    serializer_class = DealSerializer
    permission_classes = [IsSalesWorker]


class CRMTaskListCreateView(OrganizationScopedMixin,ListCreateAPIView):
    queryset = CRMTask.objects.all().order_by('due_at','id')
    serializer_class = CRMTaskSerializer
    permission_classes = [IsSalesWorker]
    filterset_fields = ['organization','lead','deal','assigned_to','status']
    search_fields = ['title']


class CRMTaskDetailView(OrganizationScopedMixin,RetrieveUpdateDestroyAPIView):
    queryset = CRMTask.objects.all()
    serializer_class = CRMTaskSerializer
    permission_classes = [IsSalesWorker]


class CRMActivityListCreateView(OrganizationScopedMixin,ListCreateAPIView):
    queryset = CRMActivity.objects.all().order_by('-happened_at')
    serializer_class = CRMActivitySerializer
    permission_classes = [IsSalesWorker]
    filterset_fields = ['organization','activity_type','customer','lead','deal','employee']
    search_fields = ['subject','notes']

    def perform_create(self,serializer):
        serializer.save(created_by=self.request.user)


class CRMActivityDetailView(OrganizationScopedMixin,RetrieveUpdateDestroyAPIView):
    queryset = CRMActivity.objects.all()
    serializer_class = CRMActivitySerializer
    permission_classes = [IsSalesWorker]


class GenerateSalaryPaymentsView(APIView):
    permission_classes = [IsHRWorker]

    def post(self,request):
        organization = get_scoped_object(request,Organization,pk=request.data.get('organization'))
        month = request.data.get('month')
        if not month:
            return Response({'error':'Укажите month в формате YYYY-MM-DD'},status=400)
        created = 0
        for employee in Employee.objects.filter(organization=organization,status='WORKING'):
            if SalaryPayment.objects.filter(employee=employee,month=month).exists():
                continue
            SalaryPayment.objects.create(employee=employee,month=month,base_salary=employee.salary,amount=employee.salary)
            created += 1
        return Response({'message':'Начисления созданы','created':created})
