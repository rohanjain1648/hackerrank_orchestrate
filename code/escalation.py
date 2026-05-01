"""
Escalation engine — deterministic rules for when to escalate vs reply.
This runs BEFORE the LLM to catch clear-cut cases fast.
"""
import re
from typing import Tuple

from schemas import SupportTicket


# ── High-confidence escalation triggers ────────────────────────────────
_ESCALATION_RULES = [
    # Billing / payment / refund
    (r"\b(refund|reimburse|money\s+back|charge\s*back|overcharg|billing\s+error|wrong\s+charge)\b",
     "billing_and_payments", "Billing/refund request requires human review"),

    # Account access issues requiring admin intervention
    (r"\b(restore\s+my\s+access|account\s+(locked|blocked|disabled|suspended)|lost\s+access|removed?\s+my\s+seat)\b",
     "account_access", "Account access restoration requires admin intervention"),

    # Identity theft / fraud
    (r"\b(identity\s+(theft|stolen)|fraud(ulent)?|unauthorized\s+(transaction|charge|access))\b",
     "security", "Identity theft / fraud requires immediate human attention"),

    # Security vulnerabilities
    (r"\b(security\s+vulnerability|bug\s+bounty|found\s+a\s+(bug|vulnerability|exploit)|CVE-)\b",
     "security", "Security vulnerability reports must be escalated to security team"),

    # Test score / grading disputes
    (r"\b(increase\s+my\s+score|grade[d]?\s+(me\s+)?unfairly|review\s+my\s+(answers?|score|results?)|move\s+me\s+to\s+(the\s+)?next\s+round)\b",
     "assessment_integrity", "Score disputes require human review — agent cannot modify grades"),

    # Assessment rescheduling
    (r"\b(reschedul|postpone|alternative\s+date|extend\s+(the\s+)?deadline)\b.*\b(assessment|test|exam)\b",
     "screen", "Assessment rescheduling requests need recruiter/admin action"),

    # Subscription pause/cancel (for work accounts)
    (r"\b(pause|cancel|stop|suspend)\s+(our|the|my)?\s*(subscription|plan|account|hiring)\b",
     "subscription_management", "Subscription changes require account admin action"),

    # System-wide outages
    (r"\b(site\s+is\s+down|everything\s+is\s+(broken|down|failing)|all\s+requests?\s+(are\s+)?failing|completely?\s+(stopped|not\s+work))\b",
     "platform_status", "Potential system outage requires immediate engineering escalation"),

    # Requests the agent cannot fulfil
    (r"\b(fill\s+(in|out)\s+(the|our|my)\s+forms?|infosec\s+process|compliance\s+(form|questionnaire))\b",
     "enterprise_sales", "Administrative/compliance form requests need human handling"),

    # Payment/order ID issues
    (r"\b(order\s+ID|payment\s+ID|transaction\s+ID|cs_live_|pi_)\b",
     "billing_and_payments", "Payment issues with specific order IDs need human investigation"),
]

_COMPILED_RULES = [(re.compile(pat, re.IGNORECASE), area, reason)
                    for pat, area, reason in _ESCALATION_RULES]


def check_escalation_rules(ticket: SupportTicket) -> Tuple[bool, str, str]:
    """
    Check deterministic escalation rules.
    Returns (should_escalate, product_area, reason).
    """
    combined = f"{ticket.subject} {ticket.issue}"

    for pattern, area, reason in _COMPILED_RULES:
        if pattern.search(combined):
            return True, area, reason

    return False, "", ""


def is_vague_ticket(ticket: SupportTicket) -> bool:
    """Check if a ticket is too vague to resolve automatically."""
    text = f"{ticket.subject} {ticket.issue}".strip()
    # Very short with no specifics
    if len(text.split()) < 6:
        return True
    # Only generic complaints
    generic_patterns = [
        r"^(it'?s?\s+)?not\s+work(ing)?\s*[,.]?\s*(help)?$",
        r"^help(\s+me)?(\s+please)?$",
        r"^(please\s+)?fix(\s+it)?$",
    ]
    for pat in generic_patterns:
        if re.match(pat, text.strip(), re.IGNORECASE):
            return True
    return False
