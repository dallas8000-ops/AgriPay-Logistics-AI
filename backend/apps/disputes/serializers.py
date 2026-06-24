from rest_framework import serializers

from .models import Dispute, DisputeMessage


class DisputeMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = DisputeMessage
        fields = ("id", "sender", "sender_name", "body", "created_at")
        read_only_fields = ("sender", "created_at")


class DisputeSerializer(serializers.ModelSerializer):
    messages = DisputeMessageSerializer(many=True, read_only=True)
    raised_by_name = serializers.CharField(source="raised_by.username", read_only=True)

    class Meta:
        model = Dispute
        fields = (
            "id",
            "order",
            "raised_by",
            "raised_by_name",
            "category",
            "description",
            "status",
            "resolution",
            "messages",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("raised_by", "status", "resolution", "created_at", "updated_at")
