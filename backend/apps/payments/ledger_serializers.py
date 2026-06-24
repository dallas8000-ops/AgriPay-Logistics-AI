from rest_framework import serializers

from .models import PaymentLedgerEntry


class PaymentLedgerEntrySerializer(serializers.ModelSerializer):
    order_reference = serializers.SerializerMethodField()
    invoice_reference = serializers.SerializerMethodField()
    suggested_order_ids = serializers.SerializerMethodField()
    suggested_invoice_ids = serializers.SerializerMethodField()

    class Meta:
        model = PaymentLedgerEntry
        fields = (
            "id",
            "owner",
            "recorded_by",
            "order",
            "invoice",
            "order_reference",
            "invoice_reference",
            "source",
            "status",
            "raw_sms",
            "amount",
            "currency",
            "provider",
            "txn_reference",
            "payer_phone",
            "parse_confidence",
            "parsed_fields",
            "notes",
            "suggested_order_ids",
            "suggested_invoice_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "recorded_by",
            "parse_confidence",
            "parsed_fields",
            "created_at",
            "updated_at",
        )

    def get_order_reference(self, obj):
        if obj.order:
            return obj.order.payment_reference
        parsed_ref = (obj.parsed_fields or {}).get("order_reference", "")
        if parsed_ref and parsed_ref.upper().startswith(("AGR", "ORDER")):
            return parsed_ref
        return ""

    def get_invoice_reference(self, obj):
        if obj.invoice:
            return obj.invoice.payment_reference
        parsed_ref = (obj.parsed_fields or {}).get("order_reference", "")
        if parsed_ref and parsed_ref.upper().startswith("INV"):
            return parsed_ref
        return ""

    def get_suggested_order_ids(self, obj):
        return self.context.get("suggestions", {}).get(str(obj.id), [])

    def get_suggested_invoice_ids(self, obj):
        return self.context.get("invoice_suggestions", {}).get(str(obj.id), [])


class ParseSmsSerializer(serializers.Serializer):
    text = serializers.CharField()


class MatchLedgerSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
