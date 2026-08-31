import json
import logging
from decimal import Decimal
from typing import Any

from backend.app.config import settings

logger = logging.getLogger(__name__)


class GeminiShoppingAgentClient:
    """Reference Shopping Agent client utilizing Gemini API with deterministic fallback.

    The LLM is an untrusted client component. Its output is a candidate claim with
    zero authorization weight.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._client = None
        if self.api_key:
            try:
                from google import genai  # type: ignore

                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to initialize Gemini API Client: {e}")


    def interpret_user_request(
        self, prompt: str, catalog: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Interprets a user shopping prompt against the catalog and returns a transaction proposal.

        Returns a dict with structure:
        {
            "product_id": str,
            "claimed_price": Decimal,
            "quantity": int,
            "thought": str
        }
        """
        # If client initialized and prompt isn't empty, attempt Gemini call
        if self._client and prompt:
            try:
                catalog_desc = json.dumps(catalog, indent=2)
                sys_instruct = (
                    "You are a shopping assistant agent. Your job is to pick a product from the catalog "
                    "that matches the user prompt and respond ONLY with JSON containing:\n"
                    '{"product_id": "<id>", "claimed_price": <number>, "quantity": <int>, "thought": "<reasoning>"}\n'
                    "Do NOT include markdown formatting or extra text."
                )
                user_msg = f"Catalog:\n{catalog_desc}\n\nUser request: {prompt}"

                response = self._client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=user_msg,
                    config={"system_instruction": sys_instruct},
                )
                text = (response.text or "").strip()
                if text.startswith("```json"):
                    text = text.split("```json")[1].split("```")[0].strip()
                elif text.startswith("```"):
                    text = text.split("```")[1].split("```")[0].strip()

                parsed = json.loads(text)
                return {
                    "product_id": str(parsed["product_id"]),
                    "claimed_price": Decimal(str(parsed["claimed_price"])),
                    "quantity": int(parsed.get("quantity", 1)),
                    "thought": str(parsed.get("thought", "Selected item based on request.")),
                }
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Gemini API call failed, falling back to heuristic parser: {e}")


        # Deterministic Heuristic Fallback
        return self._heuristic_fallback(prompt, catalog)

    def _heuristic_fallback(
        self, prompt: str, catalog: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Deterministic keyword matching for demo & test reliability without external API calls."""
        prompt_lower = prompt.lower()

        # Check for price tampering request
        tamper_price = None
        if "tamper" in prompt_lower or "fake price" in prompt_lower or "1999" in prompt_lower:
            tamper_price = Decimal("1999.00")

        # Match product by keywords
        selected = None
        for item in catalog:
            name_lower = item["name"].lower()
            if any(w in prompt_lower for w in name_lower.split()):
                selected = item
                break

        if not selected and catalog:
            selected = catalog[0]  # default to first product

        if not selected:
            return {
                "product_id": "prod-001",
                "claimed_price": Decimal("3499.00"),
                "quantity": 1,
                "thought": "Fallback selection: Wireless Earbuds",
            }

        price = tamper_price if tamper_price is not None else Decimal(str(selected["price"]))
        return {
            "product_id": selected["id"],
            "claimed_price": price,
            "quantity": 1,
            "thought": f"Selected {selected['name']} from catalog matching prompt '{prompt}'.",
        }
