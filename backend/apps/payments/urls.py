from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, stripe_webhook

router = DefaultRouter()
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("webhook/stripe/", stripe_webhook, name="stripe_webhook"),
    path("", include(router.urls)),
]
