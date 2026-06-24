from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "payer",
            "amount",
            "currency",
            "provider",
            "status",
            "phone_number",
            "external_reference",
            "stripe_payment_intent_id",
            "created_at",
        )
        read_only_fields = (
            "id",
            "payer",
            "amount",
            "currency",
            "status",
            "external_reference",
            "stripe_payment_intent_id",
            "created_at",
        )
