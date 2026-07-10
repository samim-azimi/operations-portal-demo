from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.database import Base, engine, ensure_performance_indexes, ensure_schema_compatibility
from app.middleware import SecurityMiddleware
from app.routers import (
    assistant,
    auth,
    audit_logs,
    categories,
    dashboard,
    dashboards,
    knowledge_base,
    locations,
    modules,
    notifications,
    organization_settings,
    profile,
    sign,
    lan_messenger,
    inventory,
    stock,
    stock_management,
    stock_reports,
    tickets,
    tasks,
    users,
    videos,
    workspace,
)

Base.metadata.create_all(bind=engine)
ensure_schema_compatibility()
ensure_performance_indexes()
is_production = settings.environment.lower() == "production"

app = FastAPI(
    title=settings.app_name,
    description="Unified backend for Mission Operations Portal modules.",
    version="2.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityMiddleware)

for router in [
    auth.router,
    assistant.router,
    workspace.router,
    modules.router,
    profile.router,
    sign.router,
    sign.admin_router,
    lan_messenger.router,
    organization_settings.router,
    inventory.router,
    stock_management.router,
    stock_reports.router,
    stock.router,
    dashboards.router,
    users.router,
    tickets.router,
    knowledge_base.router,
    categories.router,
    locations.router,
    videos.router,
    notifications.router,
    dashboard.router,
    tasks.router,
    audit_logs.router,
]:
    app.include_router(router, prefix="/api")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy", "environment": settings.environment}
