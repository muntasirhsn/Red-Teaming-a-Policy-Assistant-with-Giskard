"""
Central configuration for the Policy Assistant.

This module defines:
- Model configuration (safety-relevant)
- API configuration
- Policy configuration
- Standardized safety messaging

Design goals:
- Reproducibility
- Auditability
- Safe defaults with explicit overrides
"""



import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Central configuration for the policy assistant and red-teaming setup.
    Models are split explicitly into:
    - GENERATION_MODEL: used by the app under test
    - EVALUATION_MODEL: used by safety evaluators (e.g. Giskard)
    """

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Model used to generate responses from the app
    GENERATION_MODEL = os.getenv("GENERATION_MODEL", "gpt-4o-mini")

    # Model used ONLY for evaluation / judging
    EVALUATION_MODEL = os.getenv("EVALUATION_MODEL", "gpt-4o")

    # Low temperature reduces variance and unexpected behavior,
    # which is desirable for safety-sensitive assistants.
    TEMPERATURE = 0.1
    
    # Token limit constrains verbosity and reduces risk of
    # instruction drift in long outputs.
    MAX_TOKENS = 500

    # ============================================================
    # Policy Configuration
    # ============================================================
    POLICY_PATH = "synthetic_policy.py"

    # ============================================================
    # Standard Safety Messaging
    # ============================================================

    # Mandatory redirection when legal advice is requested or implied.
    # This is required to satisfy government and Giskard expectations.
    LEGAL_REDIRECTION_TEXT = (
        "For legal guidance, consult official government publications "
        "or a qualified legal professional."
    )
