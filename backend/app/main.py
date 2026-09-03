from typing import Any

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, Request, status

# pyrefly: ignore [missing-import]
from fastapi.exceptions import RequestValidationError

# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
