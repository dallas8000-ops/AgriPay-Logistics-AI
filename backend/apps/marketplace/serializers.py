from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Order, ProduceListing


class ProduceListingSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.username", read_only=True)

    class Meta:
        model = ProduceListing
        fields = (
            "id",
            "seller",
            "seller_name",
            "crop",
            "variety",
            "quantity_kg",
            "unit_price",
            "currency",
            "location",
            "country",
            "season",
            "harvest_date",
            "description",
            "image",
            "ai_suggested_price",
            "status",
            "created_at",
        )
        read_only_fields = ("seller", "ai_suggested_price", "created_at")


class OrderSerializer(serializers.ModelSerializer):
    listing_detail = ProduceListingSerializer(source="listing", read_only=True)
    buyer_name = serializers.CharField(source="buyer.username", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "listing",
            "listing_detail",
            "buyer",
            "buyer_name",
            "quantity_kg",
            "total_amount",
            "currency",
            "delivery_address",
            "status",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("buyer", "total_amount", "currency", "status", "created_at", "updated_at")

    def create(self, validated_data):
        listing = validated_data["listing"]
        quantity = validated_data["quantity_kg"]
        validated_data["total_amount"] = quantity * listing.unit_price
        validated_data["currency"] = listing.currency
        validated_data["buyer"] = self.context["request"].user
        return super().create(validated_data)
