"""Điểm vào FastAPI. `uvicorn app.main:app`."""
import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import admin, auth, errors, public, staff
from .application import Application
from .config import ROOT, Settings

PUBLIC = os.path.join(ROOT, "public")
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
       "connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


def create_app(core: Application | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if core is None:
        settings = Settings.from_env()
        settings.validate()
        core = Application(settings)
        core.bootstrap_admin()
    api = FastAPI(title="Event Management & Check-in", docs_url="/api/docs" if not core.settings.production else None,
                  redoc_url=None, openapi_url="/api/openapi.json" if not core.settings.production else None)
    api.state.core = core
    errors.install(api)

    @api.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                             "Referrer-Policy": "same-origin", "Content-Security-Policy": CSP})
        if request.url.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @api.get("/api/health")
    def health():
        return {"ok": True}

    for r in (auth.router, public.router, admin.router, staff.router):
        api.include_router(r)

    @api.get("/e/{unique_url}", include_in_schema=False)
    def event_page(unique_url: str):
        return FileResponse(os.path.join(PUBLIC, "portal", "event.html"))

    @api.get("/", include_in_schema=False)
    def home():
        return FileResponse(os.path.join(PUBLIC, "portal", "index.html"))

    api.mount("/", StaticFiles(directory=PUBLIC, html=True), name="public")
    return api


def __getattr__(name):                    # `uvicorn app.main:app` tạo ứng dụng khi được import
    if name == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError(name)
