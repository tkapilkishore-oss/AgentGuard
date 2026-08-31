"""FastAPI Route Introspector for AgentGuard Knowledge Pipeline.

Introspects active FastAPI application routes, handler functions, request/response models,
and security classifications directly from the running FastAPI app instance.
"""

import hashlib
import inspect
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

from backend.app.knowledge.models import (
    ApiRouteRecord,
    AuthorityType,
    DomainCategory,
    FreshnessStatus,
    KnowledgeUnit,
    QAIssue,
    SourceTier,
)
from backend.app.main import app

ROUTE_SECURITY_MAP: dict[str, tuple[str, str, DomainCategory]] = {
    "/transaction/propose": (
        "PROPOSE_ONLY",
        "Evaluates untrusted agent claims against pure policy engine. Does not mutate money.",
        DomainCategory.L_TRANSACTIONS,
    ),
    "/transaction/execute": (
        "REQUIRES_CONFIRMATION",
        "Performs atomic budget reservation under row lock and executes payment via Razorpay test mode.",
        DomainCategory.L_TRANSACTIONS,
    ),
    "/transaction/{transaction_id}/approve": (
        "SUPERVISOR_ONLY",
        "Human supervisor explicit approval for an escalated over-budget transaction.",
        DomainCategory.L_TRANSACTIONS,
    ),
    "/transaction/{transaction_id}/reject": (
        "SUPERVISOR_ONLY",
        "Human supervisor explicit rejection for an escalated over-budget transaction.",
        DomainCategory.L_TRANSACTIONS,
    ),
    "/mandate/{mandate_id}/revoke": (
        "REQUIRES_CONFIRMATION",
        "Revokes active spending mandate, immediately invalidating in-flight executions.",
        DomainCategory.J_MANDATES,
    ),
    "/agent/chat": (
        "PROPOSE_ONLY",
        "Untrusted shopping assistant LLM interpreter. Bridges prompt to /transaction/propose.",
        DomainCategory.N_AGENT_BEHAVIOR,
    ),
    "/mandate/{mandate_id}": (
        "READ_ONLY",
        "Retrieves mandate status, remaining budget, and merchant scopes.",
        DomainCategory.J_MANDATES,
    ),
    "/products": (
        "READ_ONLY",
        "Retrieves active PostgreSQL product catalog with authoritative prices and stock.",
        DomainCategory.G_BACKEND_ARCHITECTURE,
    ),
    "/transactions": (
        "READ_ONLY",
        "Retrieves past transaction history list in descending created_at order.",
        DomainCategory.P_AUDIT_TRAIL,
    ),
    "/transaction/{transaction_id}/audit": (
        "READ_ONLY",
        "Retrieves chronological SHA-256 audit events and verifies hash chain integrity.",
        DomainCategory.P_AUDIT_TRAIL,
    ),
    "/health": (
        "READ_ONLY",
        "Service liveness and health probe.",
        DomainCategory.G_BACKEND_ARCHITECTURE,
    ),
}


class ApiExtractor:
    """Introspects FastAPI application routes and generates canonical API records."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def _collect_api_routes(self, app_or_router: Any) -> list[APIRoute]:
        """Recursively unpacks FastAPI routes, including nested routers and _IncludedRouter objects."""
        routes: list[APIRoute] = []
        for r in getattr(app_or_router, "routes", []):
            if isinstance(r, APIRoute):
                routes.append(r)
            elif hasattr(r, "original_router"):
                routes.extend(self._collect_api_routes(r.original_router))
            elif hasattr(r, "router"):
                routes.extend(self._collect_api_routes(r.router))
            elif hasattr(r, "routes"):
                routes.extend(self._collect_api_routes(r))
        return routes

    def extract_routes(self) -> tuple[list[ApiRouteRecord], list[KnowledgeUnit], list[QAIssue]]:
        """Introspects all registered routes from the FastAPI app instance."""
        records: list[ApiRouteRecord] = []
        units: list[KnowledgeUnit] = []
        issues: list[QAIssue] = []

        all_api_routes = self._collect_api_routes(app)

        for route in all_api_routes:
            methods = list(route.methods or {"GET"})
            primary_method = [m for m in methods if m != "HEAD"][0] if methods else "GET"
            path = route.path
            handler_name = route.endpoint.__name__

            # Locate source file & line of endpoint handler
            try:
                src_file_raw = inspect.getsourcefile(route.endpoint) or "backend/app/main.py"
                rel_src = str(Path(src_file_raw).relative_to(self.workspace_root)).replace("\\", "/")
                src_lines, start_line = inspect.getsourcelines(route.endpoint)
                raw_end_line = start_line + len(src_lines) - 1
            except Exception:
                rel_src = "backend/app/main.py"
                start_line = 1
                raw_end_line = 1

            # Clamp line_end to actual physical file line count
            phys_path = self.workspace_root / rel_src
            if phys_path.exists():
                try:
                    file_line_count = len(phys_path.read_text(encoding="utf-8").splitlines())
                    end_line = min(max(start_line, raw_end_line), file_line_count)
                except Exception:
                    end_line = max(start_line, raw_end_line)
            else:
                end_line = max(start_line, raw_end_line)

            is_mutation = primary_method in ("POST", "PUT", "DELETE", "PATCH")
            sec_info = ROUTE_SECURITY_MAP.get(
                path,
                (
                    "READ_ONLY" if not is_mutation else "PROPOSE_ONLY",
                    "Standard API endpoint.",
                    DomainCategory.G_BACKEND_ARCHITECTURE,
                ),
            )
            safety_level, sec_significance, domain = sec_info

            # Safely extract request & response models across Pydantic v1/v2 / FastAPI compat
            req_model = None
            if route.body_field:
                field_info = getattr(route.body_field, "field_info", None)
                if field_info and hasattr(field_info, "annotation"):
                    req_model = getattr(field_info.annotation, "__name__", str(field_info.annotation))
                else:
                    req_model = str(getattr(route.body_field, "type_", "Payload"))

            resp_model = None
            if route.response_model:
                resp_model = getattr(route.response_model, "__name__", str(route.response_model))

            path_slug = "".join(c if c.isalnum() else "_" for c in path.lower()).strip("_")
            rec_id = f"api_{primary_method.lower()}_{path_slug}"
            content_hash = hashlib.sha256(f"{primary_method}:{path}:{rel_src}:{start_line}".encode()).hexdigest()

            api_record = ApiRouteRecord(
                id=rec_id,
                method=primary_method,
                path=path,
                handler_name=handler_name,
                source_file=rel_src,
                source_line=start_line,
                request_model=req_model,
                response_model=resp_model,
                is_mutation=is_mutation,
                safety_level=safety_level,
                security_significance=sec_significance,
            )
            records.append(api_record)

            unit = KnowledgeUnit(
                id=f"route_{rec_id}_{content_hash[:8]}",
                domain=domain,
                title=f"API: {primary_method} {path}",
                summary=sec_significance,
                content=(
                    f"Endpoint: `{primary_method} {path}`\n"
                    f"Handler: `{handler_name}()` in `{rel_src}:{start_line}`\n"
                    f"Mutation: {'Yes' if is_mutation else 'No (Read-Only)'}\n"
                    f"Safety Classification: `{safety_level}`\n"
                    f"Request Schema: `{req_model or 'None'}`\n"
                    f"Response Schema: `{resp_model or 'None'}`\n\n"
                    f"Security Significance:\n{sec_significance}"
                ),
                source_type="API_ROUTE",
                source_path=rel_src,
                source_tier=SourceTier.TIER_3_API_SCHEMA,
                line_start=start_line,
                line_end=end_line,
                symbol=handler_name,
                route=path,
                content_sha256=content_hash,
                authority=AuthorityType.AUTHORITATIVE,
                freshness=FreshnessStatus.VERIFIED,
                relationships=[],
                tags=["api", "fastapi", primary_method.lower(), domain.value.lower()],
            )
            units.append(unit)

        return records, units, issues
