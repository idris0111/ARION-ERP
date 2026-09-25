import csv
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Product,Stock,Sale,Purchase,Debt,Employee,CashTransaction

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
        return export_csv(Product.objects.all(),'products')

class ExportStocksView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(Stock.objects.all(),'stocks')

class ExportSalesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(Sale.objects.all(),'sales')

class ExportPurchasesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(Purchase.objects.all(),'purchases')

class ExportDebtsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(Debt.objects.all(),'debts')

class ExportEmployeesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(Employee.objects.all(),'employees')

class ExportCashTransactionsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_csv(CashTransaction.objects.all(),'cash_transactions')
