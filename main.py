import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Import our settings and routers
from app.config import settings
from app.api.router import api_router

def create_app() -> FastAPI:
    """Factory function to initialize the FastAPI application."""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="A unified control plane for LLM inference routing, caching, and FinOps.",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Middleware to disable caching for documentation endpoints
    @app.middleware("http")
    async def remove_docs_cache(request: Request, call_next):
        response = await call_next(request)
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files (Dashboard UI)
    app.mount("/dashboard-ui", StaticFiles(directory="app/static", html=True), name="static")

    # Root endpoint
    @app.get("/", tags=["System"])
    async def root():
        return JSONResponse(
            content={
                "message": f"Welcome to the {settings.PROJECT_NAME}",
                "environment": settings.ENVIRONMENT,
                "status": "online",
                "docs_url": "/docs"
            }
        )

    # Include API routers
    app.include_router(api_router, prefix="/api/v1")

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=True if settings.ENVIRONMENT == "development" else False
    )