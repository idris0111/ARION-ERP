import csv
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Product,Stock,Sale,Purchase,Debt,Employee,CashTransaction
from .tenancy import scope_queryset

def export_csv(queryset,filename):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    writer = csv.writer(response)
    fields = [field.name for field in queryset.model._meta.fields]
    writer.writerow(fields)
    for obj in queryset:
        writer.writerow([getattr(obj,field) for field in fields])
    return response

class ExportProductsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(scope_queryset(Product.objects.all(),request.user),'products')

class ExportStocksView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(scope_queryset(Stock.objects.all(),request.user),'stocks')

class ExportSalesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(scope_queryset(Sale.objects.all(),request.user),'sales')

class ExportPurchasesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(scope_queryset(Purchase.objects.all(),request.user),'purchases')

class ExportDebtsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(scope_queryset(Debt.objects.all(),request.user),'debts')

class ExportEmployeesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(scope_queryset(Employee.objects.all(),request.user),'employees')

class ExportCashTransactionsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(scope_queryset(CashTransaction.objects.all(),request.user),'cash_transactions')
