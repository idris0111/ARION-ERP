from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Account,JournalEntry,JournalEntryLine,StockMovement


DEFAULT_ACCOUNTS = {
    '1010':('Cash','ASSET'),
    '1020':('Bank','ASSET'),
    '1200':('Accounts Receivable','ASSET'),
    '1300':('Inventory','ASSET'),
    '2000':('Accounts Payable','LIABILITY'),
    '4000':('Revenue','REVENUE'),
    '5000':('Cost of Goods Sold','EXPENSE'),
    '6000':('Expenses','EXPENSE'),
    '6100':('Salary Expense','EXPENSE'),
}


def get_account(organization,code):
    name,account_type = DEFAULT_ACCOUNTS[code]
    account,_ = Account.objects.get_or_create(organization=organization,code=code,defaults={'name':name,'account_type':account_type})
    return account


def get_cash_ledger(cash_account):
    code = f'CASH-{cash_account.pk}'
    account,_ = Account.objects.get_or_create(
        organization=cash_account.organization,code=code,
        defaults={'name':cash_account.name,'account_type':'ASSET'},
    )
    return account


def create_entry(organization,description,document_type,document_id,lines,created_by=None,date=None):
    debit = sum((Decimal(str(line.get('debit',0))) for line in lines),Decimal('0'))
    credit = sum((Decimal(str(line.get('credit',0))) for line in lines),Decimal('0'))
    if debit <= 0 or debit != credit:
        raise ValidationError(f'Проводка не сбалансирована: дебет {debit}, кредит {credit}')
    entry = JournalEntry.objects.create(
        organization=organization,date=date or timezone.now(),description=description,
        document_type=document_type,document_id=document_id,status='POSTED',created_by=created_by,
    )
    JournalEntryLine.objects.bulk_create([
        JournalEntryLine(journal_entry=entry,account=line['account'],debit=line.get('debit',0),credit=line.get('credit',0))
        for line in lines if Decimal(str(line.get('debit',0))) or Decimal(str(line.get('credit',0)))
    ])
    return entry


def cancel_entries(document_type,document_id):
    JournalEntry.objects.filter(document_type=document_type,document_id=document_id,status='POSTED').update(status='CANCELLED')


def post_sale_entry(sale):
    if sale.total_amount <= 0:
        return None
    lines = [{'account':get_account(sale.organization,'4000'),'credit':sale.total_amount}]
    if sale.paid_amount:
        lines.append({'account':get_cash_ledger(sale.cash_account),'debit':sale.paid_amount})
    remaining = sale.total_amount-sale.paid_amount
    if remaining:
        lines.append({'account':get_account(sale.organization,'1200'),'debit':remaining})
    movements = StockMovement.objects.filter(document_type='SALE',document_id=sale.pk,movement_type='OUT')
    cost = sum((movement.quantity*movement.unit_cost for movement in movements),Decimal('0'))
    if cost:
        lines.extend([
            {'account':get_account(sale.organization,'5000'),'debit':cost},
            {'account':get_account(sale.organization,'1300'),'credit':cost},
        ])
    return create_entry(sale.organization,f'Продажа №{sale.number}','SALE',sale.pk,lines,sale.created_by,sale.date)


def post_purchase_entry(purchase):
    if purchase.total_amount <= 0:
        return None
    lines = [{'account':get_account(purchase.organization,'1300'),'debit':purchase.total_amount}]
    if purchase.paid_amount:
        lines.append({'account':get_cash_ledger(purchase.cash_account),'credit':purchase.paid_amount})
    remaining = purchase.total_amount-purchase.paid_amount
    if remaining:
        lines.append({'account':get_account(purchase.organization,'2000'),'credit':remaining})
    return create_entry(purchase.organization,f'Закупка №{purchase.number}','PURCHASE',purchase.pk,lines,purchase.created_by,purchase.date)


def post_salary_entry(salary,user):
    return create_entry(salary.employee.organization,f'Зарплата {salary.employee}','SALARY',salary.pk,[
        {'account':get_account(salary.employee.organization,'6100'),'debit':salary.amount},
        {'account':get_cash_ledger(salary.cash_account),'credit':salary.amount},
    ],user)


def post_debt_payment_entry(payment,user):
    debt = payment.debt
    if debt.debt_type == 'CUSTOMER':
        lines = [
            {'account':get_cash_ledger(payment.cash_account),'debit':payment.amount},
            {'account':get_account(debt.organization,'1200'),'credit':payment.amount},
        ]
    else:
        lines = [
            {'account':get_account(debt.organization,'2000'),'debit':payment.amount},
            {'account':get_cash_ledger(payment.cash_account),'credit':payment.amount},
        ]
    return create_entry(debt.organization,f'Оплата долга №{debt.pk}','DEBT_PAYMENT',payment.pk,lines,user)


def post_cash_transaction_entry(cash_transaction,user):
    cash = get_cash_ledger(cash_transaction.account)
    if cash_transaction.transaction_type == 'INCOME':
        lines = [{'account':cash,'debit':cash_transaction.amount},{'account':get_account(cash_transaction.organization,'4000'),'credit':cash_transaction.amount}]
    else:
        lines = [{'account':get_account(cash_transaction.organization,'6000'),'debit':cash_transaction.amount},{'account':cash,'credit':cash_transaction.amount}]
    return create_entry(cash_transaction.organization,cash_transaction.purpose or cash_transaction.number,'CASH_TRANSACTION',cash_transaction.pk,lines,user,cash_transaction.date)


def post_transfer_entry(transfer,user):
    return create_entry(transfer.organization,f'Перевод №{transfer.pk}','MONEY_TRANSFER',transfer.pk,[
        {'account':get_cash_ledger(transfer.to_account),'debit':transfer.amount},
        {'account':get_cash_ledger(transfer.from_account),'credit':transfer.amount},
    ],user,transfer.date)


def entry_totals(entry):
    totals = entry.lines.aggregate(debit=Sum('debit'),credit=Sum('credit'))
    return totals['debit'] or 0,totals['credit'] or 0
