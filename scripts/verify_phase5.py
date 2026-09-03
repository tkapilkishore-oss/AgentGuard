#!/usr/bin/env python
"""Phase 5 Manual Verification Script — AgentGuard / Agentic Commerce Firewall.

Verifies end-to-end Phase 5 Audit Trail & Transaction History capabilities:
 1. Database seed and reset.
 2. Successful transaction proposal & execution.
 3. Authoritative lifecycle reconstruction for SUCCESS transaction.
 4. Denied transaction audit trace (Price Tampering / PRICE_MISMATCH).
 5. Escalated & approved transaction lifecycle (Over-budget -> Approved -> Executed).
 6. Deterministic chronological sequence (seq_id ASC).
 7. Actor attribution (agent, firewall, human, razorpay).
 8. SHA-256 cryptographic chain verification (verify_audit_chain == True).
 9. Transaction history list (GET /transactions descending order).
10. Nonexistent transaction handling (404 TRANSACTION_NOT_FOUND).
11. Read-only invariant (audit requests mutate 0 state).
12. Zero secret credentials leaked.
"""

import os
import sys
import uuid
from decimal import Decimal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models import AuditChainState, AuditEvent, Transaction
from backend.app.services.audit_log import verify_audit_chain
from backend.app.services.payment_gateway import payment_gateway
from scripts.seed_db import seed_database, seed_demo_state


def run_phase5_verification() -> bool:
    print("=" * 76)
    print("  AGENTGUARD PHASE 5 AUDIT TRAIL / TRANSACTION HISTORY VERIFICATION")
    print("=" * 76)

    payment_gateway.force_decline = False
    db = SessionLocal()

    try:
        # 1. Reset Database
        seed_database(db)
        client = TestClient(app)
        print("[1/12] Database seeded to fresh baseline.")

        # 2. Propose and Execute Successful Transaction (Speaker ₹2,799)
        prop1 = client.post(
            "/transaction/propose",
            json={
                "user_id": "user-001",
                "mandate_id": "mandate-001",
                "agent_claim": {
                    "product_id": "prod-002",
                    "claimed_price": 2799.00,
                    "quantity": 1,
                },
            },
        )
        assert prop1.status_code == 200, f"Propose failed: {prop1.text}"
        txn1_id = prop1.json()["data"]["transaction_id"]

        exec1 = client.post(
            "/transaction/execute",
            json={
                "transaction_id": txn1_id,
                "idempotency_key": f"verify-p5-{uuid.uuid4()}",
            },
        )
        assert exec1.status_code == 200, f"Execute failed: {exec1.text}"
        print(f"[2/12] Created and executed transaction: {txn1_id} (SUCCESS)")

        # 3. Retrieve Authoritative Audit History for Txn 1
        audit1 = client.get(f"/transaction/{txn1_id}/audit")
        assert audit1.status_code == 200, f"Audit endpoint failed: {audit1.text}"
        body1 = audit1.json()
        assert body1["success"] is True
        assert body1["error"] is None
        data1 = body1["data"]

        assert data1["transaction"]["id"] == txn1_id
        assert data1["transaction"]["status"] == "SUCCESS"
        assert Decimal(str(data1["transaction"]["authoritative_total"])) == Decimal("2799.00")
        assert data1["chain_verified"] is True

        events1 = data1["events"]
        types1 = [e["event_type"] for e in events1]
        assert types1 == ["PROPOSED", "POLICY_DECISION", "EXECUTING", "EXECUTED"], f"Unexpected event flow: {types1}"
        actors1 = [e["actor"] for e in events1]
        assert actors1 == ["agent", "firewall", "firewall", "razorpay"], f"Unexpected actors: {actors1}"
        print(f"[3/12] Reconstructed lifecycle for {txn1_id[:8]}...: {' -> '.join(types1)}")

        # 4. Propose Price-Tampered Transaction (Earbuds claimed 1999 vs authoritative 3499)
        prop2 = client.post(
            "/transaction/propose",
            json={
                "user_id": "user-001",
                "mandate_id": "mandate-001",
                "agent_claim": {
                    "product_id": "prod-001",
                    "claimed_price": 1999.00,
                    "quantity": 1,
                },
            },
        )
        assert prop2.status_code == 200
        txn2_id = prop2.json()["data"]["transaction_id"]
        assert prop2.json()["data"]["decision"] == "DENY"
        assert prop2.json()["data"]["reason_code"] == "PRICE_MISMATCH"

        audit2 = client.get(f"/transaction/{txn2_id}/audit")
        assert audit2.status_code == 200
        data2 = audit2.json()["data"]
        assert data2["transaction"]["status"] == "DENIED"
        assert data2["transaction"]["reason_code"] == "PRICE_MISMATCH"
        types2 = [e["event_type"] for e in data2["events"]]
        assert types2 == ["PROPOSED", "POLICY_DECISION"], f"Unexpected denied events: {types2}"
        print(f"[4/12] Reconstructed DENIED trace for {txn2_id[:8]}...: {' -> '.join(types2)} ({data2['transaction']['reason_code']})")

        # 5. Propose Over-budget -> Approve -> Execute Flow
        prop3 = client.post(
            "/transaction/propose",
            json={
                "user_id": "user-001",
                "mandate_id": "mandate-001",
                "agent_claim": {
                    "product_id": "prod-001",
                    "claimed_price": 3499.00,
                    "quantity": 1,
                },
            },
        )
        assert prop3.status_code == 200
        txn3_id = prop3.json()["data"]["transaction_id"]
        assert prop3.json()["data"]["decision"] == "ESCALATE"

        # Approve
        appr3 = client.post(f"/transaction/{txn3_id}/approve")
        assert appr3.status_code == 200

        # Execute
        exec3 = client.post(
            "/transaction/execute",
            json={
                "transaction_id": txn3_id,
                "idempotency_key": f"verify-p5-{uuid.uuid4()}",
            },
        )
        assert exec3.status_code == 200

        audit3 = client.get(f"/transaction/{txn3_id}/audit")
        assert audit3.status_code == 200
        data3 = audit3.json()["data"]
        types3 = [e["event_type"] for e in data3["events"]]
        assert types3 == ["PROPOSED", "POLICY_DECISION", "APPROVED", "EXECUTING", "EXECUTED"], f"Unexpected approved flow: {types3}"
        actors3 = [e["actor"] for e in data3["events"]]
        assert actors3 == ["agent", "firewall", "human", "firewall", "razorpay"], f"Unexpected actors: {actors3}"
        print(f"[5/12] Reconstructed ESCALATED->APPROVED flow for {txn3_id[:8]}...: {' -> '.join(types3)}")

        # 6. Verify Deterministic Order (seq_id monotonically increasing)
        for d in [data1, data2, data3]:
            seqs = [e["seq_id"] for e in d["events"]]
            assert seqs == sorted(seqs), f"Events not in ascending seq_id order: {seqs}"
        print("[6/12] Deterministic ordering verified: events strictly ascending by seq_id.")

        # 7. Actor Attribution Verified
        assert data1["events"][0]["actor"] == "agent"
        assert data1["events"][1]["actor"] == "firewall"
        assert data3["events"][2]["actor"] == "human"
        assert data3["events"][4]["actor"] == "razorpay"
        print("[7/12] Actor attribution verified across all participants: agent, firewall, human, razorpay.")

        # 8. Cryptographic Hash Chain Integrity
        is_valid, err = verify_audit_chain(db)
        assert is_valid is True, f"Audit chain verification failed: {err}"
        assert err is None
        print("[8/12] SHA-256 cryptographic chain verified: continuous, unbroken hash chain.")

        # 9. Transaction History List (GET /transactions)
        list_resp = client.get("/transactions")
        assert list_resp.status_code == 200
        txns_list = list_resp.json()["data"]
        assert len(txns_list) >= 3
        # Confirm descending created_at order
        created_times = [t["created_at"] for t in txns_list]
        assert created_times == sorted(created_times, reverse=True)
        print(f"[9/12] Transaction explorer list verified: {len(txns_list)} transactions returned in descending order.")

        # 10. Nonexistent Transaction Handling (404)
        non_existent = client.get("/transaction/00000000-0000-0000-0000-000000000000/audit")
        assert non_existent.status_code == 404
        ne_body = non_existent.json()
        assert ne_body["success"] is False
        assert ne_body["error"]["code"] == "TRANSACTION_NOT_FOUND"
        print("[10/12] Nonexistent transaction correctly returns 404 TRANSACTION_NOT_FOUND.")

        # 11. Read-Only Invariant
        events_before = db.query(AuditEvent).count()
        txns_before = db.query(Transaction).count()
        state_before = db.query(AuditChainState).filter_by(id=1).first().last_hash

        for _ in range(5):
            client.get(f"/transaction/{txn1_id}/audit")
            client.get("/transactions")

        assert db.query(AuditEvent).count() == events_before
        assert db.query(Transaction).count() == txns_before
        assert db.query(AuditChainState).filter_by(id=1).first().last_hash == state_before
        print("[11/12] Read-only invariant confirmed: zero mutations caused by audit read requests.")

        # 12. Zero Secret Leakage
        all_responses_text = audit1.text + audit2.text + audit3.text + list_resp.text
        forbidden = ["GEMINI_API_KEY", "RAZORPAY_TEST_KEY_SECRET", "rzp_test_secret", "AIzaSy", "password"]
        for f in forbidden:
            assert f not in all_responses_text, f"Secret leaked in audit API: {f}"
        print("[12/12] Zero secret leakage confirmed: credentials and environment keys protected.")

        print("=" * 76)
        print("  ALL 12 PHASE 5 AUDIT TRAIL VERIFICATION CHECKS PASSED SUCCESSFULLY")
        print("=" * 76)
        return True

    finally:
        seed_demo_state(db, reset=True)
        db.close()


if __name__ == "__main__":
    success = run_phase5_verification()
    sys.exit(0 if success else 1)
