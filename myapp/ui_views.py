from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import never_cache


@never_cache
def erp_ui(request, pk=None, subpath=None):
    """Serve the built React app while keeping the REST API under /api/."""
    index = settings.BASE_DIR / 'frontend' / 'dist' / 'index.html'
    if not index.is_file():
        return HttpResponse(
            'Frontend is not built. Run npm install and npm run build in frontend/.',
            content_type='text/plain', status=503,
        )
    return HttpResponse(index.read_text(encoding='utf-8'), content_type='text/html')
