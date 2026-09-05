import os
from typing import Any

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, Request, status

# pyrefly: ignore [missing-import]
from fastapi.exceptions import RequestValidationError

# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.approve import router as approve_router
from backend.app.api.execute import router as execute_router
from backend.app.api.propose import router as propose_router
from backend.app.api.routes_agent import router as agent_router
from backend.app.api.routes_audit import router as audit_router
from backend.app.api.routes_conversational import router as conversational_router
from backend.app.api.routes_mandate import router as mandate_router
from backend.app.api.routes_tts import router as tts_router
from backend.app.api.schemas import ApiResponse

app = FastAPI(
    title="Agentic Commerce Firewall API",
    description="Deterministic authorization boundary for autonomous AI agents",
    version="0.1.0",
)

# Enable CORS for React/Next.js frontend development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add defensive security headers to all responses (nosniff, clickjacking, referrer policy)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response


# Register API routers
app.include_router(propose_router)
app.include_router(approve_router)
app.include_router(execute_router)
app.include_router(agent_router)
app.include_router(mandate_router)
app.include_router(audit_router)
app.include_router(conversational_router)
app.include_router(tts_router)



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = exc.detail if isinstance(exc.detail, str) and exc.detail.isupper() else "HTTP_ERROR"
    message = exc.detail if isinstance(exc.detail, str) else "HTTP error occurred."

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", "HTTP error occurred.")

    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "data": None, "error": {"code": code, "message": message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "MALFORMED_REQUEST",
                "message": "Invalid request payload structure or missing required fields.",
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            },
        },
    )


@app.get("/health", response_model=ApiResponse[dict[str, Any]])
async def health_check() -> ApiResponse[dict[str, Any]]:
    return ApiResponse.ok({"status": "ok", "service": "Agentic Commerce Firewall"})


# ── Frontend Static Assets & SPA Client-Side Routing ─────────────────────────
FRONTEND_DIST_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../frontend/dist")
)
FRONTEND_ASSETS_DIR = os.path.join(FRONTEND_DIST_DIR, "assets")

if os.path.exists(FRONTEND_DIST_DIR):
    if os.path.exists(FRONTEND_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="assets")

    # Serve SPA entrypoint index.html for all React Router client-side navigation views
    @app.get("/", include_in_schema=False)
    @app.get("/live", include_in_schema=False)
    @app.get("/threats", include_in_schema=False)
    @app.get("/forensics", include_in_schema=False)
    async def serve_spa_views():
        index_file = os.path.join(FRONTEND_DIST_DIR, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frontend index.html not found. Run 'npm run build' in frontend directory.",
        )
