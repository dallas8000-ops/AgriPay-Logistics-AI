from django.db import connection
from django.http import JsonResponse


def health_check(request):
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False
    status_code = 200 if db_ok else 503
    return JsonResponse(
        {
            "status": "ok" if db_ok else "degraded",
            "database": "connected" if db_ok else "unavailable",
            "service": "agripay-logistics-api",
        },
        status=status_code,
    )


def api_root(request):
    return JsonResponse(
        {
            "service": "agripay-logistics-api",
            "message": "API is running. Use the web app at http://127.0.0.1:5174/",
            "endpoints": {
                "auth": "/api/auth/",
                "marketplace": "/api/marketplace/",
                "logistics": "/api/logistics/",
                "payments": "/api/payments/",
                "ai": "/api/ai/",
                "disputes": "/api/disputes/",
                "notifications": "/api/notifications/",
                "health": "/health/",
            },
        }
    )
