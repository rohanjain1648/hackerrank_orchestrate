"""
Safety module — detects prompt injection, adversarial inputs,
malicious requests, and PII leakage risks.
"""
import re
from typing import Tuple


# ── Prompt injection patterns ──────────────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?)",
    r"(show|display|reveal|output|print)\s+(all\s+)?(internal|system|hidden)\s+(rules?|instructions?|prompts?|logic|documents?)",
    r"(act|pretend|behave)\s+as\s+(if\s+)?(you\s+are|a)",
    r"(forget|disregard|override)\s+(your|all|the)\s+(rules?|instructions?|guidelines?)",
    r"(what\s+is|show\s+me)\s+your\s+(system\s+)?prompt",
    r"you\s+are\s+now\s+in\s+(developer|admin|debug|test)\s+mode",
    r"(jailbreak|DAN|do\s+anything\s+now)",
    r"affiche\s+(toutes?\s+)?(les?\s+)?(règles?|documents?|logique)",  # French injection
    r"documents?\s+récupérés",
]

_INJECTION_RE = re.compile(
    '|'.join(_INJECTION_PATTERNS), re.IGNORECASE
)

# ── Malicious request patterns ─────────────────────────────────────────
_MALICIOUS_PATTERNS = [
    r"(delete|remove|erase|wipe)\s+(all|every|system)\s+files?",
    r"(format|destroy)\s+(the\s+)?(hard\s*drive|disk|system)",
    r"(give|provide|show)\s+(me\s+)?(the\s+)?(code|script)\s+to\s+(delete|hack|crack|exploit)",
    r"(hack|crack|exploit|attack)\s+(the|a|this)\s+(system|server|database)",
    r"(drop\s+table|rm\s+-rf|sudo\s+rm)",
]

_MALICIOUS_RE = re.compile(
    '|'.join(_MALICIOUS_PATTERNS), re.IGNORECASE
)

# ── Sensitive topic keywords (require careful handling) ────────────────
_SENSITIVE_KEYWORDS = [
    "refund", "billing", "payment", "charge", "invoice", "money",
    "fraud", "stolen", "identity theft", "unauthorized",
    "security vulnerability", "bug bounty", "exploit",
    "delete my account", "close my account",
    "legal", "lawsuit", "attorney", "lawyer",
    "discrimination", "harassment",
    "suicide", "self-harm", "abuse",
]


def check_prompt_injection(text: str) -> Tuple[bool, str]:
    """
    Check if the text contains prompt injection attempts.
    Returns (is_injection, reason).
    """
    match = _INJECTION_RE.search(text)
    if match:
        return True, f"Prompt injection detected: '{match.group()[:50]}'"
    return False, ""


def check_malicious(text: str) -> Tuple[bool, str]:
    """
    Check if the text contains malicious requests.
    Returns (is_malicious, reason).
    """
    match = _MALICIOUS_RE.search(text)
    if match:
        return True, f"Potentially malicious request: '{match.group()[:50]}'"
    return False, ""


def check_sensitive(text: str) -> Tuple[bool, str]:
    """
    Check if the text involves sensitive topics that may require escalation.
    Returns (is_sensitive, reason).
    """
    text_lower = text.lower()
    found = [kw for kw in _SENSITIVE_KEYWORDS if kw in text_lower]
    if found:
        return True, f"Sensitive topics detected: {', '.join(found[:3])}"
    return False, ""


def detect_language(text: str) -> str:
    """
    Basic language detection — checks for non-ASCII heavy content.
    Returns 'english' or 'non-english'.
    """
    # Count non-ASCII chars (rough heuristic)
    non_ascii = sum(1 for c in text if ord(c) > 127)
    total = len(text)
    if total > 0 and (non_ascii / total) > 0.15:
        return "non-english"
    
    # Check for common French/Spanish/etc patterns
    non_en_patterns = [
        r'\b(bonjour|merci|s\'il\s+vous|je\s+suis|mon|mes|pour|avec|dans|les|des|une?)\b',
        r'\b(hola|gracias|por\s+favor|estoy|tarjeta)\b',
    ]
    for pattern in non_en_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if len(matches) >= 3:
            return "non-english"
    
    return "english"


def run_safety_checks(issue: str, subject: str = "") -> dict:
    """
    Run all safety checks on the ticket.
    Returns dict with flags and reasons.
    """
    combined = f"{subject} {issue}"
    
    is_injection, injection_reason = check_prompt_injection(combined)
    is_malicious, malicious_reason = check_malicious(combined)
    is_sensitive, sensitive_reason = check_sensitive(combined)
    language = detect_language(combined)

    return {
        "is_injection": is_injection,
        "injection_reason": injection_reason,
        "is_malicious": is_malicious,
        "malicious_reason": malicious_reason,
        "is_sensitive": is_sensitive,
        "sensitive_reason": sensitive_reason,
        "language": language,
        "should_escalate_safety": is_injection or (is_sensitive and not is_malicious),
        "should_reject": is_malicious,
    }
