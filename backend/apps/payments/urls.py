from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .invoice_views import InvoiceViewSet, PublicInvoiceView
from .ledger_views import PaymentLedgerViewSet, PersonalCollectionViewSet
from .views import (
    PaymentViewSet,
    flutterwave_webhook,
    mpesa_webhook,
    mtn_momo_webhook,
    stripe_webhook,
)

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("ledger", PaymentLedgerViewSet, basename="payment-ledger")
router.register("collect", PersonalCollectionViewSet, basename="personal-collection")
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("invoices/public/<str:payment_reference>/", PublicInvoiceView.as_view(), name="public-invoice"),
    path("webhook/stripe/", stripe_webhook, name="stripe_webhook"),
    path("webhook/flutterwave/", flutterwave_webhook, name="flutterwave_webhook"),
    path("webhook/mtn/", mtn_momo_webhook, name="mtn_momo_webhook"),
    path("webhook/mpesa/", mpesa_webhook, name="mpesa_webhook"),
    path("", include(router.urls)),
]
