from django.db.models import Q
from rest_framework import generics, permissions, viewsets

from apps.accounts.models import User

from decimal import Decimal

from apps.ai_services.pricing import estimate_price

from .models import Order, ProduceListing
from .serializers import OrderSerializer, ProduceListingSerializer


class ProduceListingViewSet(viewsets.ModelViewSet):
    serializer_class = ProduceListingSerializer
    filterset_fields = ["crop", "country", "season", "status"]
    search_fields = ["crop", "variety", "location"]
    ordering_fields = ["unit_price", "created_at", "quantity_kg"]

    def get_queryset(self):
        qs = ProduceListing.objects.filter(status=ProduceListing.Status.ACTIVE)
        if self.request.user.is_authenticated and self.request.user.role in (
            User.Role.FARMER,
            User.Role.VENDOR,
        ):
            if self.action in ("update", "partial_update", "destroy"):
                return ProduceListing.objects.filter(seller=self.request.user)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        crop = data.get("crop", "")
        qty = float(data.get("quantity_kg", 100))
        season = data.get("season") or "long_rains"
        ai_price = None
        if crop:
            est = estimate_price(crop, user.country, qty, season)
            ai_price = Decimal(str(est["unit_price"]))
        serializer.save(seller=user, country=user.country, ai_suggested_price=ai_price)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.BUYER:
            return Order.objects.filter(buyer=user)
        if user.role in (User.Role.FARMER, User.Role.VENDOR):
            return Order.objects.filter(listing__seller=user)
        if user.role == User.Role.ADMIN or user.is_staff:
            return Order.objects.all()
        return Order.objects.none()

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.BUYER:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only buyers can place orders.")
        order = serializer.save()
        order.listing.status = ProduceListing.Status.RESERVED
        order.listing.save(update_fields=["status"])
        from apps.notifications.services import notify_order_placed

        notify_order_placed(order)
