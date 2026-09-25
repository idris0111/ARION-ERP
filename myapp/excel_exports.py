from openpyxl import Workbook
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Product,Stock,Sale,Purchase,Debt,Employee,CashTransaction

def export_excel(queryset,filename):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = filename
    fields = [field.name for field in queryset.model._meta.fields]
    sheet.append(fields)
    for obj in queryset:
        row = []
        for field in fields:
            value = getattr(obj,field)
            if value is None:
                value = ''
            elif not isinstance(value,(str,int,float,bool)):
                value = str(value)
            row.append(value)
        sheet.append(row)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    workbook.save(response)
    return response

class ExportProductsExcelView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_excel(Product.objects.all(),'products')

class ExportStocksExcelView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_excel(Stock.objects.all(),'stocks')

class ExportSalesExcelView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_excel(Sale.objects.all(),'sales')

class ExportPurchasesExcelView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_excel(Purchase.objects.all(),'purchases')

class ExportDebtsExcelView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_excel(Debt.objects.all(),'debts')

class ExportEmployeesExcelView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_excel(Employee.objects.all(),'employees')

class ExportCashTransactionsExcelView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        return export_excel(CashTransaction.objects.all(),'cash_transactions')