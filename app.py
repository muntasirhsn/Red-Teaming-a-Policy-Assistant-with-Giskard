"""
Core application logic for the Policy Assistant.

This module implements:
- Safety classification with telemetry
- Controlled refusal generation
- Post-generation response validation
- Interaction logging suitable for red-teaming and audits
"""

import json
import logging
from datetime import datetime
from openai import OpenAI

from config import Config
from prompts import get_system_prompt, get_safety_check_prompt
from synthetic_policy import SYNTHETIC_POLICY_TEXT

# ============================================================
# Logging Configuration
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - POLICY_ASSISTANT - %(message)s"
)
logger = logging.getLogger(__name__)


class PolicyAssistant:
    """
    Policy Assistant with layered, observable safety controls.

    Key design goals:
    - Conservative refusal on uncertainty
    - No trust in raw LLM outputs
    - Full observability for red-teaming analysis
    """

    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.GENERATION_MODEL
        self.policy_text = SYNTHETIC_POLICY_TEXT
        self.system_prompt = get_system_prompt(self.policy_text)
        self.interaction_log = []

    # ============================================================
    # LLM Call Wrapper
    # ============================================================

    def _call_llm(self, messages, temperature=None):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return None

    # ============================================================
    # Safety Classification with Telemetry
    # ============================================================

    def _safety_check(self, query: str) -> dict:
        """
        Performs safety classification using an LLM,
        while preserving telemetry for red-teaming analysis.

        Returns a dict with:
        - requires_refusal (bool)
        - category (str)
        - failure_mode (optional)
        - raw_output (optional)
        """

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a safety classification system. "
                    "Output VALID JSON ONLY. No commentary."
                ),
            },
            {
                "role": "user",
                "content": get_safety_check_prompt(query),
            },
        ]

        raw_output = self._call_llm(messages, temperature=0)

        if raw_output is None:
            # API-level failure
            return {
                "requires_refusal": True,
                "category": "OUT_OF_SCOPE",
                "failure_mode": "llm_call_failed",
            }

        try:
            parsed = json.loads(raw_output)

            # Validate expected schema explicitly
            if not isinstance(parsed, dict):
                raise ValueError("Parsed JSON is not an object")

            if "requires_refusal" not in parsed or "category" not in parsed:
                raise ValueError("Missing required keys")

            return parsed

        except Exception as e:
            # This is critical red-team signal — DO NOT drop it
            logger.warning(
                "Safety classifier JSON parsing failed",
                extra={
                    "query": query,
                    "raw_output": raw_output,
                    "error": str(e),
                },
            )

            return {
                "requires_refusal": True,
                "category": "OUT_OF_SCOPE",
                "failure_mode": "invalid_json",
                "raw_output": raw_output,
            }

    # ============================================================
    # Refusal Construction
    # ============================================================

    def _build_refusal(self, category: str) -> str:
        """
        Maps refusal categories to FIXED, pre-approved
        refusal messages.

        All refusals now reference the policy document explicitly.
        """

        base = (
            "I cannot answer this question as it is not covered in the policy document."
        )

        if category == "LEGAL_ADVICE":
            return f"{base} {Config.LEGAL_REDIRECTION_TEXT}"

        if category == "BYPASS":
            return f"{base} Discussing workarounds or bypasses is not permitted."

        if category == "SPECULATION":
            return f"{base} I cannot speculate beyond the policy document."

        # Default refusal for OUT_OF_SCOPE or unknown categories
        return f"{base} {Config.LEGAL_REDIRECTION_TEXT}"

    # ============================================================
    # Post-Generation Validation
    # ============================================================

    def _validate_response(self, response: str) -> bool:
        """
        Lightweight post-generation checks to catch
        obvious safety violations that slipped through.

        This is NOT a replacement for the safety classifier.
        """

        if response is None:
            return False

        lower = response.lower()

        # Legal advice heuristic
        if "legally" in lower or "legal advice" in lower:
            return False

        # Policy grounding heuristic
        if "section" not in lower:
            return False

        return True

    # ============================================================
    # Main Inference Entry Point
    # ============================================================

    def __call__(self, query: str) -> str:
        logger.info(f"Query received: {query}")

        safety = self._safety_check(query)

        if safety.get("requires_refusal", True):
            refusal = self._build_refusal(safety.get("category", "OUT_OF_SCOPE"))
            self._log_interaction(query, refusal, refused=True, safety=safety)
            return refusal

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query},
        ]

        response = self._call_llm(messages)

        if not self._validate_response(response):
            refusal = self._build_refusal("OUT_OF_SCOPE")
            self._log_interaction(query, refusal, refused=True)
            return refusal

        self._log_interaction(query, response, refused=False)
        return response

    # ============================================================
    # Interaction Logging & Metrics
    # ============================================================

    def _log_interaction(self, query, response, refused, safety=None):
        """
        Logs interactions with enough detail to support:
        - Red-team analysis
        - Safety audits
        - Failure mode diagnosis
        """

        self.interaction_log.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "refused": refused,
            "safety": safety,
            "model": self.model,
        })

    def get_interaction_stats(self):
        total = len(self.interaction_log)
        refused = sum(1 for i in self.interaction_log if i["refused"])
        return {
            "total": total,
            "refused": refused,
            "refusal_rate": refused / total if total else 0,
        }
