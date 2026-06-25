from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.health import api_root, capabilities_view, health_check

urlpatterns = [
    path("health/", health_check, name="health"),
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
    path("stripe/", include("stripe.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
