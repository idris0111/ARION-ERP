from rest_framework import serializers
from .models import (Organization, SaleReturn,SaleReturnItem,PurchaseReturn,PurchaseReturnItem,Branch,OrganizationMember,Department,Position,Employee,SalaryPayment,
    Counterparty,ContactPerson,Category,Unit,Brand,Product,PriceType,ProductPrice,Warehouse,Stock,StockMovement,Purchase,PurchaseItem,Sale,
    SaleItem,StockTransfer,StockTransferItem,WriteOff,WriteOffItem,Inventory,InventoryItem,CashAccount,FinanceCategory,CashTransaction,MoneyTransfer,Debt,AuditLog,Notification,
)


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'


class OrganizationMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMember
        fields = '__all__'


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = '__all__'


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'


class SalaryPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryPayment
        fields = '__all__'


class CounterpartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Counterparty
        fields = '__all__'


class ContactPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactPerson
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class PriceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceType
        fields = '__all__'


class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = '__all__'


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = '__all__'


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = '__all__'


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = '__all__'

    def validate_paid_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Оплата не может быть отрицательной')
        return value


class PurchaseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
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
        purchase = data.get('purchase')
        if purchase is None and self.instance is not None:
            purchase = self.instance.purchase
        if purchase and purchase.status == 'POSTED':
            raise serializers.ValidationError('Нельзя менять проведённую закупку')
        return data


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'

    def validate_paid_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Оплата не может быть отрицательной')
        return value


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
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
        sale = data.get('sale')
        if sale is None and self.instance is not None:
            sale = self.instance.sale
        if sale and sale.status == 'POSTED':
            raise serializers.ValidationError('Нельзя менять проведённую продажу')
        return data


class StockTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransfer
        fields = '__all__'

    def validate(self, data):
        from_warehouse = data.get('from_warehouse')
        to_warehouse = data.get('to_warehouse')
        if self.instance is not None:
            from_warehouse = from_warehouse or self.instance.from_warehouse
            to_warehouse = to_warehouse or self.instance.to_warehouse
        if from_warehouse == to_warehouse:
            raise serializers.ValidationError('Склады должны быть разными')
        return data


class StockTransferItemSerializer(serializers.ModelSerializer):
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


class WriteOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = WriteOff
        fields = '__all__'


class WriteOffItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WriteOffItem
        fields = '__all__'

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


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'


class CashAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashAccount
        fields = '__all__'


class FinanceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceCategory
        fields = '__all__'


class CashTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashTransaction
        fields = '__all__'


class MoneyTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoneyTransfer
        fields = '__all__'


class DebtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Debt
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class SaleReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleReturn
        fields = '__all__'

class SaleReturnItemSerializer(serializers.ModelSerializer):
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

class PurchaseReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseReturn
        fields = '__all__'

class PurchaseReturnItemSerializer(serializers.ModelSerializer):
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
