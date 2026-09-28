"""Replaceable source of display exchange rates. Stored rates survive provider outages."""
import json
from threading import Lock
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import ExchangeRate

TARGETS = ('USD', 'EUR', 'CNY')
REFRESH_AFTER = timedelta(hours=3)
_last_failed_attempt = None
_refresh_lock = Lock()


def fetch_provider_rates():
    """Return target currency units per TJS from the configured provider."""
    url = settings.EXCHANGE_RATE_PROVIDER_URL
    request = Request(url, headers={'User-Agent': 'NexoraERP/1.0 (exchange rates; backend)', 'Accept': 'application/json'})
    with urlopen(request, timeout=4) as response:
        rows = json.load(response)
    rates = {}
    for row in rows:
        if row.get('base') != 'TJS' or row.get('quote') not in TARGETS:
            continue
        try:
            rate = Decimal(str(row['rate']))
        except (InvalidOperation, KeyError):
            continue
        if rate > 0:
            rates[row['quote']] = rate
    if set(rates) != set(TARGETS):
        raise ValueError('Provider returned incomplete exchange rates')
    return rates


def latest_rates():
    global _last_failed_attempt
    stored = {row.target_currency: row for row in ExchangeRate.objects.filter(base_currency='TJS', target_currency__in=TARGETS)}
    newest = min((row.updated_at for row in stored.values()), default=None)
    stale = newest is None or len(stored) != len(TARGETS) or newest < timezone.now() - REFRESH_AFTER
    retry_allowed = (_last_failed_attempt is None or _last_failed_attempt < timezone.now() - timedelta(minutes=10)) and not cache.get('exchange_rates_failed')
    if stale and retry_allowed and _refresh_lock.acquire(blocking=False):
        try:
            fresh = fetch_provider_rates()
            now = timezone.now()
            for target, rate in fresh.items():
                ExchangeRate.objects.update_or_create(base_currency='TJS', target_currency=target, defaults={'rate': rate, 'updated_at': now})
            stored = {row.target_currency: row for row in ExchangeRate.objects.filter(base_currency='TJS', target_currency__in=TARGETS)}
            newest = now
            stale = False
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            _last_failed_attempt = timezone.now()
            cache.set('exchange_rates_failed', True, 600)
        finally:
            _refresh_lock.release()
    return {'base': 'TJS', 'updated_at': newest, 'rates': {'TJS': 1, **{code: str(row.rate) for code, row in stored.items()}}, 'stale': stale}
