from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend.app.policy.engine import evaluate_policy
from backend.app.policy.models import (
    AgentProposalInput,
    MandatePolicyInput,
    ProductPolicyInput,
)
from backend.app.policy.reason_codes import PolicyDecision, ReasonCode


@pytest.fixture
def base_time():
    return datetime(2026, 8, 26, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def valid_mandate(base_time):
    return MandatePolicyInput(
        id="mandate-001",
        user_id="user-001",
        budget_total=Decimal("3000.00"),
        budget_remaining=Decimal("3000.00"),
        merchant_scope="merchant-001",
        max_transaction_amount=Decimal("3000.00"),
        status="active",
        expires_at=base_time + timedelta(hours=24),
    )


@pytest.fixture
def valid_product():
    return ProductPolicyInput(
        id="prod-001",
        merchant_id="merchant-001",
        name="Wireless Earbuds",
        price=Decimal("2799.00"),
        stock=50,
        active=True,
    )


@pytest.fixture
def valid_proposal():
    return AgentProposalInput(
        product_id="prod-001",
        claimed_price=Decimal("2799.00"),
        quantity=1,
    )


# U1: Happy path
def test_u1_happy_path(valid_mandate, valid_product, valid_proposal, base_time):
    result = evaluate_policy(valid_mandate, valid_product, valid_proposal, current_time=base_time)
    assert result.decision == PolicyDecision.ALLOW
    assert result.reason_code == ReasonCode.ALLOW
    assert result.authoritative_total == Decimal("2799.00")
    assert result.authoritative_price == Decimal("2799.00")
    assert result.claimed_price == Decimal("2799.00")


# U2: Over-budget
def test_u2_over_budget(valid_mandate, valid_product, base_time):
    over_budget_product = ProductPolicyInput(
        id="prod-002",
        merchant_id="merchant-001",
        name="Expensive Item",
        price=Decimal("3499.00"),
        stock=50,
    )
    proposal = AgentProposalInput(
        product_id="prod-002",
        claimed_price=Decimal("3499.00"),
        quantity=1,
    )
    result = evaluate_policy(valid_mandate, over_budget_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.ESCALATE
    assert result.reason_code == ReasonCode.BUDGET_EXCEEDED
    assert result.authoritative_total == Decimal("3499.00")


# U3: Price mismatch
def test_u3_price_mismatch(valid_mandate, valid_product, base_time):
    proposal = AgentProposalInput(
        product_id="prod-001",
        claimed_price=Decimal("1999.00"),
        quantity=1,
    )
    result = evaluate_policy(valid_mandate, valid_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.PRICE_MISMATCH
    assert result.authoritative_total == Decimal("2799.00")


# U4: Merchant out of scope
def test_u4_merchant_out_of_scope(valid_mandate, base_time):
    out_of_scope_product = ProductPolicyInput(
        id="prod-003",
        merchant_id="merchant-002",
        name="Studio Headphones",
        price=Decimal("2000.00"),
        stock=10,
    )
    proposal = AgentProposalInput(
        product_id="prod-003",
        claimed_price=Decimal("2000.00"),
        quantity=1,
    )
    result = evaluate_policy(valid_mandate, out_of_scope_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.MERCHANT_MISMATCH


# U5: Expired mandate
def test_u5_expired_mandate(valid_mandate, valid_product, valid_proposal, base_time):
    expired_time = base_time + timedelta(hours=25)
    result = evaluate_policy(valid_mandate, valid_product, valid_proposal, current_time=expired_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.MANDATE_EXPIRED


# U6: Revoked mandate
def test_u6_revoked_mandate(valid_mandate, valid_product, valid_proposal, base_time):
    revoked_mandate = MandatePolicyInput(
        id=valid_mandate.id,
        user_id=valid_mandate.user_id,
        budget_total=valid_mandate.budget_total,
        budget_remaining=valid_mandate.budget_remaining,
        merchant_scope=valid_mandate.merchant_scope,
        max_transaction_amount=valid_mandate.max_transaction_amount,
        status="revoked",
        expires_at=valid_mandate.expires_at,
    )
    result = evaluate_policy(revoked_mandate, valid_product, valid_proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.MANDATE_REVOKED


# U7: Quantity manipulation
@pytest.mark.parametrize("qty", [0, -1, 11, 51])
def test_u7_quantity_invalid(valid_mandate, valid_product, base_time, qty):
    proposal = AgentProposalInput(
        product_id="prod-001",
        claimed_price=Decimal("2799.00"),
        quantity=qty,
    )
    result = evaluate_policy(valid_mandate, valid_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.QUANTITY_INVALID


# U8: Exact budget boundary
def test_u8_exact_budget_boundary(valid_mandate, base_time):
    product = ProductPolicyInput(
        id="prod-004",
        merchant_id="merchant-001",
        name="Exact Budget Item",
        price=Decimal("3000.00"),
        stock=10,
    )
    proposal = AgentProposalInput(
        product_id="prod-004",
        claimed_price=Decimal("3000.00"),
        quantity=1,
    )
    result = evaluate_policy(valid_mandate, product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.ALLOW
    assert result.reason_code == ReasonCode.ALLOW
    assert result.authoritative_total == Decimal("3000.00")


# U9: Price tolerance boundary
def test_u9_price_tolerance_boundary(valid_mandate, valid_product, base_time):
    proposal = AgentProposalInput(
        product_id="prod-001",
        claimed_price=Decimal("2799.01"),  # Exactly +0.01 tolerance
        quantity=1,
    )
    result = evaluate_policy(valid_mandate, valid_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.ALLOW
    assert result.reason_code == ReasonCode.ALLOW


# Additional Mandate Status Tests
def test_mandate_status_expired(valid_mandate, valid_product, valid_proposal, base_time):
    expired_status_mandate = MandatePolicyInput(
        id=valid_mandate.id,
        user_id=valid_mandate.user_id,
        budget_total=valid_mandate.budget_total,
        budget_remaining=valid_mandate.budget_remaining,
        merchant_scope=valid_mandate.merchant_scope,
        max_transaction_amount=valid_mandate.max_transaction_amount,
        status="expired",
        expires_at=valid_mandate.expires_at,  # Future expires_at, but status is expired
    )
    result = evaluate_policy(expired_status_mandate, valid_product, valid_proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.MANDATE_EXPIRED


# Additional Expiry & Current Time Tests
def test_expiry_exact_boundary(valid_mandate, valid_product, valid_proposal):
    result = evaluate_policy(
        valid_mandate, valid_product, valid_proposal, current_time=valid_mandate.expires_at
    )
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.MANDATE_EXPIRED


def test_expiry_omitted_current_time(valid_mandate, valid_product, valid_proposal):
    # current_time is None -> defaults to current time inside evaluate_policy
    result = evaluate_policy(valid_mandate, valid_product, valid_proposal, current_time=None)
    assert result.decision == PolicyDecision.ALLOW
    assert result.reason_code == ReasonCode.ALLOW


# Additional Quantity Boolean Exclusion Tests
def test_quantity_boolean_true(valid_mandate, valid_product, base_time):
    proposal = AgentProposalInput(
        product_id="prod-001",
        claimed_price=Decimal("2799.00"),
        quantity=True,  # type: ignore
    )
    result = evaluate_policy(valid_mandate, valid_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.QUANTITY_INVALID


def test_quantity_boolean_false(valid_mandate, valid_product, base_time):
    proposal = AgentProposalInput(
        product_id="prod-001",
        claimed_price=Decimal("2799.00"),
        quantity=False,  # type: ignore
    )
    result = evaluate_policy(valid_mandate, valid_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.QUANTITY_INVALID


# Additional Merchant Scope Tests
def test_merchant_scope_none(valid_mandate, valid_product, valid_proposal, base_time):
    unrestricted_mandate = MandatePolicyInput(
        id=valid_mandate.id,
        user_id=valid_mandate.user_id,
        budget_total=valid_mandate.budget_total,
        budget_remaining=valid_mandate.budget_remaining,
        merchant_scope=None,  # Unrestricted
        max_transaction_amount=valid_mandate.max_transaction_amount,
        status="active",
        expires_at=valid_mandate.expires_at,
    )
    out_of_scope_product = ProductPolicyInput(
        id="prod-003",
        merchant_id="any-merchant-xyz",
        name="Any Headphones",
        price=Decimal("1000.00"),
        stock=10,
    )
    proposal = AgentProposalInput(
        product_id="prod-003",
        claimed_price=Decimal("1000.00"),
        quantity=1,
    )
    result = evaluate_policy(unrestricted_mandate, out_of_scope_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.ALLOW
    assert result.reason_code == ReasonCode.ALLOW


# Additional Limit Boundary Tests
def test_one_unit_above_budget(valid_mandate, base_time):
    product = ProductPolicyInput(
        id="prod-005",
        merchant_id="merchant-001",
        name="Item",
        price=Decimal("3000.01"),
        stock=10,
    )
    proposal = AgentProposalInput(
        product_id="prod-005",
        claimed_price=Decimal("3000.01"),
        quantity=1,
    )
    result = evaluate_policy(valid_mandate, product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.ESCALATE
    assert result.reason_code == ReasonCode.BUDGET_EXCEEDED


def test_one_unit_above_max_transaction(valid_mandate, base_time):
    mandate_with_cap = MandatePolicyInput(
        id=valid_mandate.id,
        user_id=valid_mandate.user_id,
        budget_total=Decimal("5000.00"),
        budget_remaining=Decimal("5000.00"),
        merchant_scope="merchant-001",
        max_transaction_amount=Decimal("2000.00"),  # Cap is 2000
        status="active",
        expires_at=valid_mandate.expires_at,
    )
    product = ProductPolicyInput(
        id="prod-006",
        merchant_id="merchant-001",
        name="Item",
        price=Decimal("2000.01"),
        stock=10,
    )
    proposal = AgentProposalInput(
        product_id="prod-006",
        claimed_price=Decimal("2000.01"),
        quantity=1,
    )
    result = evaluate_policy(mandate_with_cap, product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.ESCALATE
    assert result.reason_code == ReasonCode.BUDGET_EXCEEDED


def test_price_tolerance_just_beyond(valid_mandate, valid_product, base_time):
    proposal = AgentProposalInput(
        product_id="prod-001",
        claimed_price=Decimal("2799.02"),  # 0.02 diff vs 0.01 tolerance
        quantity=1,
    )
    result = evaluate_policy(valid_mandate, valid_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.PRICE_MISMATCH


# Security Critical Test: "LLM Lies"
def test_security_llm_lies_price_tampering(valid_mandate, base_time):
    product = ProductPolicyInput(
        id="prod-earbuds",
        merchant_id="merchant-001",
        name="Wireless Earbuds",
        price=Decimal("3499.00"),
        stock=50,
    )
    proposal = AgentProposalInput(
        product_id="prod-earbuds",
        claimed_price=Decimal("1999.00"),  # Agent lies, claiming 1999
        quantity=1,
    )
    result = evaluate_policy(valid_mandate, product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.PRICE_MISMATCH
    assert result.authoritative_total == Decimal("3499.00")
    assert result.authoritative_price == Decimal("3499.00")
    assert result.claimed_price == Decimal("1999.00")


# Revoked mandate even if otherwise valid
def test_revoked_mandate_terminal_even_if_valid(valid_mandate, valid_product, valid_proposal, base_time):
    revoked_mandate = MandatePolicyInput(
        id=valid_mandate.id,
        user_id=valid_mandate.user_id,
        budget_total=valid_mandate.budget_total,
        budget_remaining=valid_mandate.budget_remaining,
        merchant_scope=valid_mandate.merchant_scope,
        max_transaction_amount=valid_mandate.max_transaction_amount,
        status="revoked",
        expires_at=valid_mandate.expires_at,
    )
    result = evaluate_policy(revoked_mandate, valid_product, valid_proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.MANDATE_REVOKED


def test_naive_expires_at_with_aware_current_time(valid_mandate, valid_product, valid_proposal):
    naive_mandate = MandatePolicyInput(
        id=valid_mandate.id,
        user_id=valid_mandate.user_id,
        budget_total=valid_mandate.budget_total,
        budget_remaining=valid_mandate.budget_remaining,
        merchant_scope=valid_mandate.merchant_scope,
        max_transaction_amount=valid_mandate.max_transaction_amount,
        status="active",
        expires_at=datetime(2026, 8, 26, 10, 0, 0),  # Naive datetime  # noqa: DTZ001
    )
    aware_current = datetime(2026, 8, 26, 12, 0, 0, tzinfo=timezone.utc)  # Aware datetime
    result = evaluate_policy(naive_mandate, valid_product, valid_proposal, current_time=aware_current)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.MANDATE_EXPIRED


def test_aware_expires_at_with_naive_current_time(valid_mandate, valid_product, valid_proposal):
    aware_mandate = MandatePolicyInput(
        id=valid_mandate.id,
        user_id=valid_mandate.user_id,
        budget_total=valid_mandate.budget_total,
        budget_remaining=valid_mandate.budget_remaining,
        merchant_scope=valid_mandate.merchant_scope,
        max_transaction_amount=valid_mandate.max_transaction_amount,
        status="active",
        expires_at=datetime(2026, 8, 26, 10, 0, 0, tzinfo=timezone.utc),  # Aware datetime
    )
    naive_current = datetime(2026, 8, 26, 12, 0, 0)  # Naive datetime  # noqa: DTZ001
    result = evaluate_policy(aware_mandate, valid_product, valid_proposal, current_time=naive_current)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.MANDATE_EXPIRED


def test_non_integer_quantity_float(valid_mandate, valid_product, base_time):
    proposal = AgentProposalInput(
        product_id="prod-001",
        claimed_price=Decimal("2799.00"),
        quantity=1.5,  # type: ignore
    )
    result = evaluate_policy(valid_mandate, valid_product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.DENY
    assert result.reason_code == ReasonCode.QUANTITY_INVALID


def test_both_budget_and_max_transaction_exceeded(valid_mandate, base_time):
    mandate_tight = MandatePolicyInput(
        id=valid_mandate.id,
        user_id=valid_mandate.user_id,
        budget_total=Decimal("1000.00"),
        budget_remaining=Decimal("1000.00"),
        merchant_scope="merchant-001",
        max_transaction_amount=Decimal("500.00"),
        status="active",
        expires_at=valid_mandate.expires_at,
    )
    product = ProductPolicyInput(
        id="prod-big",
        merchant_id="merchant-001",
        name="Big Item",
        price=Decimal("2000.00"),
        stock=10,
    )
    proposal = AgentProposalInput(
        product_id="prod-big",
        claimed_price=Decimal("2000.00"),
        quantity=1,
    )
    result = evaluate_policy(mandate_tight, product, proposal, current_time=base_time)
    assert result.decision == PolicyDecision.ESCALATE
    assert result.reason_code == ReasonCode.BUDGET_EXCEEDED
    assert result.authoritative_total == Decimal("2000.00")
