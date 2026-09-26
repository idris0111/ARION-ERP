from django.db.models import Model
from django.utils import timezone
from rest_framework import serializers
from .models import (Organization, SaleReturn,SaleReturnItem,PurchaseReturn,PurchaseReturnItem,Branch,OrganizationMember,Department,Position,Employee,SalaryPayment,
    Counterparty,ContactPerson,Category,Unit,Brand,Product,PriceType,ProductPrice,Warehouse,Stock,StockMovement,Purchase,PurchaseItem,Sale,
    SaleItem,StockTransfer,StockTransferItem,WriteOff,WriteOffItem,Inventory,InventoryItem,CashAccount,FinanceCategory,CashTransaction,MoneyTransfer,Debt,AuditLog,Notification,
    StockReservation,DebtPayment,Account,JournalEntry,JournalEntryLine,DealStage,Lead,Deal,CRMTask,CRMActivity,
)
from .tenancy import ensure_organization_access,get_object_organization_id


class OrganizationModelSerializer(serializers.ModelSerializer):
    def run_validation(self,data=serializers.empty):
        validated = super().run_validation(data)
        request = self.context.get('request')
        if request:
            objects = [value for value in validated.values() if isinstance(value,Model)]
            if self.instance is not None:
                objects.append(self.instance)
            ensure_organization_access(request.user,*objects)
            organization_ids = {get_object_organization_id(obj) for obj in objects if get_object_organization_id(obj) is not None}
            if len(organization_ids) > 1:
                raise serializers.ValidationError('Связанные объекты относятся к разным организациям')
        return validated


class OrganizationSerializer(OrganizationModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'


class BranchSerializer(OrganizationModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'


class OrganizationMemberSerializer(OrganizationModelSerializer):
    class Meta:
        model = OrganizationMember
        fields = '__all__'


class DepartmentSerializer(OrganizationModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


class PositionSerializer(OrganizationModelSerializer):
    class Meta:
        model = Position
        fields = '__all__'


class EmployeeSerializer(OrganizationModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'


class SalaryPaymentSerializer(OrganizationModelSerializer):
    class Meta:
        model = SalaryPayment
        fields = '__all__'
        read_only_fields = ['status','paid_at','amount']

    def validate(self,data):
        employee = data.get('employee') or getattr(self.instance,'employee',None)
        base_salary = data.get('base_salary',getattr(self.instance,'base_salary',0))
        bonus = data.get('bonus',getattr(self.instance,'bonus',0))
        deduction = data.get('deduction',getattr(self.instance,'deduction',0))
        if not base_salary and employee:
            base_salary = employee.salary
            data['base_salary'] = base_salary
        data['amount'] = base_salary+bonus-deduction
        if data['amount'] <= 0:
            raise serializers.ValidationError('???????? ???????? ?????? ???? ?????? 0')
        return data


class CounterpartySerializer(OrganizationModelSerializer):
    class Meta:
        model = Counterparty
        fields = '__all__'


class ContactPersonSerializer(OrganizationModelSerializer):
    class Meta:
        model = ContactPerson
        fields = '__all__'


class CategorySerializer(OrganizationModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class UnitSerializer(OrganizationModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'


class BrandSerializer(OrganizationModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'


class ProductSerializer(OrganizationModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class PriceTypeSerializer(OrganizationModelSerializer):
    class Meta:
        model = PriceType
        fields = '__all__'


class ProductPriceSerializer(OrganizationModelSerializer):
    class Meta:
        model = ProductPrice
        fields = '__all__'


class WarehouseSerializer(OrganizationModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'


class StockSerializer(OrganizationModelSerializer):
    available_quantity = serializers.DecimalField(max_digits=14,decimal_places=3,read_only=True)

    class Meta:
        model = Stock
        fields = '__all__'
        read_only_fields = ['quantity','reserved_quantity','average_cost']


class StockMovementSerializer(OrganizationModelSerializer):
    class Meta:
        model = StockMovement
        fields = '__all__'


class PurchaseSerializer(OrganizationModelSerializer):
    class Meta:
        model = Purchase
        fields = '__all__'
        read_only_fields = ['status', 'payment_status', 'total_amount']

    def validate_paid_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Оплата не может быть отрицательной')
        return value


class PurchaseItemSerializer(OrganizationModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = '__all__'
        read_only_fields = ['total']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Цена не может быть отрицательной')
        return value

    def validate(self, data):
        purchase = data.get('purchase')
        if purchase is None and self.instance is not None:
            purchase = self.instance.purchase
        if purchase and purchase.status == 'POSTED':
            raise serializers.ValidationError('Нельзя менять проведённую закупку')
        return data


class SaleSerializer(OrganizationModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ['status', 'payment_status', 'total_amount']

    def validate_paid_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Оплата не может быть отрицательной')
        return value


class SaleItemSerializer(OrganizationModelSerializer):
    class Meta:
        model = SaleItem
        fields = '__all__'
        read_only_fields = ['total']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Цена не может быть отрицательной')
        return value

    def validate(self, data):
        sale = data.get('sale')
        if sale is None and self.instance is not None:
            sale = self.instance.sale
        if sale and sale.status == 'POSTED':
            raise serializers.ValidationError('Нельзя менять проведённую продажу')
        return data


class StockTransferSerializer(OrganizationModelSerializer):
    class Meta:
        model = StockTransfer
        fields = '__all__'
        read_only_fields = ['status']

    def validate(self, data):
        from_warehouse = data.get('from_warehouse')
        to_warehouse = data.get('to_warehouse')
        if self.instance is not None:
            from_warehouse = from_warehouse or self.instance.from_warehouse
            to_warehouse = to_warehouse or self.instance.to_warehouse
        if from_warehouse == to_warehouse:
            raise serializers.ValidationError('Склады должны быть разными')
        return data


class StockTransferItemSerializer(OrganizationModelSerializer):
    class Meta:
        model = StockTransferItem
        fields = '__all__'

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value

    def validate(self, data):
        transfer = data.get('transfer')
        if transfer is None and self.instance is not None:
            transfer = self.instance.transfer
        if transfer and transfer.status == 'POSTED':
            raise serializers.ValidationError('Нельзя менять проведённое перемещение')
        return data


class WriteOffSerializer(OrganizationModelSerializer):
    class Meta:
        model = WriteOff
        fields = '__all__'
        read_only_fields = ['status']


class WriteOffItemSerializer(OrganizationModelSerializer):
    class Meta:
        model = WriteOffItem
        fields = '__all__'
        read_only_fields = ['cost']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value

    def validate(self, data):
        write_off = data.get('write_off')
        if write_off is None and self.instance is not None:
            write_off = self.instance.write_off
        if write_off and write_off.status == 'POSTED':
            raise serializers.ValidationError('Нельзя менять проведённое списание')
        return data


class InventorySerializer(OrganizationModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'
        read_only_fields = ['status']


class InventoryItemSerializer(OrganizationModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'
        read_only_fields = ['system_quantity', 'difference']

    def validate_actual_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError('Фактический остаток не может быть отрицательным')
        return value

    def validate(self, data):
        inventory = data.get('inventory')
        if inventory is None and self.instance is not None:
            inventory = self.instance.inventory
        if inventory and inventory.status == 'POSTED':
            raise serializers.ValidationError('Нельзя менять проведённую инвентаризацию')
        return data


class CashAccountSerializer(OrganizationModelSerializer):
    class Meta:
        model = CashAccount
        fields = '__all__'

    def validate_balance(self, value):
        if value < 0:
            raise serializers.ValidationError('Баланс не может быть отрицательным')
        if self.instance is not None and value != self.instance.balance:
            raise serializers.ValidationError('Баланс изменяется только денежными операциями')
        return value


class FinanceCategorySerializer(OrganizationModelSerializer):
    class Meta:
        model = FinanceCategory
        fields = '__all__'


class CashTransactionSerializer(OrganizationModelSerializer):
    class Meta:
        model = CashTransaction
        fields = '__all__'
        read_only_fields = ['status', 'sale', 'purchase']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Сумма должна быть больше 0')
        return value


class MoneyTransferSerializer(OrganizationModelSerializer):
    class Meta:
        model = MoneyTransfer
        fields = '__all__'

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Сумма должна быть больше 0')
        return value

    def validate(self, data):
        if data.get('from_account') == data.get('to_account'):
            raise serializers.ValidationError('Нельзя переводить деньги на тот же счёт')
        organization = data.get('organization')
        from_account = data.get('from_account')
        to_account = data.get('to_account')
        if organization and from_account and from_account.organization_id != organization.id:
            raise serializers.ValidationError('Счёт отправителя относится к другой организации')
        if organization and to_account and to_account.organization_id != organization.id:
            raise serializers.ValidationError('Счёт получателя относится к другой организации')
        return data


class DebtSerializer(OrganizationModelSerializer):
    remaining = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Debt
        fields = '__all__'
        read_only_fields = ['paid_amount','status','sale','purchase','created_at']

    def validate_amount(self,value):
        if value <= 0:
            raise serializers.ValidationError('????? ?????? ???? ?????? 0')
        return value

    def get_remaining(self,obj):
        return obj.amount-obj.paid_amount

    def get_is_overdue(self,obj):
        return bool(obj.due_date and obj.status != 'PAID' and obj.due_date < timezone.now().date())


class AuditLogSerializer(OrganizationModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'


class NotificationSerializer(OrganizationModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class SaleReturnSerializer(OrganizationModelSerializer):
    class Meta:
        model = SaleReturn
        fields = '__all__'
        read_only_fields = ['status']

class SaleReturnItemSerializer(OrganizationModelSerializer):
    class Meta:
        model = SaleReturnItem
        fields = '__all__'

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Цена не может быть отрицательной')
        return value

    def validate(self, data):
        sale_return = data.get('sale_return')
        if sale_return is None and self.instance is not None:
            sale_return = self.instance.sale_return
        if sale_return and sale_return.status == 'POSTED':
            raise serializers.ValidationError('Нельзя менять проведённый возврат')
        return data

class PurchaseReturnSerializer(OrganizationModelSerializer):
    class Meta:
        model = PurchaseReturn
        fields = '__all__'
        read_only_fields = ['status']

class PurchaseReturnItemSerializer(OrganizationModelSerializer):
    class Meta:
        model = PurchaseReturnItem
        fields = '__all__'

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Цена не может быть отрицательной')
        return value


    def validate(self, data):
        purchase_return = data.get('purchase_return')
        if purchase_return is None and self.instance is not None:
            purchase_return = self.instance.purchase_return
        if purchase_return and purchase_return.status == 'POSTED':
            raise serializers.ValidationError('Нельзя менять проведённый возврат')
        return data
