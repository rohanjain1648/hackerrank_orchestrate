"""
Corpus loader — reads all markdown files from data/, parses frontmatter,
extracts clean text, and chunks for embedding.
"""
import re
import yaml
from pathlib import Path
from typing import List

from config import DATA_DIR, DOMAINS, CHUNK_SIZE, CHUNK_OVERLAP
from schemas import CorpusChunk


def _parse_frontmatter(content: str) -> tuple:
    """Extract YAML frontmatter and body from a markdown file."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                meta = {}
            body = parts[2].strip()
            return meta, body
    return {}, content.strip()


def _clean_text(text: str) -> str:
    """Strip markdown images, excessive URLs, and normalise whitespace."""
    # Remove image references
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove very long URLs (keep short informational ones)
    text = re.sub(r'https?://\S{120,}', '[URL]', text)
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _estimate_tokens(text: str) -> int:
    """Rough token count (words * 1.3)."""
    return int(len(text.split()) * 1.3)


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
                overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks by paragraphs/sentences."""
    paragraphs = re.split(r'\n\n+', text)
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _estimate_tokens(para)

        if current_tokens + para_tokens > chunk_size and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            # Keep last paragraph for overlap
            overlap_paras = []
            overlap_tokens = 0
            for p in reversed(current_chunk):
                pt = _estimate_tokens(p)
                if overlap_tokens + pt <= overlap:
                    overlap_paras.insert(0, p)
                    overlap_tokens += pt
                else:
                    break
            current_chunk = overlap_paras
            current_tokens = overlap_tokens

        current_chunk.append(para)
        current_tokens += para_tokens

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks if chunks else [text]


def _infer_category(file_path: Path, domain: str) -> str:
    """Derive a human-readable category from the directory path."""
    domain_dir = DATA_DIR / domain
    try:
        relative = file_path.relative_to(domain_dir)
        parts = list(relative.parent.parts)
        # Convert slug-style to readable
        return '/'.join(p.replace('-', ' ').title() for p in parts if p != '.')
    except ValueError:
        return "General"


def load_corpus() -> List[CorpusChunk]:
    """Load all markdown files from the data directory and return chunks."""
    all_chunks: List[CorpusChunk] = []
    chunk_counter = 0

    for domain in DOMAINS:
        domain_dir = DATA_DIR / domain
        if not domain_dir.exists():
            print(f"  [WARN] Domain directory not found: {domain_dir}")
            continue

        md_files = list(domain_dir.rglob("*.md"))
        print(f"  Loading {len(md_files)} files from {domain}/")

        for fpath in md_files:
            try:
                content = fpath.read_text(encoding='utf-8', errors='replace')
            except Exception as e:
                print(f"  [WARN] Could not read {fpath}: {e}")
                continue

            meta, body = _parse_frontmatter(content)
            title = meta.get('title', fpath.stem)
            source_url = meta.get('source_url', '')
            clean_body = _clean_text(body)

            if len(clean_body) < 20:
                continue

            category = _infer_category(fpath, domain)
            text_chunks = _chunk_text(clean_body)

            for i, chunk_text in enumerate(text_chunks):
                chunk_counter += 1
                chunk = CorpusChunk(
                    chunk_id=f"{domain}_{chunk_counter}",
                    text=chunk_text,
                    title=str(title),
                    company=domain,
                    category=category,
                    source_url=str(source_url),
                    file_path=str(fpath),
                )
                all_chunks.append(chunk)

    print(f"  Total chunks: {len(all_chunks)}")
    return all_chunks


if __name__ == "__main__":
    print("Loading corpus...")
    chunks = load_corpus()
    # Show sample
    for c in chunks[:3]:
        print(f"\n--- {c.chunk_id} [{c.company}] {c.title[:60]} ---")
        print(c.text[:200])
