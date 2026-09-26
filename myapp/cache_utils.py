from django.core.cache import cache


def get_cached(key):
    try:
        return cache.get(key)
    except Exception:
        return None


def set_cached(key, value, timeout, group=None):
    try:
        cache.set(key, value, timeout)
        if group and key != group:
            registry_key = f'{group}_cache_keys'
            keys = cache.get(registry_key) or []
            if key not in keys:
                keys.append(key)
                cache.set(registry_key, keys, timeout)
    except Exception:
        pass


def delete_cached(*groups):
    try:
        for group in groups:
            registry_key = f'{group}_cache_keys'
            for key in cache.get(registry_key) or []:
                cache.delete(key)
            cache.delete(registry_key)
            cache.delete(group)
    except Exception:
        pass


def parameterized_key(base, *values):
    values = [value for value in values if value not in (None,'')]
    if not values:
        return base
    return f"{base}_{'_'.join(str(value) for value in values)}"


def invalidate_stock_cache():
    delete_cached('stocks', 'dashboard', 'stock_report', 'top_products', 'monthly_sales', 'profit_report')


def invalidate_sales_cache():
    invalidate_stock_cache()
    delete_cached('sales_report')


def invalidate_purchase_cache():
    invalidate_stock_cache()
    delete_cached('purchase_report')
