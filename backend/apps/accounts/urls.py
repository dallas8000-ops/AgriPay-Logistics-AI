from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .billing_views import BillingChargeView, BillingSummaryView
from .views import AdminDashboardStatsView, MeView, OnboardingView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path("admin/stats/", AdminDashboardStatsView.as_view(), name="admin_stats"),
    path("billing/", BillingSummaryView.as_view(), name="billing_summary"),
    path("billing/charge/", BillingChargeView.as_view(), name="billing_charge"),
]
