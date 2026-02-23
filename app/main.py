import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import Base, engine
from app.api.api_v1.endpoints import auth as auth_router
from app.api.api_v1.endpoints import super_admin as super_admin_router
from app.api.api_v1.endpoints import admin as admin_router
from app.api.api_v1.endpoints import user as user_router
from app.api.api_v1.endpoints import notification as notification_router
from app.api.api_v1.endpoints import public as public_router
from app.api.api_v1.endpoints.tenant_admin import categories as categories_router
from app.api.api_v1.endpoints.tenant_admin import ticket_configuration as ticket_config_router
from app.api.api_v1.endpoints.tenant_admin import configuration as config_router
from app.api.api_v1.endpoints.tenant_admin import tickets as tickets_router
from app.api.api_v1.endpoints.tenant_admin import dashboard as dashboard_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create all database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Multi-tenant SaaS application API with user authentication",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Setup CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).strip() for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
        max_age=600,
    )

# Include routers
app.include_router(public_router.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api/v1/auth")
app.include_router(super_admin_router.router, prefix="/api/v1/super-admin")
app.include_router(admin_router.router, prefix="/api/v1/admin")
app.include_router(user_router.router, prefix="/api/v1/user")
app.include_router(notification_router.router, prefix="/api/v1/user")
app.include_router(categories_router.router, prefix="/api/v1/admin")
app.include_router(ticket_config_router.router, prefix="/api/v1/admin")
app.include_router(config_router.router, prefix="/api/v1/admin")
app.include_router(tickets_router.router, prefix="/api/v1/admin")
app.include_router(dashboard_router.router, prefix="/api/v1/admin")


# Root endpoints
@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint"""
    return {
        "message": "Welcome to Shakwa Multi-Tenant API",
        "docs": "/api/docs",
        "version": settings.PROJECT_VERSION,
    }


@app.get("/api", tags=["Root"])
async def api_root():
    """API root endpoint with available endpoints"""
    return {
        "message": "Shakwa Multi-Tenant API",
        "version": settings.PROJECT_VERSION,
        "endpoints": {
            "login": "/api/v1/auth/login",
            "register": "/api/v1/auth/register",
            "health": "/api/v1/auth/health",
            "documentation": "/api/docs",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
