from rest_framework.generics import (ListCreateAPIView,RetrieveUpdateDestroyAPIView,ListAPIView,)
from rest_framework.permissions import IsAuthenticated
from .models import (Organization,Branch,OrganizationMember,Department,Position,Employee,SalaryPayment,Counterparty,ContactPerson,
    Category,Unit,Brand,Product,PriceType,ProductPrice,Warehouse,Stock,StockMovement,Purchase,PurchaseItem,Sale,SaleItem,StockTransfer,
    StockTransferItem,WriteOff,WriteOffItem,Inventory,InventoryItem,CashAccount,FinanceCategory,CashTransaction,MoneyTransfer,Debt,AuditLog,
)
from .serializers import (OrganizationSerializer,BranchSerializer,OrganizationMemberSerializer,DepartmentSerializer,
    PositionSerializer,EmployeeSerializer,SalaryPaymentSerializer,CounterpartySerializer,ContactPersonSerializer,
    CategorySerializer,UnitSerializer,BrandSerializer,ProductSerializer,PriceTypeSerializer,ProductPriceSerializer,
    WarehouseSerializer,StockSerializer,StockMovementSerializer,PurchaseSerializer,PurchaseItemSerializer,SaleSerializer,
    SaleItemSerializer,StockTransferSerializer,StockTransferItemSerializer,WriteOffSerializer,WriteOffItemSerializer,
    InventorySerializer,InventoryItemSerializer,CashAccountSerializer,FinanceCategorySerializer,CashTransactionSerializer,
    MoneyTransferSerializer,DebtSerializer,AuditLogSerializer,
)
from .permissions import (IsAdminOrDirector,IsAccountant,IsWarehouseWorker,IsSalesWorker,IsPurchaseWorker,IsHRWorker,IsAuditor,)


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
    permission_classes = [IsWarehouseWorker]


class StockMovementListView(ListAPIView):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsWarehouseWorker]

class PurchaseListCreateView(ListCreateAPIView):
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [IsPurchaseWorker]


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

class SaleListCreateView(ListCreateAPIView):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsSalesWorker]


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

class StockTransferListCreateView(ListCreateAPIView):
    queryset = StockTransfer.objects.all()
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

class WriteOffListCreateView(ListCreateAPIView):
    queryset = WriteOff.objects.all()
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

class InventoryListCreateView(ListCreateAPIView):
    queryset = Inventory.objects.all()
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
    queryset = CashTransaction.objects.all()
    serializer_class = CashTransactionSerializer
    permission_classes = [IsAccountant]


class CashTransactionDetailView(RetrieveUpdateDestroyAPIView):
    queryset = CashTransaction.objects.all()
    serializer_class = CashTransactionSerializer
    permission_classes = [IsAccountant]


class MoneyTransferListCreateView(ListCreateAPIView):
    queryset = MoneyTransfer.objects.all()
    serializer_class = MoneyTransferSerializer
    permission_classes = [IsAccountant]


class MoneyTransferDetailView(RetrieveUpdateDestroyAPIView):
    queryset = MoneyTransfer.objects.all()
    serializer_class = MoneyTransferSerializer
    permission_classes = [IsAccountant]


class DebtListCreateView(ListCreateAPIView):
    queryset = Debt.objects.all()
    serializer_class = DebtSerializer
    permission_classes = [IsAccountant]


class DebtDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Debt.objects.all()
    serializer_class = DebtSerializer
    permission_classes = [IsAccountant]

class AuditLogListView(ListAPIView):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuditor]