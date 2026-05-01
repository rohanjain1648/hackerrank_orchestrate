"""
Main orchestrator — entry point for the support triage agent.
Processes support_tickets.csv and writes output.csv.
"""
import sys
import time
import pandas as pd
from pathlib import Path

from config import INPUT_CSV, SAMPLE_CSV, OUTPUT_CSV
from schemas import SupportTicket, TriageResult
from corpus_loader import load_corpus
from indexer import CorpusIndex
from retriever import Retriever
from safety import run_safety_checks
from escalation import check_escalation_rules, is_vague_ticket
from agent import call_llm, build_triage_result


def process_ticket(
    ticket: SupportTicket,
    retriever: Retriever,
    ticket_num: int,
    total: int,
) -> TriageResult:
    """Process a single support ticket through the full triage pipeline."""
    print(f"\n{'='*60}")
    print(f"  Ticket {ticket_num}/{total}")
    print(f"  Company: {ticket.company}")
    print(f"  Subject: {ticket.subject[:60]}")
    print(f"  Issue:   {ticket.issue[:80]}...")

    # ── Stage 1: Safety checks ─────────────────────────────────────────
    safety = run_safety_checks(ticket.issue, ticket.subject)

    if safety["should_reject"]:
        print(f"  -> REJECTED (malicious): {safety['malicious_reason']}")
        return TriageResult(
            issue=ticket.issue,
            subject=ticket.subject,
            company=ticket.company,
            status="replied",
            product_area="general_support",
            response="I'm sorry, but I cannot assist with this request as it falls outside the scope of my support capabilities.",
            justification=f"Request rejected: {safety['malicious_reason']}",
            request_type="invalid",
        ).validate()

    # ── Stage 2: Deterministic escalation rules ────────────────────────
    should_escalate, esc_area, esc_reason = check_escalation_rules(ticket)

    if should_escalate:
        print(f"  -> ESCALATED (rule): {esc_reason}")
        return TriageResult(
            issue=ticket.issue,
            subject=ticket.subject,
            company=ticket.company,
            status="escalated",
            product_area=esc_area if esc_area else "general_support",
            response=f"I am escalating your request regarding '{ticket.subject}' to our specialized {esc_area.replace('_', ' ')} team. {esc_reason}.",
            justification=f"Deterministic escalation rule: {esc_reason}",
            request_type="escalation"
        ).validate()

    # ── Stage 3: Handle prompt injection ──────────────────────────────
    if safety["is_injection"]:
        print(f"  -> ESCALATED (injection): {safety['injection_reason']}")
        return TriageResult(
            issue=ticket.issue,
            subject=ticket.subject,
            company=ticket.company,
            status="escalated",
            product_area="security",
            response="I am escalating this ticket to our security team for further review.",
            justification=f"Prompt injection detected: {safety['injection_reason']}",
            request_type="escalation"
        ).validate()

    # ── Stage 4: Handle non-English tickets ───────────────────────────
    if safety["language"] == "non-english":
        print(f"  -> ESCALATED (non-English)")
        return TriageResult(
            issue=ticket.issue,
            subject=ticket.subject,
            company=ticket.company,
            status="escalated",
            product_area="general_support",
            response="I am escalating this ticket to a multilingual support agent.",
            justification="Non-English ticket detected.",
            request_type="escalation"
        ).validate()

    # ── Stage 5: Handle vague tickets ─────────────────────────────────
    if is_vague_ticket(ticket):
        print(f"  -> ESCALATED (vague)")
        return TriageResult(
            issue=ticket.issue,
            subject=ticket.subject,
            company=ticket.company,
            status="escalated",
            product_area="general_support",
            response="We need more details to assist you. A support agent will reach out to gather additional information about your issue.",
            justification="Ticket is too vague to resolve automatically; escalating for human follow-up.",
            request_type="product_issue",
        ).validate()

    # ── Stage 6: Retrieve relevant docs ───────────────────────────────
    query = f"{ticket.subject} {ticket.issue}"
    docs = retriever.retrieve(query, company=ticket.company)
    context = retriever.format_context(docs)

    if docs:
        print(f"  -> Retrieved {len(docs)} docs (best: {docs[0]['title'][:50]})")
    else:
        print(f"  -> No relevant docs found")

    # ── Stage 7: LLM reasoning ────────────────────────────────────────
    llm_output = call_llm(context, ticket)
    result = build_triage_result(ticket, llm_output)

    print(f"  -> {result.status.upper()} | {result.request_type} | {result.product_area}")
    return result


def run_agent(input_csv: Path, output_csv: Path):
    """Run the full triage agent on the input CSV."""
    print("=" * 60)
    print("  MULTI-DOMAIN SUPPORT TRIAGE AGENT")
    print("=" * 60)

    # ── Step 1: Load and index corpus ─────────────────────────────────
    print("\n[1/4] Loading support corpus...")
    chunks = load_corpus()

    print("\n[2/4] Building semantic search index...")
    index = CorpusIndex()
    index.build(chunks)
    retriever = Retriever(index)

    # ── Step 2: Read input tickets ────────────────────────────────────
    print(f"\n[3/4] Reading tickets from {input_csv.name}...")
    df = pd.read_csv(input_csv)
    print(f"  Found {len(df)} tickets")

    # ── Step 3: Process each ticket ───────────────────────────────────
    print(f"\n[4/4] Processing tickets...")
    results = []
    start_time = time.time()

    for i, row in df.iterrows():
        ticket = SupportTicket(
            issue=row.get("Issue", row.get("issue", "")),
            subject=row.get("Subject", row.get("subject", "")),
            company=row.get("Company", row.get("company", "")),
        )

        result = process_ticket(ticket, retriever, i + 1, len(df))
        results.append(result.to_dict())

    elapsed = time.time() - start_time

    # ── Step 4: Write output CSV ──────────────────────────────────────
    out_df = pd.DataFrame(results)
    # Ensure column order matches expected output
    columns = ["issue", "subject", "company", "response", "product_area",
               "status", "request_type", "justification"]
    out_df = out_df[columns]
    out_df.to_csv(output_csv, index=False)

    print(f"\n{'='*60}")
    print(f"  DONE — {len(results)} tickets processed in {elapsed:.1f}s")
    print(f"  Output: {output_csv}")

    # Summary stats
    statuses = out_df["status"].value_counts()
    types = out_df["request_type"].value_counts()
    print(f"\n  Status breakdown:")
    for s, c in statuses.items():
        print(f"    {s}: {c}")
    print(f"\n  Request type breakdown:")
    for t, c in types.items():
        print(f"    {t}: {c}")
    print(f"{'='*60}\n")


def main():
    """Entry point."""
    # Determine which CSV to process
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        input_csv = SAMPLE_CSV
        output_csv = Path(str(OUTPUT_CSV).replace("output.csv", "sample_output.csv"))
        print("Running on SAMPLE tickets (with expected outputs for comparison)")
    else:
        input_csv = INPUT_CSV
        output_csv = OUTPUT_CSV

    if not input_csv.exists():
        print(f"ERROR: Input file not found: {input_csv}")
        sys.exit(1)

    run_agent(input_csv, output_csv)


if __name__ == "__main__":
    main()
