from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User

from .models import Dispute, DisputeMessage
from .serializers import DisputeMessageSerializer, DisputeSerializer


class DisputeViewSet(viewsets.ModelViewSet):
    serializer_class = DisputeSerializer
    filterset_fields = ["status", "category"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == User.Role.ADMIN:
            return Dispute.objects.all()
        return Dispute.objects.filter(raised_by=user)

    def perform_create(self, serializer):
        dispute = serializer.save(raised_by=self.request.user)
        from apps.notifications.services import notify_dispute_raised

        notify_dispute_raised(dispute)

    @action(detail=True, methods=["post"])
    def add_message(self, request, pk=None):
        dispute = self.get_object()
        serializer = DisputeMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(dispute=dispute, sender=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        dispute.status = Dispute.Status.RESOLVED
        dispute.resolution = request.data.get("resolution", "")
        dispute.resolved_by = request.user
        dispute.save()
        return Response(DisputeSerializer(dispute).data)
