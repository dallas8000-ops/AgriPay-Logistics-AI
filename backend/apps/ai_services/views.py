from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import BuyerProfile
from apps.logistics.models import Delivery

from .pricing import buyer_reliability_score, estimate_price, route_summary


class PriceEstimateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        crop = request.data.get("crop", "")
        country = request.data.get("country", request.user.country)
        quantity = request.data.get("quantity_kg", 100)
        season = request.data.get("season", "long_rains")
        if not crop:
            return Response({"detail": "crop is required"}, status=400)
        result = estimate_price(crop, country, float(quantity), season)
        result["method"] = "rule_based"
        result["method_note"] = (
            "Static crop price tables with season multipliers — not live market feeds or ML."
        )
        return Response(result)


class BuyerScoreView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, buyer_id=None):
        target_id = buyer_id or request.user.id
        try:
            profile = BuyerProfile.objects.get(user_id=target_id)
        except BuyerProfile.DoesNotExist:
            return Response({"detail": "Buyer profile not found"}, status=404)
        return Response(buyer_reliability_score(profile))


class RouteSummaryView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        pickup = request.data.get("pickup", "")
        dropoff = request.data.get("dropoff", "")
        delivery_id = request.data.get("delivery_id")
        distance = request.data.get("distance_km")
        if delivery_id:
            try:
                d = Delivery.objects.get(id=delivery_id)
                pickup = d.pickup_location
                dropoff = d.dropoff_location
            except Delivery.DoesNotExist:
                return Response({"detail": "Delivery not found"}, status=404)
        if not pickup or not dropoff:
            return Response({"detail": "pickup and dropoff required"}, status=400)
        result = route_summary(pickup, dropoff, float(distance) if distance else None)
        if delivery_id:
            Delivery.objects.filter(id=delivery_id).update(route_summary=result["summary"])
        return Response(result)
