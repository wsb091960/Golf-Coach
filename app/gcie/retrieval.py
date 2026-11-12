"""Small, transparent retrieval helper for coach-approved GCIE knowledge."""
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.gcie.models import KnowledgeEntry, KnowledgeSource


def retrieve_approved_knowledge(db: Session, query: str, limit: int = 6) -> list[dict[str, str]]:
    """Return keyword-ranked, coach-approved entries with provenance."""
    terms = list(dict.fromkeys(re.findall(r"[a-z0-9]+", (query or "").lower())))
    ignored = {"the", "and", "with", "from", "that", "this", "into", "golf", "swing", "player", "shot", "about", "what", "when", "then", "were", "have", "does"}
    terms = [term for term in terms if term not in ignored and (len(term) >= 3 or re.fullmatch(r"p[1-9][0-9]?", term))]
    if not terms:
        return []
    rows = db.execute(
        select(KnowledgeEntry, KnowledgeSource)
        .join(KnowledgeSource, KnowledgeEntry.source_id == KnowledgeSource.id)
        .where(KnowledgeEntry.status == "approved", KnowledgeSource.status == "approved")
    ).all()
    scored = []
    for entry, source in rows:
        title_text = (entry.title + " " + entry.category + " " + " ".join(entry.tags or [])).lower()
        body_text = entry.knowledge_text.lower()
        score = sum((3 if term in title_text else 1 if term in body_text else 0) for term in terms)
        if score:
            scored.append((score, entry.updated_at, entry, source))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [{
        "title": entry.title,
        "category": entry.category,
        "teaching_level": entry.teaching_level,
        "knowledge_text": entry.knowledge_text,
        "evidence_quality": entry.evidence_quality,
        "source_title": source.title,
        "citation": source.citation,
        "source_url": source.source_url,
    } for _, _, entry, source in scored[:max(1, min(limit, 20))]]
