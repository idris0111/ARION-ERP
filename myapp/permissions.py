from rest_framework.permissions import BasePermission


class IsAdminOrDirector(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role in [
            'SUPER_ADMIN',
            'ADMIN',
            'DIRECTOR',
        ]


class IsAccountant(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role in [
            'SUPER_ADMIN',
            'ADMIN',
            'DIRECTOR',
            'CHIEF_ACCOUNTANT',
            'ACCOUNTANT',
        ]


class IsWarehouseWorker(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role in [
            'SUPER_ADMIN',
            'ADMIN',
            'DIRECTOR',
            'WAREHOUSE_MANAGER',
            'STOREKEEPER',
        ]


class IsSalesWorker(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role in [
            'SUPER_ADMIN',
            'ADMIN',
            'DIRECTOR',
            'MANAGER',
            'SALES_MANAGER',
            'CASHIER',
        ]


class IsPurchaseWorker(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role in [
            'SUPER_ADMIN',
            'ADMIN',
            'DIRECTOR',
            'MANAGER',
            'PURCHASE_MANAGER',
        ]


class IsHRWorker(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role in [
            'SUPER_ADMIN',
            'ADMIN',
            'DIRECTOR',
            'HR',
        ]


class IsAuditor(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role in [
            'SUPER_ADMIN',
            'ADMIN',
            'DIRECTOR',
            'AUDITOR',
            'ANALYST',
        ]