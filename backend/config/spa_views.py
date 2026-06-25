"""Serve the Vite production build for portfolio live demo (same origin as API)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.http import FileResponse, HttpResponseRedirect
from django.views import View

SPA_ROOT = Path(__file__).resolve().parent.parent / "spa"


def _guess_type(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(str(path))
    return content_type or "application/octet-stream"


def serve_spa(request, path: str = "") -> FileResponse:
    rel = (path or "").lstrip("/")
    if rel:
        candidate = SPA_ROOT / rel
        if candidate.is_file():
            return FileResponse(candidate.open("rb"), content_type=_guess_type(candidate))
    index = SPA_ROOT / "index.html"
    if not index.is_file():
        from django.http import HttpResponse

        return HttpResponse("AgriPay UI build missing — redeploy with frontend bundle.", status=503)
    return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")


class DemoRedirectView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect("/login/")


def spa_catchall(request):
    return serve_spa(request, path=request.path.lstrip("/"))
