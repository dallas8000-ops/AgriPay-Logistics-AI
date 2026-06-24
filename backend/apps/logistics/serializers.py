from rest_framework import serializers

from .models import Delivery, DeliveryTrackingEvent, ProofOfDelivery


class TrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTrackingEvent
        fields = ("id", "status", "latitude", "longitude", "note", "timestamp")


class ProofOfDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofOfDelivery
        fields = (
            "id",
            "delivery",
            "photo",
            "recipient_name",
            "recipient_phone",
            "signature_data",
            "otp_verified",
            "notes",
            "submitted_at",
        )
        read_only_fields = ("submitted_at",)


class DeliverySerializer(serializers.ModelSerializer):
    tracking_events = TrackingEventSerializer(many=True, read_only=True)
    proof = ProofOfDeliverySerializer(read_only=True)
    driver_name = serializers.CharField(source="driver.username", read_only=True)
    order_id = serializers.IntegerField(source="order.id", read_only=True)

    class Meta:
        model = Delivery
        fields = (
            "id",
            "order",
            "order_id",
            "driver",
            "driver_name",
            "status",
            "pickup_location",
            "dropoff_location",
            "estimated_arrival",
            "actual_delivery",
            "current_latitude",
            "current_longitude",
            "route_summary",
            "tracking_events",
            "proof",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "route_summary")
