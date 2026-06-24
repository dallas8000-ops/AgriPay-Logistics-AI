from rest_framework import serializers

from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.username", read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "seller",
            "seller_name",
            "customer_name",
            "customer_phone",
            "customer_email",
            "description",
            "amount",
            "currency",
            "payment_reference",
            "status",
            "collection_method",
            "due_date",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "seller",
            "payment_reference",
            "status",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        validated_data["seller"] = self.context["request"].user
        if not validated_data.get("currency"):
            validated_data["currency"] = self.context["request"].user.currency
        return super().create(validated_data)


class InvoicePaySerializer(serializers.Serializer):
    redirect_url = serializers.URLField(required=False, allow_blank=True)
