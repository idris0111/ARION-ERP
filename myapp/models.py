from django.db import models
from django.conf import settings


class Organization(models.Model):
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=500, blank=True)
    inn = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    currency = models.CharField(max_length=10, default='TJS')
    logo = models.ImageField(upload_to='organizations/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Branch(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    ROLE_CHOICES = [
        ('OWNER', 'Владелец'),
        ('ADMIN', 'Администратор'),
        ('MANAGER', 'Менеджер'),
        ('ACCOUNTANT', 'Бухгалтер'),
        ('WAREHOUSE', 'Кладовщик'),
        ('CASHIER', 'Кассир'),
        ('EMPLOYEE', 'Сотрудник'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organization_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EMPLOYEE')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.organization}'


class Department(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Position(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='positions')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    STATUS_CHOICES = [
        ('WORKING', 'Работает'),
        ('VACATION', 'В отпуске'),
        ('FIRED', 'Уволен'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='employees')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hire_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WORKING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class SalaryPayment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    month = models.DateField()
    comment = models.TextField(blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.employee} - {self.amount}'


class Counterparty(models.Model):
    TYPE_CHOICES = [
        ('CUSTOMER', 'Клиент'),
        ('SUPPLIER', 'Поставщик'),
        ('BOTH', 'Клиент и поставщик'),
    ]

    PERSON_CHOICES = [
        ('INDIVIDUAL', 'Физическое лицо'),
        ('COMPANY', 'Компания'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='counterparties')
    name = models.CharField(max_length=255)
    counterparty_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    person_type = models.CharField(max_length=20, choices=PERSON_CHOICES, default='COMPANY')
    inn = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ContactPerson(models.Model):
    counterparty = models.ForeignKey(Counterparty, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Unit(models.Model):
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=20)

    def __str__(self):
        return self.short_name


class Brand(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Product(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    min_stock = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_service = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PriceType(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='price_types')
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class ProductPrice(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    price_type = models.ForeignKey(PriceType, on_delete=models.CASCADE, related_name='product_prices')
    price = models.DecimalField(max_digits=14, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.product} - {self.price}'


class Warehouse(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='warehouses')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='warehouses')
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True)
    responsible = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='warehouses')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    average_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['warehouse', 'product']

    def __str__(self):
        return f'{self.product} - {self.quantity}'


class StockMovement(models.Model):
    TYPE_CHOICES = [
        ('IN', 'Приход'),
        ('OUT', 'Расход'),
        ('TRANSFER_IN', 'Перемещение приход'),
        ('TRANSFER_OUT', 'Перемещение расход'),
        ('WRITE_OFF', 'Списание'),
        ('INVENTORY', 'Инвентаризация'),
    ]

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='movements')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    document_type = models.CharField(max_length=100, blank=True)
    document_id = models.PositiveIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.product} - {self.movement_type}'


class Purchase(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Черновик'),
        ('POSTED', 'Проведен'),
        ('CANCELLED', 'Отменен'),
    ]

    PAYMENT_CHOICES = [
        ('UNPAID', 'Не оплачено'),
        ('PARTIAL', 'Частично'),
        ('PAID', 'Оплачено'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='purchases')
    supplier = models.ForeignKey(Counterparty, on_delete=models.PROTECT, related_name='purchases')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='purchases')
    cash_account = models.ForeignKey('CashAccount', on_delete=models.PROTECT, null=True, blank=True)
    number = models.CharField(max_length=100, unique=True)
    date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='UNPAID')
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_purchases')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_items')
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return str(self.product)


class Sale(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Черновик'),
        ('POSTED', 'Проведен'),
        ('CANCELLED', 'Отменен'),
    ]

    PAYMENT_CHOICES = [
        ('UNPAID', 'Не оплачено'),
        ('PARTIAL', 'Частично'),
        ('PAID', 'Оплачено'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='sales')
    customer = models.ForeignKey(Counterparty, on_delete=models.PROTECT, related_name='sales')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='sales')
    cash_account = models.ForeignKey('CashAccount', on_delete=models.PROTECT, null=True, blank=True)
    number = models.CharField(max_length=100, unique=True)
    date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='UNPAID')
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_sales')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return str(self.product)


class StockTransfer(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Черновик'),
        ('POSTED', 'Проведен'),
        ('CANCELLED', 'Отменен'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='stock_transfers')
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='outgoing_transfers')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='incoming_transfers')
    number = models.CharField(max_length=100, unique=True)
    date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_stock_transfers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number


class StockTransferItem(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)

    def __str__(self):
        return str(self.product)


class WriteOff(models.Model):
    REASON_CHOICES = [
        ('DAMAGED', 'Поврежден'),
        ('EXPIRED', 'Просрочен'),
        ('LOST', 'Потерян'),
        ('OTHER', 'Другое'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Черновик'),
        ('POSTED', 'Проведен'),
        ('CANCELLED', 'Отменен'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='write_offs')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='write_offs')
    number = models.CharField(max_length=100, unique=True)
    date = models.DateTimeField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_write_offs')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number


class WriteOffItem(models.Model):
    write_off = models.ForeignKey(WriteOff, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return str(self.product)


class Inventory(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Черновик'),
        ('POSTED', 'Проведен'),
        ('CANCELLED', 'Отменен'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='inventories')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='inventories')
    number = models.CharField(max_length=100, unique=True)
    date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_inventories')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number


class InventoryItem(models.Model):
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    system_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    actual_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    difference = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    def __str__(self):
        return str(self.product)


class CashAccount(models.Model):
    TYPE_CHOICES = [
        ('CASH', 'Касса'),
        ('BANK', 'Банк'),
        ('CARD', 'Карта'),
        ('OTHER', 'Другое'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='cash_accounts')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_accounts')
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    currency = models.CharField(max_length=10, default='TJS')
    balance = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class FinanceCategory(models.Model):
    TYPE_CHOICES = [
        ('INCOME', 'Доход'),
        ('EXPENSE', 'Расход'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='finance_categories')
    name = models.CharField(max_length=255)
    category_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    def __str__(self):
        return self.name


class CashTransaction(models.Model):
    TYPE_CHOICES = [
        ('INCOME', 'Приход'),
        ('EXPENSE', 'Расход'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Черновик'),
        ('POSTED', 'Проведен'),
        ('CANCELLED', 'Отменен'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='cash_transactions')
    account = models.ForeignKey(CashAccount, on_delete=models.PROTECT, related_name='transactions')
    category = models.ForeignKey(FinanceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    counterparty = models.ForeignKey(Counterparty, on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_transactions')
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True, blank=True)
    purchase = models.ForeignKey(Purchase, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    number = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    purpose = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_cash_transactions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.number} - {self.amount}'


class MoneyTransfer(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='money_transfers')
    from_account = models.ForeignKey(CashAccount, on_delete=models.PROTECT, related_name='outgoing_transfers')
    to_account = models.ForeignKey(CashAccount, on_delete=models.PROTECT, related_name='incoming_transfers')
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    date = models.DateTimeField()
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_money_transfers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.from_account} -> {self.to_account}'


class Debt(models.Model):
    DEBT_TYPES = [
        ('CUSTOMER', 'Customer'),
        ('SUPPLIER', 'Supplier'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Открыт'),
        ('PARTIAL', 'Частично'),
        ('PAID', 'Оплачен'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='debts')
    counterparty = models.ForeignKey(Counterparty, on_delete=models.PROTECT, related_name='debts')
    debt_type = models.CharField(max_length=20, choices=DEBT_TYPES)
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True, blank=True)
    purchase = models.ForeignKey(Purchase, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.counterparty} - {self.amount}'


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Создание'),
        ('UPDATE', 'Изменение'),
        ('DELETE', 'Удаление'),
        ('LOGIN', 'Вход'),
        ('LOGOUT', 'Выход'),
        ('POST', 'Проведение'),
        ('CANCEL', 'Отмена'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.action}'


class SaleReturn(models.Model):
    STATUS_CHOICES = [('DRAFT','Draft'),('POSTED','Posted')]
    number = models.CharField(max_length=50,unique=True)
    sale = models.ForeignKey(Sale,on_delete=models.CASCADE,related_name='returns')
    warehouse = models.ForeignKey(Warehouse,on_delete=models.CASCADE)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='DRAFT')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.number

class SaleReturnItem(models.Model):
    sale_return = models.ForeignKey(SaleReturn,on_delete=models.CASCADE,related_name='items')
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12,decimal_places=2)
    price = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    def __str__(self):
        return str(self.product)

class PurchaseReturn(models.Model):
    STATUS_CHOICES = [('DRAFT','Draft'),('POSTED','Posted')]
    number = models.CharField(max_length=50,unique=True)
    purchase = models.ForeignKey(Purchase,on_delete=models.CASCADE,related_name='returns')
    warehouse = models.ForeignKey(Warehouse,on_delete=models.CASCADE)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='DRAFT')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.number

class PurchaseReturnItem(models.Model):
    purchase_return = models.ForeignKey(PurchaseReturn,on_delete=models.CASCADE,related_name='items')
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12,decimal_places=2)
    price = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    def __str__(self):
        return str(self.product)
