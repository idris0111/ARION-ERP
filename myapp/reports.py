from django.db.models import Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Product,Stock,StockMovement,Sale,SaleItem,Purchase,CashTransaction,Debt,Employee
from .permissions import IsAccountant
from django.db.models import Sum,F,DecimalField,ExpressionWrapper

class ProfitReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        sales = Sale.objects.filter(status='POSTED')
        movements = StockMovement.objects.filter(document_type='SALE',movement_type='OUT')
        if date_from:
            sales = sales.filter(created_at__date__gte=date_from)
            movements = movements.filter(created_at__date__gte=date_from)
        if date_to:
            sales = sales.filter(created_at__date__lte=date_to)
            movements = movements.filter(created_at__date__lte=date_to)
        revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        cost_expression = ExpressionWrapper(F('quantity')*F('unit_cost'),output_field=DecimalField(max_digits=20,decimal_places=2))
        cost = movements.aggregate(total=Sum(cost_expression))['total'] or 0
        profit = revenue-cost
        margin = 0
        if revenue:
            margin = round((profit/revenue)*100,2)
        return Response({'revenue':revenue,'cost':cost,'profit':profit,'margin_percent':margin})

class ProductProfitReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        products = Product.objects.all()
        data = []
        for product in products:
            sale_items = SaleItem.objects.filter(product=product,sale__status='POSTED')
            movements = StockMovement.objects.filter(product=product,document_type='SALE',movement_type='OUT')
            revenue = sale_items.aggregate(total=Sum('total'))['total'] or 0
            cost = 0
            for movement in movements:
                cost += movement.quantity*movement.unit_cost
            profit = revenue-cost
            data.append({'product':product.name,'revenue':revenue,'cost':cost,'profit':profit})
        data = sorted(data,key=lambda x:x['profit'],reverse=True)
        return Response(data)

class DailyProfitReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        today = timezone.now().date()
        sales = Sale.objects.filter(status='POSTED',created_at__date=today)
        movements = StockMovement.objects.filter(document_type='SALE',movement_type='OUT',created_at__date=today)
        revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        cost = 0
        for movement in movements:
            cost += movement.quantity*movement.unit_cost
        profit = revenue-cost
        return Response({'date':today,'revenue':revenue,'cost':cost,'profit':profit})


class MonthlyProfitReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        now = timezone.now()
        sales = Sale.objects.filter(status='POSTED',created_at__year=now.year,created_at__month=now.month)
        movements = StockMovement.objects.filter(document_type='SALE',movement_type='OUT',created_at__year=now.year,created_at__month=now.month)
        revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        cost = 0
        for movement in movements:
            cost += movement.quantity*movement.unit_cost
        profit = revenue-cost
        return Response({'year':now.year,'month':now.month,'revenue':revenue,'cost':cost,'profit':profit})

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        today = timezone.now().date()
        sales = Sale.objects.filter(status='POSTED',created_at__date=today)
        purchases = Purchase.objects.filter(status='POSTED',created_at__date=today)
        return Response({
            'products':Product.objects.count(),
            'employees':Employee.objects.count(),
            'sales_today':sales.count(),
            'sales_amount_today':sales.aggregate(total=Sum('total_amount'))['total'] or 0,
            'purchases_today':purchases.count(),
            'purchase_amount_today':purchases.aggregate(total=Sum('total_amount'))['total'] or 0,
            'debts':Debt.objects.exclude(status='PAID').count(),
        })

class SalesReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        sales = Sale.objects.filter(status='POSTED')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            sales = sales.filter(created_at__date__gte=date_from)
        if date_to:
            sales = sales.filter(created_at__date__lte=date_to)
        return Response({
            'sales_count':sales.count(),
            'total_sales':sales.aggregate(total=Sum('total_amount'))['total'] or 0,
        })

class PurchaseReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        purchases = Purchase.objects.filter(status='POSTED')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            purchases = purchases.filter(created_at__date__gte=date_from)
        if date_to:
            purchases = purchases.filter(created_at__date__lte=date_to)
        return Response({
            'purchases_count':purchases.count(),
            'total_purchases':purchases.aggregate(total=Sum('total_amount'))['total'] or 0,
        })

class FinanceReportView(APIView):
    permission_classes = [IsAccountant]
    def get(self,request):
        transactions = CashTransaction.objects.filter(status='POSTED')
        income = transactions.filter(transaction_type='INCOME').aggregate(total=Sum('amount'))['total'] or 0
        expense = transactions.filter(transaction_type='EXPENSE').aggregate(total=Sum('amount'))['total'] or 0
        return Response({'income':income,'expense':expense,'balance_difference':income-expense})

class DebtReportView(APIView):
    permission_classes = [IsAccountant]
    def get(self,request):
        debts = Debt.objects.exclude(status='PAID')
        total = debts.aggregate(total=Sum('amount'))['total'] or 0
        paid = debts.aggregate(total=Sum('paid_amount'))['total'] or 0
        return Response({'debts_count':debts.count(),'total_debt':total,'paid_amount':paid,'remaining':total-paid})

class StockReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        stocks = Stock.objects.select_related('product','warehouse')
        warehouse = request.GET.get('warehouse')
        if warehouse:
            stocks = stocks.filter(warehouse_id=warehouse)
        data = []
        for stock in stocks:
            data.append({'id':stock.id,'product':str(stock.product),'warehouse':str(stock.warehouse),'quantity':stock.quantity,'average_cost':stock.average_cost})
        return Response(data)

class LowStockReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        try:
            limit = int(request.GET.get('limit',5))
        except:
            limit = 5
        stocks = Stock.objects.filter(quantity__lte=limit).select_related('product','warehouse')
        data = []
        for stock in stocks:
            data.append({'product':str(stock.product),'warehouse':str(stock.warehouse),'quantity':stock.quantity})
        return Response(data)

class TopProductsReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        products = SaleItem.objects.filter(sale__status='POSTED').values('product__id','product__name').annotate(sold_quantity=Sum('quantity')).order_by('-sold_quantity')[:10]
        return Response(products)

class MonthlySalesReportView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        now = timezone.now()
        sales = Sale.objects.filter(status='POSTED',created_at__year=now.year,created_at__month=now.month)
        total = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        return Response({'year':now.year,'month':now.month,'sales_count':sales.count(),'total_sales':total})