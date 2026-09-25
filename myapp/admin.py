from django.contrib import admin
from .models import (
    Organization,
    Branch,
    OrganizationMember,
    Department,
    Position,
    Employee,
    SalaryPayment,
    Counterparty,
    ContactPerson,
    Category,
    Unit,
    Brand,
    Product,
    PriceType,
    ProductPrice,
    Warehouse,
    Stock,
    StockMovement,
    Purchase,
    PurchaseItem,
    Sale,
    SaleItem,
    StockTransfer,
    StockTransferItem,
    WriteOff,
    WriteOffItem,
    Inventory,
    InventoryItem,
    CashAccount,
    FinanceCategory,
    CashTransaction,
    MoneyTransfer,
    Debt,
    AuditLog,
    SaleReturn,
    SaleReturnItem,
    PurchaseReturn,
    PurchaseReturnItem,
    Notification,
)


admin.site.register(Organization)
admin.site.register(Branch)
admin.site.register(OrganizationMember)
admin.site.register(Department)
admin.site.register(Position)
admin.site.register(Employee)
admin.site.register(SalaryPayment)

admin.site.register(Counterparty)
admin.site.register(ContactPerson)

admin.site.register(Category)
admin.site.register(Unit)
admin.site.register(Brand)
admin.site.register(Product)
admin.site.register(PriceType)
admin.site.register(ProductPrice)

admin.site.register(Warehouse)
admin.site.register(Stock)
admin.site.register(StockMovement)

admin.site.register(Purchase)
admin.site.register(PurchaseItem)

admin.site.register(Sale)
admin.site.register(SaleItem)

admin.site.register(StockTransfer)
admin.site.register(StockTransferItem)

admin.site.register(WriteOff)
admin.site.register(WriteOffItem)

admin.site.register(Inventory)
admin.site.register(InventoryItem)

admin.site.register(CashAccount)
admin.site.register(FinanceCategory)
admin.site.register(CashTransaction)
admin.site.register(MoneyTransfer)

admin.site.register(Debt)
admin.site.register(AuditLog)
admin.site.register(SaleReturn)
admin.site.register(SaleReturnItem)
admin.site.register(PurchaseReturn)
admin.site.register(PurchaseReturnItem)
admin.site.register(Notification)
