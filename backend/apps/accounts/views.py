from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import BuyerProfile, DriverProfile, FarmerProfile, User, VendorProfile
from .serializers import (
    BuyerProfileSerializer,
    DriverProfileSerializer,
    FarmerProfileSerializer,
    RegisterSerializer,
    UserSerializer,
    VendorProfileSerializer,
)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class OnboardingView(APIView):
    PROFILE_MAP = {
        User.Role.FARMER: (FarmerProfile, FarmerProfileSerializer, "farmer_profile"),
        User.Role.VENDOR: (VendorProfile, VendorProfileSerializer, "vendor_profile"),
        User.Role.BUYER: (BuyerProfile, BuyerProfileSerializer, "buyer_profile"),
        User.Role.DRIVER: (DriverProfile, DriverProfileSerializer, "driver_profile"),
    }

    def get(self, request):
        user = request.user
        mapping = self.PROFILE_MAP.get(user.role)
        if not mapping:
            return Response({"detail": "No onboarding profile for this role."}, status=404)
        model, serializer_cls, attr = mapping
        related = getattr(user, attr, None)
        if related is None:
            try:
                related = model.objects.get(user=user)
            except model.DoesNotExist:
                return Response({"onboarding_complete": False, "profile": None})
        return Response(
            {
                "onboarding_complete": getattr(related, "onboarding_complete", False),
                "profile": serializer_cls(related).data,
            }
        )

    def post(self, request):
        user = request.user
        mapping = self.PROFILE_MAP.get(user.role)
        if not mapping:
            return Response({"detail": "No onboarding profile for this role."}, status=400)
        model, serializer_cls, _attr = mapping
        profile, _ = model.objects.get_or_create(user=user)
        data = {**request.data, "onboarding_complete": True}
        serializer = serializer_cls(profile, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminDashboardStatsView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        from django.db.models import Sum

        from apps.disputes.models import Dispute
        from apps.logistics.models import Delivery
        from apps.marketplace.models import Order, ProduceListing
        from apps.payments.models import Payment

        volume = Payment.objects.filter(status="completed").aggregate(total=Sum("amount"))["total"]

        return Response(
            {
                "users_by_role": {
                    role: User.objects.filter(role=role).count()
                    for role, _ in User.Role.choices
                },
                "total_listings": ProduceListing.objects.count(),
                "active_orders": Order.objects.exclude(status="delivered").count(),
                "deliveries_in_transit": Delivery.objects.filter(status="in_transit").count(),
                "open_disputes": Dispute.objects.filter(status="open").count(),
                "payments_volume": float(volume or 0),
            }
        )
