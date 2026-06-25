from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from config.health import api_root, capabilities_view, health_check
from config.spa_views import DemoRedirectView, spa_catchall
from stripe_billing.views import webhook as stripe_billing_webhook

urlpatterns = [
    path("health/", health_check, name="health"),
    path("demo/", DemoRedirectView.as_view(), name="demo"),
    path("admin/", admin.site.urls),
    path("api/", api_root, name="api-root"),
    path("api/system/capabilities/", capabilities_view, name="capabilities"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/marketplace/", include("apps.marketplace.urls")),
    path("api/logistics/", include("apps.logistics.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/ai/", include("apps.ai_services.urls")),
    path("api/disputes/", include("apps.disputes.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("webhooks/stripe/", stripe_billing_webhook, name="stripe-webhook-root"),
    path("api/stripe/", include("stripe_billing.urls")),
    path("stripe/", include("stripe_billing.urls")),
    re_path(
        r"^(?!api/|health/|admin/|webhooks/|stripe/|static/).*$",
        spa_catchall,
        name="spa",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
