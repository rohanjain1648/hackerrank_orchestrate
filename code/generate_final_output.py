"""
Emergency script to generate a complete output.csv for all 29 tickets.
Handles rate limits by providing high-quality deterministic fallbacks
where the Gemini API is blocked.
"""
import os
import sys
import pandas as pd
from pathlib import Path

# Add code directory to path
sys.path.append(str(Path(__file__).parent))

from main import process_ticket
from retriever import Retriever
from indexer import CorpusIndex
from corpus_loader import load_corpus
from config import INPUT_CSV, OUTPUT_CSV

def generate():
    print("="*60)
    print("  GENERATING FINAL OUTPUT.CSV (29 TICKETS)")
    print("="*60)

    # 1. Setup RAG
    print("[1/3] Building index...")
    chunks = load_corpus()
    index = CorpusIndex()
    index.build(chunks)
    retriever = Retriever(index)

    # 2. Load Tickets
    print(f"[2/3] Reading tickets from {INPUT_CSV}...")
    df = pd.read_csv(INPUT_CSV)
    results = []

    # 3. Process each ticket
    print("[3/3] Processing tickets (with safe fallbacks)...")
    from schemas import SupportTicket
    for i, row in df.iterrows():
        ticket_num = i + 1
        print(f"  Processing Ticket {ticket_num}/29...")
        
        ticket = SupportTicket(
            issue=str(row.get('Issue', row.get('issue', ''))),
            subject=str(row.get('Subject', row.get('subject', ''))),
            company=str(row.get('Company', row.get('company', '')))
        )
        
        result = process_ticket(ticket, retriever, ticket_num, len(df))
        results.append(result.to_dict())

    # 4. Save to CSV
    output_df = pd.DataFrame(results)
    output_df.to_csv(OUTPUT_CSV, index=False)
    print("="*60)
    print(f"SUCCESS! Created {OUTPUT_CSV} with {len(output_df)} rows.")
    print("="*60)

if __name__ == "__main__":
    generate()
