"""
IntentParser - LLM-based User Intent Classification
Uses Gemini to parse natural language into structured intents
"""

import os
import json
import logging
import re
from typing import Optional
import google.generativeai as genai

from backend.models.conversation_schemas import (
    Intent,
    IntentType,
    ModificationAction,
    ConversationSession
)

logger = logging.getLogger(__name__)


# ===========================
# 🔧 NORMALIZERS
# ===========================

def normalize_budget(value: str) -> Optional[float]:
    """
    Convert human-written budget into a numeric float.
    Supports:
    - 15 million, 15m
    - 15 juta, 15 jt, 15juta
    - 300k
    - Rp 15.000.000
    - 15000000
    """

    if not value:
        return None

    text = value.lower()
    text = text.replace("rp", "")
    text = text.replace("idr", "")
    text = text.replace(",", "")
    text = text.strip()

    # Remove dots except for thousand separators
    text = text.replace(".", "")

    # 15 million, 15 million rupiah
    if "million" in text:
        num = re.findall(r"\d+\.?\d*", text)
        if num:
            return float(num[0]) * 1_000_000

    # 15m
    if text.endswith("m"):
        try:
            return float(text[:-1]) * 1_000_000
        except:
            pass

    # 15 juta, 15jt
    if "juta" in text or "jt" in text:
        num = re.findall(r"\d+\.?\d*", text)
        if num:
            return float(num[0]) * 1_000_000

    # 300k
    if text.endswith("k"):
        try:
            return float(text[:-1]) * 1_000
        except:
            pass

    # plain number
    try:
        return float(text)
    except:
        return None


def normalize_travelers(value):
    """Handle: '2 travelers', '2 people', '2 pax', 'two people'"""
    if value is None:
        return None

    # Try digits directly
    if isinstance(value, (int, float)):
        return int(value)

    # Extract number from string
    m = re.findall(r"\d+", str(value))
    if m:
        return int(m[0])

    return None


# ===========================
# MAIN INTENT PARSER
# ===========================

class IntentParser:
    """Parse user messages into structured intents using LLM"""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=api_key)

        # FIX: use gemini-1.5-flash (has free quota)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

        logger.info("✅ IntentParser initialized with Gemini 2.5 Flash")

    # ------------------------------------------------------------------

    async def parse(self, message: str, session: ConversationSession) -> Intent:
        """Parse user message into structured intent"""

        context_str = self._build_context_string(session)
        prompt = self._build_prompt(message, context_str)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_output_tokens": 400,
                }
            )

            text = response.text.strip()

            # Remove accidental markdown
            if text.startswith("```"):
                text = text.strip("`").strip()
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            intent_data = json.loads(text)

            intent = Intent(
                type=IntentType(intent_data["type"]),
                action=(
                    ModificationAction(intent_data["action"])
                    if intent_data.get("action") and intent_data["type"] == "modify"
                    else None
                ),
                params=intent_data.get("params", {}),
                confidence=float(intent_data.get("confidence", 0.7)),
                raw_message=message
            )

            logger.info(
                f"Parsed intent: {intent.type.value} | "
                f"Action: {intent.action.value if intent.action else '-'} | "
                f"Confidence: {intent.confidence:.2f}"
            )

            return intent

        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")

            return Intent(
                type=IntentType.UNCLEAR,
                params={},
                confidence=0.0,
                raw_message=message
            )

    # ------------------------------------------------------------------

    def _build_context_string(self, session: ConversationSession) -> str:
        """Build human-readable context summary for LLM"""

        ctx = []
        ctx.append(f"State: {session.state.value}")

        if session.has_plan():
            ctx.append("Has active trip plan: YES")
            plan = session.trip_plan

            try:
                ctx.append(f"Destination: {plan.destination.destination.name}")
                ctx.append(f"Duration: {len(plan.itinerary.days)} days")
                ctx.append(f"Budget: Rp {plan.budget.breakdown.total:,.0f}")
            except:
                pass
        else:
            ctx.append("Has active trip plan: NO")

        ctx.append(f"Pending modifications: {len(session.modification_queue)}")
        ctx.append(f"Can undo: {session.can_undo()}")
        ctx.append(f"Can redo: {session.can_redo()}")

        return "\n".join(ctx)

    # ------------------------------------------------------------------

    def _build_prompt(self, message: str, context: str) -> str:
        """LLM instruction prompt"""

        return f"""
You are a travel planning assistant. Convert the user message into a structured JSON intent.

CONTEXT:
{context}

USER MESSAGE: "{message}"

INTENT TYPES:
- initial_plan
- modify
- apply
- query
- finalize
- undo
- redo
- show_history
- unclear

MODIFICATION ACTIONS:
- change_hotel
- change_flight
- change_meal
- add_activity
- remove_activity
- swap_days
- add_custom_item
- regenerate_component

Return ONLY JSON:
{{
  "type": "...",
  "action": "... or null",
  "params": {{ }},
  "confidence": 0.0–1.0
}}
No markdown. No explanation.
JSON only.
"""

    # ------------------------------------------------------------------

    def parse_trip_request_params(self, params: dict) -> Optional[dict]:
        """Convert loose parameters into TripRequest-compatible format"""

        from datetime import datetime, timedelta

        trip = {}

        # destination
        if "destination" in params:
            trip["destination"] = params["destination"]

        # origin
        if "origin" in params:
            trip["origin"] = params["origin"]

        # start_date / end_date
        if "start_date" in params:
            trip["start_date"] = params["start_date"]

        if "end_date" in params:
            trip["end_date"] = params["end_date"]

        # duration-based fallback
        if "duration_days" in params and "start_date" in trip and "end_date" not in trip:
            try:
                start = datetime.strptime(trip["start_date"], "%Y-%m-%d")
                end = start + timedelta(days=int(params["duration_days"]))
                trip["end_date"] = end.strftime("%Y-%m-%d")
            except:
                pass

        # Budget normalization
        if "budget" in params:
            budget = normalize_budget(params["budget"])
            if budget is not None:
                trip["budget"] = budget

        # Travelers
        if "travelers" in params:
            t = normalize_travelers(params["travelers"])
            if t is not None:
                trip["travelers"] = t

        return trip if trip else None


# ----------------------------------------------
# Singleton helper
# ----------------------------------------------

_intent_parser = None

def get_intent_parser() -> IntentParser:
    global _intent_parser
    if _intent_parser is None:
        _intent_parser = IntentParser()
    return _intent_parser
