from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .exchange_rate_service import latest_rates


class ExchangeRatesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(latest_rates())
