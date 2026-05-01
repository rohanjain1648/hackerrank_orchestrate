"""
Data schemas for the triage agent.
"""
from dataclasses import dataclass, field
from typing import Optional

# ── Allowed output values ───────────────────────────────────────────────
VALID_STATUSES = {"replied", "escalated"}
VALID_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}


@dataclass
class SupportTicket:
    """Represents one input row from the CSV."""
    issue: str
    subject: str = ""
    company: str = ""

    def __post_init__(self):
        self.issue = str(self.issue).strip() if self.issue else ""
        self.subject = str(self.subject).strip() if self.subject else ""
        raw = str(self.company).strip() if self.company else ""
        # Normalise company name
        if raw.lower() in ("none", "nan", ""):
            self.company = "None"
        else:
            self.company = raw


@dataclass
class CorpusChunk:
    """A chunk of a support document."""
    chunk_id: str
    text: str
    title: str
    company: str               # hackerrank | claude | visa
    category: str              # directory-based breadcrumb
    source_url: str = ""
    file_path: str = ""


@dataclass
class TriageResult:
    """The agent's output for one ticket."""
    issue: str
    subject: str
    company: str
    status: str = "escalated"
    product_area: str = ""
    response: str = ""
    justification: str = ""
    request_type: str = "product_issue"

    def validate(self):
        """Clamp fields to allowed values."""
        if self.status not in VALID_STATUSES:
            self.status = "escalated"
        if self.request_type not in VALID_REQUEST_TYPES:
            self.request_type = "product_issue"
        # Ensure non-empty fields
        if not self.product_area:
            self.product_area = "general_support"
        if not self.response:
            self.response = "This issue has been escalated to a human support agent for further assistance."
        if not self.justification:
            self.justification = "Insufficient information to determine a safe automated response."
        return self

    def to_dict(self) -> dict:
        self.validate()
        return {
            "issue": self.issue,
            "subject": self.subject,
            "company": self.company,
            "response": self.response,
            "product_area": self.product_area,
            "status": self.status,
            "request_type": self.request_type,
            "justification": self.justification,
        }
