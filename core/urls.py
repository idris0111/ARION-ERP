"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from myapp.ui_views import erp_ui

schema_view = get_schema_view(
    openapi.Info(
        title='NEXORA ERP API',
        default_version='v1',
        description='ERP backend API',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', erp_ui, name='erp-dashboard'),
    path('products/', erp_ui, name='erp-products'),
    path('products/new/', erp_ui, name='erp-product-create'),
    path('products/<int:pk>/', erp_ui, name='erp-product-detail'),
    path('products/<int:pk>/edit/', erp_ui, name='erp-product-edit'),
    path('sales/', erp_ui, name='erp-sales'),
    path('sales/new/', erp_ui, name='erp-sale-create'),
    path('sales/<int:pk>/', erp_ui, name='erp-sale-detail'),
    path('m/<path:subpath>', erp_ui, name='erp-modules'),
    path('inventory/', erp_ui, name='erp-inventory'),
    path('finance/', erp_ui, name='erp-finance'),
    path('crm/', erp_ui, name='erp-crm'),
    path('pos/', erp_ui, name='erp-pos'),
    path('reports/', erp_ui, name='erp-reports'),
    path('settings/', erp_ui, name='erp-settings'),
    path('404/', erp_ui, name='erp-not-found'),
    path('admin/', admin.site.urls),
    path('api/account/', include('accounts.urls')),
    path('api/', include('myapp.urls')),
    re_path(
        r'^swagger/$',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui'
    ),
    re_path(
        r'^redoc/$',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc'
    ),
]
