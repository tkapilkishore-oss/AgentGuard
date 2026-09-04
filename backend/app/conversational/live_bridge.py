"""Authoritative Live Runtime Bridge for AgentGuard.

Reuses existing database models and services for strictly read-only state inspection.
Does NOT duplicate transaction, mandate, product, policy, or audit business logic.
"""

import time
from typing import Any

from sqlalchemy.orm import Session

from backend.app.conversational.models import EvidenceContext, LiveToolRequest, LiveToolResult, LiveToolType
from backend.app.db.session import SessionLocal
from backend.app.models.approval import Approval
from backend.app.models.audit import AuditEvent
from backend.app.models.mandate import Mandate
from backend.app.models.merchant import Merchant
from backend.app.models.product import Product
from backend.app.models.transaction import Transaction
from backend.app.services.audit_log import verify_audit_chain


class LiveRuntimeBridge:
    """Safe, read-only adapter querying live PostgreSQL database models and services."""

    def __init__(self, db_factory=SessionLocal) -> None:
        self.db_factory = db_factory

    def execute_live_tool(self, request: LiveToolRequest, db: Session | None = None) -> LiveToolResult:
        """Executes a live tool query against authoritative backend systems."""
        start_time = time.perf_counter()
        session_created = False

        if db is None:
            db = self.db_factory()
            session_created = True

        try:
            if request.tool_type == LiveToolType.MANDATE_BUDGET:
                result_data = self._query_mandate_budget(request.parameters, db)
            elif request.tool_type == LiveToolType.TRANSACTION_STATUS:
                result_data = self._query_transaction_status(request.parameters, db)
            elif request.tool_type == LiveToolType.PRODUCT_CATALOG:
                result_data = self._query_product_catalog(request.parameters, db)
            elif request.tool_type == LiveToolType.MERCHANT_CATALOG:
                result_data = self._query_merchant_catalog(request.parameters, db)
            elif request.tool_type == LiveToolType.AUDIT_CHAIN_INTEGRITY:
                result_data = self._verify_live_audit_chain(request.parameters, db)
            else:
                return LiveToolResult(
                    tool_type=request.tool_type,
                    success=False,
                    error=f"Unsupported live tool type: {request.tool_type}",
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return LiveToolResult(
                tool_type=request.tool_type,
                success=True,
                data=result_data,
                execution_latency_ms=round(elapsed_ms, 2),
            )
        except Exception as e:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return LiveToolResult(
                tool_type=request.tool_type,
                success=False,
                data={},
                execution_latency_ms=round(elapsed_ms, 2),
                error=f"Live tool execution failed: {str(e)}",
            )
        finally:
            if session_created:
                db.close()

    def create_evidence_context(self, tool_result: LiveToolResult) -> EvidenceContext:
        """Converts a live tool result into an EvidenceContext for response generation."""
        summary_notes: list[str] = []
        if tool_result.success:
            d = tool_result.data
            if tool_result.tool_type == LiveToolType.MANDATE_BUDGET:
                if d.get("found") is False:
                    summary_notes.append(
                        f"LIVE MANDATE NOT FOUND: Mandate '{d.get('id')}' was not found in PostgreSQL records."
                    )
                else:
                    summary_notes.append(
                        f"LIVE MANDATE: mandate budget for ID {d.get('id')}, Remaining Budget: ₹{d.get('budget_remaining')}, "
                        f"Total: ₹{d.get('budget_total')}, Status: {d.get('status')}"
                    )
            elif tool_result.tool_type == LiveToolType.TRANSACTION_STATUS:
                if d.get("found") is False:
                    summary_notes.append(
                        f"LIVE TRANSACTION NOT FOUND: Transaction '{d.get('id')}' was not found in PostgreSQL ledger. "
                        f"Total ledger transactions: {d.get('total_count', 0)}."
                    )
                else:
                    tx_items = d.get("recent_transactions", [])
                    if tx_items:
                        tx_desc = "; ".join([item.get("summary", "") for item in tx_items])
                        summary_notes.append(
                            f"LIVE TRANSACTION LEDGER: {d.get('total_count', 0)} recorded transactions in PostgreSQL "
                            f"({d.get('success_count', 0)} SUCCESS, {d.get('denied_count', 0)} DENIED, {d.get('escalated_count', 0)} ESCALATED) "
                            f"backed by {d.get('audit_events_count', 0)} SHA-256 chained audit events. "
                            f"Recent transactions: {tx_desc}"
                        )
                    else:
                        summary_notes.append(
                            f"LIVE TRANSACTION LEDGER: {d.get('total_count', 0)} total recorded transactions in PostgreSQL "
                            f"({d.get('success_count', 0)} SUCCESS, {d.get('denied_count', 0)} DENIED, {d.get('escalated_count', 0)} ESCALATED) "
                            f"with {d.get('audit_events_count', 0)} SHA-256 chained audit events. "
                            f"Latest transaction: {d.get('id')}, Status: {d.get('status')}, Reason: {d.get('reason_code')}, Total: ₹{d.get('authoritative_total')}."
                        )
            elif tool_result.tool_type == LiveToolType.PRODUCT_CATALOG:
                if d.get("found") is False:
                    summary_notes.append(
                        f"LIVE PRODUCT NOT FOUND: Product '{d.get('product_id')}' was not found in PostgreSQL catalog."
                    )
                else:
                    summary_notes.append(
                        f"LIVE CATALOG: {d.get('active_count', 1)} active products in PostgreSQL catalog: {d.get('items_summary', d.get('name'))}."
                    )
            elif tool_result.tool_type == LiveToolType.MERCHANT_CATALOG:
                summary_notes.append(
                    f"LIVE MERCHANTS: {d.get('active_count', 0)} active merchants in PostgreSQL database: {d.get('items_summary', 'None')}."
                )
            elif tool_result.tool_type == LiveToolType.AUDIT_CHAIN_INTEGRITY:
                summary_notes.append(
                    f"LIVE AUDIT LEDGER: Valid: {d.get('chain_valid')}, Entries: {d.get('entry_count')}, "
                    f"Head Hash: {d.get('head_hash')}, Status: {d.get('status')}"
                )
        else:
            summary_notes.append(f"LIVE TOOL FAILURE: {tool_result.error}")

        return EvidenceContext(
            static_evidence=None,
            live_result=tool_result,
            is_live=True,
            provenance_unit_ids=[f"live_tool_{tool_result.tool_type.value.lower()}"],
            authorities=[],
            source_tiers=[],
            confidence=1.0 if tool_result.success else 0.0,
            summary_notes=summary_notes,
        )

    def _query_mandate_budget(self, params: dict[str, Any], db: Session) -> dict[str, Any]:
        mandate_id = params.get("mandate_id")
        if mandate_id and mandate_id != "mandate-001":
            mandate = db.query(Mandate).filter_by(id=mandate_id).first()
        else:
            mandate = db.query(Mandate).filter_by(id="mandate-001").first() or db.query(Mandate).first()

        if not mandate:
            return {
                "id": mandate_id or "default",
                "found": False,
                "budget_remaining": "0.00",
                "budget_total": "0.00",
                "status": "not_found",
            }

        # Check product affordability if product_id requested
        product_id = params.get("product_id")
        product_affordability = None
        if product_id:
            prod = db.query(Product).filter_by(id=product_id).first()
            if prod:
                is_affordable = mandate.budget_remaining >= prod.price
                product_affordability = {
                    "product_name": prod.name,
                    "product_price": str(prod.price),
                    "is_affordable": is_affordable,
                    "shortfall": str(prod.price - mandate.budget_remaining) if not is_affordable else "0.00",
                }

        return {
            "id": mandate.id,
            "found": True,
            "user_id": mandate.user_id,
            "budget_remaining": str(mandate.budget_remaining),
            "current_budget": str(mandate.budget_remaining),
            "mandate_budget": str(mandate.budget_remaining),
            "budget_total": str(mandate.budget_total),
            "max_transaction_amount": str(mandate.max_transaction_amount),
            "status": mandate.status,
            "mandate_status": mandate.status,
            "expires_at": mandate.expires_at.isoformat() if mandate.expires_at else None,
            "product_affordability": product_affordability,
        }

    def _query_transaction_status(self, params: dict[str, Any], db: Session) -> dict[str, Any]:
        total_txns = db.query(Transaction).count()
        success_txns = db.query(Transaction).filter_by(status="SUCCESS").count()
        denied_txns = db.query(Transaction).filter_by(status="DENIED").count()
        escalated_txns = db.query(Transaction).filter_by(status="ESCALATED").count()
        audit_events_count = db.query(AuditEvent).count()

        # Build product and approval lookup maps
        products_map = {p.id: p.name for p in db.query(Product).all()}
        approvals_map = {a.transaction_id: a for a in db.query(Approval).all()}

        recent_txns_records = db.query(Transaction).order_by(Transaction.created_at.asc()).limit(10).all()
        recent_txns_list: list[dict[str, Any]] = []
        for t in recent_txns_records:
            p_name = products_map.get(t.product_id, t.product_id)
            appr = approvals_map.get(t.id)
            appr_desc = f" (Approved by {appr.approver_id})" if (appr and appr.status == "approved") else ""
            recent_txns_list.append({
                "id": t.id,
                "product_id": t.product_id,
                "product_name": p_name,
                "claimed_price": str(t.claimed_price),
                "authoritative_price": str(t.authoritative_price),
                "authoritative_total": str(t.authoritative_total),
                "quantity": t.quantity,
                "status": t.status,
                "reason_code": t.reason_code,
                "approval_status": appr.status if appr else None,
                "approver_id": appr.approver_id if appr else None,
                "executed_at": t.executed_at.isoformat() if t.executed_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "summary": f"{p_name} | Claimed: ₹{t.claimed_price}, Actual: ₹{t.authoritative_price} | Status: {t.status} ({t.reason_code}){appr_desc}",
            })

        txn_id = params.get("transaction_id")
        if txn_id:
            txn = db.query(Transaction).filter_by(id=txn_id).first()
        else:
            # Return latest transaction
            txn = db.query(Transaction).order_by(Transaction.created_at.desc()).first()

        if not txn:
            return {
                "id": txn_id or "latest",
                "found": False,
                "total_count": total_txns,
                "transaction_count": total_txns,
                "forensic_ledger_transaction_count": total_txns,
                "success_count": success_txns,
                "denied_count": denied_txns,
                "escalated_count": escalated_txns,
                "audit_events_count": audit_events_count,
                "recent_transactions": recent_txns_list,
                "status": "NO_TRANSACTIONS_RECORDED",
                "reason_code": "NOT_FOUND",
            }

        return {
            "id": txn.id,
            "found": True,
            "total_count": total_txns,
            "transaction_count": total_txns,
            "forensic_ledger_transaction_count": total_txns,
            "success_count": success_txns,
            "denied_count": denied_txns,
            "escalated_count": escalated_txns,
            "audit_events_count": audit_events_count,
            "recent_transactions": recent_txns_list,
            "mandate_id": txn.mandate_id,
            "user_id": txn.user_id,
            "product_id": txn.product_id,
            "product_name": products_map.get(txn.product_id, txn.product_id),
            "claimed_price": str(txn.claimed_price),
            "authoritative_price": str(txn.authoritative_price),
            "authoritative_total": str(txn.authoritative_total),
            "quantity": txn.quantity,
            "status": txn.status,
            "reason_code": txn.reason_code,
            "created_at": txn.created_at.isoformat() if txn.created_at else None,
            "executed_at": txn.executed_at.isoformat() if txn.executed_at else None,
        }

    def _query_merchant_catalog(self, params: dict[str, Any], db: Session) -> dict[str, Any]:
        merchants = db.query(Merchant).all()
        active_merchants = [m for m in merchants if m.status == "active"]
        items_desc = [f"{m.name} ({m.id}, {m.status}, category: {m.category})" for m in active_merchants or merchants]
        merchant_list = [
            {
                "id": m.id,
                "merchant_id": m.id,
                "name": m.name,
                "category": m.category,
                "status": m.status,
                "active": m.status == "active",
            }
            for m in merchants
        ]
        return {
            "active_count": len(active_merchants),
            "total_count": len(merchants),
            "items_summary": ", ".join(items_desc),
            "merchants": merchant_list,
            "active_merchants": merchant_list,
        }

    def _query_product_catalog(self, params: dict[str, Any], db: Session) -> dict[str, Any]:
        product_id = params.get("product_id")
        if product_id:
            p = db.query(Product).filter_by(id=product_id).first()
            if p:
                return {
                    "product_id": p.id,
                    "name": p.name,
                    "price": str(p.price),
                    "stock": p.stock,
                    "in_stock": p.stock > 0,
                    "active": p.active,
                    "found": True,
                }
            else:
                return {
                    "product_id": product_id,
                    "found": False,
                    "in_stock": False,
                    "active": False,
                }

        products = db.query(Product).filter_by(active=True).all()
        items_desc = [f"{p.name} (₹{p.price}, {p.stock} in stock)" for p in products]
        catalog_list = [
            {
                "id": p.id,
                "product_id": p.id,
                "name": p.name,
                "price": str(p.price),
                "stock": p.stock,
                "in_stock": p.stock > 0,
            }
            for p in products
        ]
        return {
            "active_count": len(products),
            "items_summary": ", ".join(items_desc),
            "products": catalog_list,
            "catalog_prices": catalog_list,
            "product_prices": catalog_list,
        }

    def _verify_live_audit_chain(self, params: dict[str, Any], db: Session) -> dict[str, Any]:
        transaction_id = params.get("transaction_id")
        is_valid, err_msg = verify_audit_chain(db)
        audit_events_count = db.query(AuditEvent).count()
        return {
            "chain_valid": is_valid,
            "error": err_msg,
            "entry_count": audit_events_count,
            "transaction_id_filter": transaction_id,
            "verified_at": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
            "status": "VALID_TAMPER_PROOF" if is_valid else "TAMPERING_DETECTED",
        }
