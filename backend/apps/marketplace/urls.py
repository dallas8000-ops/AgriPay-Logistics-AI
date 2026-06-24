from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, ProduceListingViewSet

router = DefaultRouter()
router.register("listings", ProduceListingViewSet, basename="listing")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("", include(router.urls)),
]
