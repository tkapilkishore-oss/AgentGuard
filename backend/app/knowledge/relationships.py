"""Cross-Reference and Relationship Linker for AgentGuard Knowledge Pipeline.

Builds lightweight deterministic cross-reference edges connecting:
Frontend Components -> API Client Methods -> FastAPI Routes -> Policy / Services -> Database Models.
"""

from backend.app.knowledge.models import CodeRelationship, KnowledgeUnit


class RelationshipLinker:
    """Links disparate knowledge units with lightweight cross-reference edges."""

    # Static mappings connecting frontend API client methods to backend routes & service functions
    API_CLIENT_TO_ROUTE_MAP: dict[str, str] = {
        "api.getProducts": "/products",
        "api.getMandate": "/mandate/{mandate_id}",
        "api.revokeMandate": "/mandate/{mandate_id}/revoke",
        "api.proposeTransaction": "/transaction/propose",
        "api.executeTransaction": "/transaction/execute",
        "api.approveTransaction": "/transaction/{transaction_id}/approve",
        "api.rejectTransaction": "/transaction/{transaction_id}/reject",
        "api.agentChat": "/agent/chat",
        "api.getTransactions": "/transactions",
        "api.getTransactionAudit": "/transaction/{transaction_id}/audit",
    }

    ROUTE_TO_SERVICE_MAP: dict[str, list[str]] = {
        "/transaction/propose": ["evaluate_policy", "log_audit_event"],
        "/transaction/execute": ["payment_gateway.process_payment", "log_audit_event"],
        "/transaction/{transaction_id}/approve": ["log_audit_event"],
        "/transaction/{transaction_id}/reject": ["log_audit_event"],
        "/mandate/{mandate_id}/revoke": ["log_audit_event"],
        "/transaction/{transaction_id}/audit": ["verify_audit_chain"],
    }

    @classmethod
    def enrich_relationships(cls, units: list[KnowledgeUnit]) -> list[KnowledgeUnit]:
        """Enriches knowledge units with cross-layer architecture relationships."""
        enriched: list[KnowledgeUnit] = []

        for unit in units:
            new_rels = list(unit.relationships)

            # Link frontend component knowledge to backend routes
            if unit.source_type == "TSX_COMPONENT":
                for rel in unit.relationships:
                    if rel.relationship_type == "CALLS_API_CLIENT" and rel.target_symbol in cls.API_CLIENT_TO_ROUTE_MAP:
                        target_route = cls.API_CLIENT_TO_ROUTE_MAP[rel.target_symbol]
                        new_rels.append(
                            CodeRelationship(
                                source_symbol=unit.symbol or unit.title,
                                target_symbol=target_route,
                                relationship_type="TRIGGERS_BACKEND_ROUTE",
                            )
                        )

            # Link API route knowledge to underlying core engine/services
            elif unit.source_type == "API_ROUTE" and unit.route in cls.ROUTE_TO_SERVICE_MAP:
                services = cls.ROUTE_TO_SERVICE_MAP[unit.route]
                for s in services:
                    new_rels.append(
                        CodeRelationship(
                            source_symbol=unit.route,
                            target_symbol=s,
                            relationship_type="DELEGATES_TO_SERVICE",
                        )
                    )

            unit_copy = unit.model_copy(update={"relationships": new_rels})
            enriched.append(unit_copy)

        return enriched
