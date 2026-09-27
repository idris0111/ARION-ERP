from rest_framework.exceptions import PermissionDenied

from .models import OrganizationMember


ORGANIZATION_LOOKUPS = {
    'Organization': 'id',
    'Branch': 'organization_id',
    'OrganizationMember': 'organization_id',
    'Department': 'organization_id',
    'Position': 'organization_id',
    'Employee': 'organization_id',
    'SalaryPayment': 'employee__organization_id',
    'Counterparty': 'organization_id',
    'ContactPerson': 'counterparty__organization_id',
    'Category': 'organization_id',
    'Unit': 'organization_id',
    'Brand': 'organization_id',
    'Product': 'organization_id',
    'PriceType': 'organization_id',
    'ProductPrice': 'product__organization_id',
    'Warehouse': 'organization_id',
    'Stock': 'warehouse__organization_id',
    'StockMovement': 'warehouse__organization_id',
    'Purchase': 'organization_id',
    'PurchaseItem': 'purchase__organization_id',
    'Sale': 'organization_id',
    'SaleItem': 'sale__organization_id',
    'StockTransfer': 'organization_id',
    'StockTransferItem': 'transfer__organization_id',
    'WriteOff': 'organization_id',
    'WriteOffItem': 'write_off__organization_id',
    'Inventory': 'organization_id',
    'InventoryItem': 'inventory__organization_id',
    'CashAccount': 'organization_id',
    'FinanceCategory': 'organization_id',
    'CashTransaction': 'organization_id',
    'MoneyTransfer': 'organization_id',
    'Debt': 'organization_id',
    'DebtPayment': 'debt__organization_id',
    'AuditLog': 'organization_id',
    'SaleReturn': 'sale__organization_id',
    'SaleReturnItem': 'sale_return__sale__organization_id',
    'PurchaseReturn': 'purchase__organization_id',
    'PurchaseReturnItem': 'purchase_return__purchase__organization_id',
    'StockReservation': 'organization_id',
    'Account': 'organization_id',
    'JournalEntry': 'organization_id',
    'JournalEntryLine': 'journal_entry__organization_id',
    'DealStage': 'organization_id',
    'Lead': 'organization_id',
    'Deal': 'organization_id',
    'CRMTask': 'organization_id',
    'CRMActivity': 'organization_id',
}


def get_user_organization_ids(user):
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser or getattr(user, 'role', None) == 'SUPER_ADMIN':
        return None
    ids = list(OrganizationMember.objects.filter(user=user,is_active=True).values_list('organization_id',flat=True))
    if not ids and getattr(user, 'role', None) in ('ADMIN','DIRECTOR'):
        return None
    return ids


def scope_queryset(queryset,user,lookup=None):
    ids = get_user_organization_ids(user)
    if ids is None:
        return queryset
    lookup = lookup or ORGANIZATION_LOOKUPS.get(queryset.model.__name__)
    if not lookup:
        return queryset.none()
    return queryset.filter(**{f'{lookup}__in':ids})


def selected_organization_id(request):
    """Validate the company switcher header against the user's memberships."""
    value = request.headers.get('X-Organization-ID') or request.GET.get('organization')
    if not value:
        return None
    try:
        selected = int(value)
    except (TypeError, ValueError):
        raise PermissionDenied('Некорректная организация')
    allowed = get_user_organization_ids(request.user)
    if allowed is not None and selected not in allowed:
        raise PermissionDenied('Нет доступа к организации')
    return selected


def get_object_organization_id(obj):
    if obj is None:
        return None
    if hasattr(obj,'organization_id'):
        return obj.organization_id
    model_name = obj.__class__.__name__
    lookup = ORGANIZATION_LOOKUPS.get(model_name)
    if not lookup:
        return None
    value = obj
    for part in lookup.replace('_id','').split('__'):
        value = getattr(value,part,None)
        if value is None:
            return None
    return getattr(value,'pk',value)


def ensure_organization_access(user,*objects):
    ids = get_user_organization_ids(user)
    if ids is None:
        return
    for obj in objects:
        organization_id = get_object_organization_id(obj)
        if organization_id is not None and organization_id not in ids:
            raise PermissionDenied('Объект относится к другой организации')


def organization_cache_scope(user):
    ids = get_user_organization_ids(user)
    if ids is None:
        return None
    return 'org-' + '-'.join(str(value) for value in sorted(ids))


class OrganizationScopedMixin:
    organization_lookup = None

    def get_queryset(self):
        queryset = scope_queryset(super().get_queryset(),self.request.user,self.organization_lookup)
        selected = selected_organization_id(self.request)
        lookup = self.organization_lookup or ORGANIZATION_LOOKUPS.get(queryset.model.__name__)
        if selected is not None and lookup:
            queryset = queryset.filter(**{lookup:selected})
        return queryset

    def perform_create(self,serializer):
        model = serializer.Meta.model
        if any(field.name == 'created_by' for field in model._meta.fields):
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
