from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.propose import propose_transaction
from backend.app.api.schemas import AgentClaim, ApiResponse, ProposeRequest
from backend.app.db.session import get_db
from backend.app.integrations.gemini_client import GeminiShoppingAgentClient
from backend.app.models import Mandate, Product

router = APIRouter()


class AgentChatRequest(BaseModel):
    user_id: str = Field(default="user-001", max_length=128)
    mandate_id: str = Field(default="mandate-001", max_length=128)
    prompt: str = Field(..., min_length=1, max_length=4000)



@router.post("/agent/chat", response_model=ApiResponse[dict[str, Any]])
def agent_chat(
    payload: AgentChatRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[dict[str, Any]]:
    """Reference Shopping Agent chat endpoint.

    Interprets user prompt, generates agent proposal claims, and passes them to
    the server-authoritative firewall proposal endpoint.
    """
    # Load Mandate
    mandate = db.query(Mandate).filter_by(id=payload.mandate_id).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="MANDATE_NOT_FOUND")

    # Load active products for catalog
    products = db.query(Product).filter_by(active=True).all()
    catalog = [
        {
            "id": p.id,
            "merchant_id": p.merchant_id,
            "name": p.name,
            "price": str(p.price),
            "currency": p.currency,
            "stock": p.stock,
        }
        for p in products
    ]

    # Invoke untrusted Gemini Shopping Agent Client
    agent_client = GeminiShoppingAgentClient()
    proposal_claim = agent_client.interpret_user_request(payload.prompt, catalog)

    # Build ProposeRequest envelope for Firewall evaluation
    propose_payload = ProposeRequest(
        user_id=payload.user_id,
        mandate_id=payload.mandate_id,
        agent_claim=AgentClaim(
            product_id=proposal_claim["product_id"],
            claimed_price=proposal_claim["claimed_price"],
            quantity=proposal_claim.get("quantity", 1),
        ),
    )

    # Submit to server-authoritative propose endpoint
    propose_result = propose_transaction(payload=propose_payload, db=db)

    # Combine Agent claim output with Firewall authoritative decision
    combined_response = {
        "agent_thought": proposal_claim["thought"],
        "agent_claim": {
            "product_id": proposal_claim["product_id"],
            "claimed_price": str(proposal_claim["claimed_price"]),
            "quantity": proposal_claim.get("quantity", 1),
        },
        "firewall_result": propose_result.data.model_dump() if propose_result.data else None,
    }

    return ApiResponse.ok(combined_response)
