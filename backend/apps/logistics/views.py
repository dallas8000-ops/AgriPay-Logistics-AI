from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.marketplace.models import Order

from .models import Delivery, DeliveryTrackingEvent, ProofOfDelivery
from .serializers import DeliverySerializer, ProofOfDeliverySerializer, TrackingEventSerializer


class DeliveryViewSet(viewsets.ModelViewSet):
    serializer_class = DeliverySerializer
    filterset_fields = ["status"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.DRIVER:
            return Delivery.objects.filter(driver=user)
        if user.role == User.Role.BUYER:
            return Delivery.objects.filter(order__buyer=user)
        if user.role in (User.Role.FARMER, User.Role.VENDOR):
            return Delivery.objects.filter(order__listing__seller=user)
        if user.is_staff or user.role == User.Role.ADMIN:
            return Delivery.objects.all()
        return Delivery.objects.none()

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def available_drivers(self, request):
        drivers = User.objects.filter(role=User.Role.DRIVER, driver_profile__is_available=True)
        data = [
            {
                "id": d.id,
                "username": d.username,
                "vehicle": d.driver_profile.vehicle_type,
                "plate": d.driver_profile.vehicle_plate,
                "capacity_kg": d.driver_profile.capacity_kg,
            }
            for d in drivers
            if hasattr(d, "driver_profile")
        ]
        return Response(data)

    @action(detail=True, methods=["post"])
    def assign_driver(self, request, pk=None):
        delivery = self.get_object()
        driver_id = request.data.get("driver_id")
        if not driver_id:
            return Response({"detail": "driver_id required"}, status=400)
        try:
            driver = User.objects.get(id=driver_id, role=User.Role.DRIVER)
        except User.DoesNotExist:
            return Response({"detail": "Driver not found"}, status=404)
        delivery.driver = driver
        delivery.status = Delivery.Status.ASSIGNED
        delivery.save()
        delivery.order.status = Order.Status.ASSIGNED
        delivery.order.save(update_fields=["status"])
        DeliveryTrackingEvent.objects.create(
            delivery=delivery, status="assigned", note=f"Assigned to {driver.username}"
        )
        from apps.notifications.services import notify_driver_assigned

        notify_driver_assigned(delivery, driver)
        return Response(DeliverySerializer(delivery).data)

    @action(detail=True, methods=["post"])
    def update_location(self, request, pk=None):
        delivery = self.get_object()
        lat = request.data.get("latitude")
        lng = request.data.get("longitude")
        status_val = request.data.get("status", delivery.status)
        delivery.current_latitude = lat
        delivery.current_longitude = lng
        delivery.status = status_val
        if status_val == Delivery.Status.IN_TRANSIT:
            delivery.order.status = Order.Status.IN_TRANSIT
            delivery.order.save(update_fields=["status"])
            from apps.notifications.services import notify_delivery_status

            notify_delivery_status(delivery, status_val)
        delivery.save()
        DeliveryTrackingEvent.objects.create(
            delivery=delivery,
            status=status_val,
            latitude=lat,
            longitude=lng,
            note=request.data.get("note", ""),
        )
        return Response(DeliverySerializer(delivery).data)

    @action(detail=True, methods=["post"])
    def submit_proof(self, request, pk=None):
        delivery = self.get_object()
        if hasattr(delivery, "proof"):
            return Response({"detail": "Proof already submitted"}, status=400)
        serializer = ProofOfDeliverySerializer(data={**request.data, "delivery": delivery.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(delivery=delivery)
        delivery.status = Delivery.Status.DELIVERED
        delivery.actual_delivery = timezone.now()
        delivery.save()
        delivery.order.status = Order.Status.DELIVERED
        delivery.order.save(update_fields=["status"])
        DeliveryTrackingEvent.objects.create(delivery=delivery, status="delivered", note="Proof of delivery submitted")
        from apps.notifications.services import notify_delivery_completed

        notify_delivery_completed(delivery)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
