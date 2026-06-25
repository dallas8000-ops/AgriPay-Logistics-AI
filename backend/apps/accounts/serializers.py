from rest_framework import serializers

from .models import BuyerProfile, DriverProfile, FarmerProfile, User, VendorProfile


class UserSerializer(serializers.ModelSerializer):
    currency = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "country",
            "phone",
            "preferred_language",
            "is_verified",
            "currency",
            "date_joined",
        )
        read_only_fields = ("id", "is_verified", "date_joined")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    organization_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "country",
            "phone",
            "organization_name",
        )

    def create(self, validated_data):
        org_name = validated_data.pop("organization_name", "").strip()
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if org_name:
            from .models import Organization, add_member_to_organization, OrganizationMembership
            org = Organization.objects.create(name=org_name)
            add_member_to_organization(org, user, role=OrganizationMembership.Role.OWNER)
        return user


class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = "__all__"
        read_only_fields = ("user", "created_at")


class VendorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProfile
        fields = "__all__"
        read_only_fields = ("user", "created_at")


class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = "__all__"
        read_only_fields = ("user", "reliability_score", "total_orders", "created_at")


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = "__all__"
        read_only_fields = ("user", "created_at")
