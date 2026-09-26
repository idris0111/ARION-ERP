from decimal import Decimal

from django.db.models import Count,DecimalField,ExpressionWrapper,F,Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .cache_utils import get_cached,parameterized_key,set_cached
from .models import (CashTransaction,Debt,Employee,Product,Purchase,Sale,SaleItem,
    SalaryPayment,Stock,StockMovement)
from .permissions import IsAccountant
from .tenancy import ORGANIZATION_LOOKUPS,organization_cache_scope,scope_queryset


def report_key(base,request,*values):
    scope = organization_cache_scope(request.user)
    return parameterized_key(base,scope,*values)


def scoped(queryset,request):
    queryset = scope_queryset(queryset,request.user)
    organization = request.GET.get('organization')
    lookup = ORGANIZATION_LOOKUPS.get(queryset.model.__name__)
    if organization and lookup:
        queryset = queryset.filter(**{lookup:organization})
    return queryset


def apply_dates(queryset,request,field='date'):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        queryset = queryset.filter(**{f'{field}__date__gte':date_from})
    if date_to:
        queryset = queryset.filter(**{f'{field}__date__lte':date_to})
    return queryset


class ProfitReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        cache_key = report_key('profit_report',request,request.GET.get('date_from'),request.GET.get('date_to'),request.GET.get('organization'))
        cached = get_cached(cache_key)
        if cached is not None:
            return Response(cached)
        sales = apply_dates(scoped(Sale.objects.filter(status='POSTED'),request),request)
        movements = scoped(StockMovement.objects.filter(document_type='SALE',movement_type='OUT'),request).filter(document_id__in=sales.values('id'))
        revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        expression = ExpressionWrapper(F('quantity')*F('unit_cost'),output_field=DecimalField(max_digits=20,decimal_places=2))
        cost = movements.aggregate(total=Sum(expression))['total'] or 0
        profit = revenue-cost
        data = {'revenue':revenue,'cost':cost,'profit':profit,'margin_percent':round((profit/revenue)*100,2) if revenue else 0}
        set_cached(cache_key,data,60,'profit_report')
        return Response(data)


class ProductProfitReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        data = []
        for product in scoped(Product.objects.all(),request):
            items = scoped(SaleItem.objects.filter(product=product,sale__status='POSTED'),request)
            movements = scoped(StockMovement.objects.filter(product=product,document_type='SALE',movement_type='OUT'),request)
            revenue = items.aggregate(total=Sum('total'))['total'] or 0
            cost = sum((row.quantity*row.unit_cost for row in movements),Decimal('0'))
            data.append({'product':product.name,'revenue':revenue,'cost':cost,'profit':revenue-cost})
        return Response(sorted(data,key=lambda row:row['profit'],reverse=True))


class DailyProfitReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        today = timezone.now().date()
        sales = scoped(Sale.objects.filter(status='POSTED',date__date=today),request)
        movements = scoped(StockMovement.objects.filter(document_type='SALE',movement_type='OUT'),request).filter(document_id__in=sales.values('id'))
        revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        cost = sum((row.quantity*row.unit_cost for row in movements),Decimal('0'))
        return Response({'date':today,'revenue':revenue,'cost':cost,'profit':revenue-cost})


class MonthlyProfitReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        now = timezone.now()
        sales = scoped(Sale.objects.filter(status='POSTED',date__year=now.year,date__month=now.month),request)
        movements = scoped(StockMovement.objects.filter(document_type='SALE',movement_type='OUT'),request).filter(document_id__in=sales.values('id'))
        revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        cost = sum((row.quantity*row.unit_cost for row in movements),Decimal('0'))
        return Response({'year':now.year,'month':now.month,'revenue':revenue,'cost':cost,'profit':revenue-cost})


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        cache_key = report_key('dashboard',request,request.GET.get('organization'))
        cached = get_cached(cache_key)
        if cached is not None:
            return Response(cached)
        today = timezone.now().date()
        sales = scoped(Sale.objects.filter(status='POSTED',date__date=today),request)
        purchases = scoped(Purchase.objects.filter(status='POSTED',date__date=today),request)
        data = {
            'products':scoped(Product.objects.all(),request).count(),
            'employees':scoped(Employee.objects.all(),request).count(),
            'sales_today':sales.count(),'sales_amount_today':sales.aggregate(total=Sum('total_amount'))['total'] or 0,
            'purchases_today':purchases.count(),'purchase_amount_today':purchases.aggregate(total=Sum('total_amount'))['total'] or 0,
            'debts':scoped(Debt.objects.exclude(status='PAID'),request).count(),
        }
        set_cached(cache_key,data,30,'dashboard')
        return Response(data)


class SalesReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        cache_key = report_key('sales_report',request,request.GET.get('date_from'),request.GET.get('date_to'),request.GET.get('organization'),request.GET.get('warehouse'),request.GET.get('employee'),request.GET.get('status'))
        cached = get_cached(cache_key)
        if cached is not None:
            return Response(cached)
        sales = apply_dates(scoped(Sale.objects.filter(status='POSTED'),request),request)
        for name,field in [('warehouse','warehouse_id'),('employee','created_by_id'),('status','status')]:
            if request.GET.get(name):
                sales = sales.filter(**{field:request.GET[name]})
        data = {'sales_count':sales.count(),'total_sales':sales.aggregate(total=Sum('total_amount'))['total'] or 0}
        set_cached(cache_key,data,60,'sales_report')
        return Response(data)


class PurchaseReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        purchases = apply_dates(scoped(Purchase.objects.filter(status='POSTED'),request),request)
        if request.GET.get('warehouse'):
            purchases = purchases.filter(warehouse_id=request.GET['warehouse'])
        return Response({'purchases_count':purchases.count(),'total_purchases':purchases.aggregate(total=Sum('total_amount'))['total'] or 0})


class FinanceReportView(APIView):
    permission_classes = [IsAccountant]
    def get(self,request):
        transactions = apply_dates(scoped(CashTransaction.objects.filter(status='POSTED'),request),request)
        if request.GET.get('account'):
            transactions = transactions.filter(account_id=request.GET['account'])
        income = transactions.filter(transaction_type='INCOME').aggregate(total=Sum('amount'))['total'] or 0
        expense = transactions.filter(transaction_type='EXPENSE').aggregate(total=Sum('amount'))['total'] or 0
        return Response({'income':income,'expense':expense,'balance_difference':income-expense})


class DebtReportView(APIView):
    permission_classes = [IsAccountant]
    def get(self,request):
        debts = scoped(Debt.objects.exclude(status='PAID'),request)
        if request.GET.get('debt_type'):
            debts = debts.filter(debt_type=request.GET['debt_type'])
        total = debts.aggregate(total=Sum('amount'))['total'] or 0
        paid = debts.aggregate(total=Sum('paid_amount'))['total'] or 0
        return Response({'debts_count':debts.count(),'total_debt':total,'paid_amount':paid,'remaining':total-paid})


class StockReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        cache_key = report_key('stock_report',request,request.GET.get('warehouse'),request.GET.get('organization'),request.GET.get('product'))
        cached = get_cached(cache_key)
        if cached is not None:
            return Response(cached)
        stocks = scoped(Stock.objects.select_related('product','warehouse'),request)
        if request.GET.get('warehouse'):
            stocks = stocks.filter(warehouse_id=request.GET['warehouse'])
        if request.GET.get('product'):
            stocks = stocks.filter(product_id=request.GET['product'])
        data = [{'id':row.id,'product':str(row.product),'warehouse':str(row.warehouse),'quantity':row.quantity,'reserved_quantity':row.reserved_quantity,'available_quantity':row.available_quantity,'average_cost':row.average_cost} for row in stocks]
        set_cached(cache_key,data,60,'stock_report')
        return Response(data)


class LowStockReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        stocks = scoped(Stock.objects.select_related('product','warehouse'),request)
        limit = request.GET.get('limit')
        try:
            stocks = stocks.filter(quantity__lte=F('product__min_stock')) if limit is None else stocks.filter(quantity__lte=Decimal(str(limit)))
        except (ArithmeticError,ValueError):
            return Response({'error':'Неверный limit'},status=400)
        return Response([{'product':str(row.product),'warehouse':str(row.warehouse),'quantity':row.quantity} for row in stocks])


class TopProductsReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        cache_key = report_key('top_products',request,request.GET.get('organization'))
        cached = get_cached(cache_key)
        if cached is not None:
            return Response(cached)
        products = list(scoped(SaleItem.objects.filter(sale__status='POSTED'),request).values('product__id','product__name').annotate(sold_quantity=Sum('quantity')).order_by('-sold_quantity')[:10])
        set_cached(cache_key,products,60,'top_products')
        return Response(products)


class MonthlySalesReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        cache_key = report_key('monthly_sales',request,request.GET.get('organization'))
        cached = get_cached(cache_key)
        if cached is not None:
            return Response(cached)
        now = timezone.now()
        sales = scoped(Sale.objects.filter(status='POSTED',date__year=now.year,date__month=now.month),request)
        data = {'year':now.year,'month':now.month,'sales_count':sales.count(),'total_sales':sales.aggregate(total=Sum('total_amount'))['total'] or 0}
        set_cached(cache_key,data,60,'monthly_sales')
        return Response(data)


class StockMovementReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        rows = apply_dates(scoped(StockMovement.objects.select_related('product','warehouse'),request),request,'created_at')
        for name,field in [('warehouse','warehouse_id'),('product','product_id'),('status','movement_type')]:
            if request.GET.get(name):
                rows = rows.filter(**{field:request.GET[name]})
        return Response([{'product':str(row.product),'warehouse':str(row.warehouse),'type':row.movement_type,'quantity':row.quantity,'unit_cost':row.unit_cost,'date':row.created_at} for row in rows])


class SalesByCategoryReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        items = scoped(SaleItem.objects.filter(sale__status='POSTED'),request)
        return Response(list(items.values('product__category__id','product__category__name').annotate(quantity=Sum('quantity'),amount=Sum('total')).order_by('-amount')))


class SalesByEmployeeReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        sales = apply_dates(scoped(Sale.objects.filter(status='POSTED'),request),request)
        return Response(list(sales.values('created_by__id','created_by__username').annotate(sales_count=Count('id'),amount=Sum('total_amount')).order_by('-amount')))


class TopCustomersReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        sales = scoped(Sale.objects.filter(status='POSTED'),request)
        return Response(list(sales.values('customer__id','customer__name').annotate(amount=Sum('total_amount')).order_by('-amount')[:10]))


class SalaryReportView(APIView):
    permission_classes = [IsAccountant]
    def get(self,request):
        salaries = scoped(SalaryPayment.objects.select_related('employee'),request)
        if request.GET.get('status'):
            salaries = salaries.filter(status=request.GET['status'])
        return Response({'count':salaries.count(),'total':salaries.aggregate(total=Sum('amount'))['total'] or 0,'items':[{'employee':str(row.employee),'month':row.month,'amount':row.amount,'status':row.status} for row in salaries]})
