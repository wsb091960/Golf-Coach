# GCIE case records, KAM and KM

The Golf Coach database uses additive SQLAlchemy tables for GCIE coaching cases, Knowledge Acquisition Model (KAM) source records, and structured Knowledge Model (KM) entries. Existing student/session tables and records remain separate.

- KAM sources begin as candidates and require a coach decision with review notes before they can be approved.
- KM entries begin as drafts, require an approved source record, and require separate coach approval before retrieval.
- The GCIE Knowledge Base screen supports source capture, review, structured entries, and keyword retrieval.
- The Coaching Assistant receives only approved KM entries that match the request. Retrieved entries include their source title, citation, evidence label, and source link.
- KM entries are for generalized, reusable instruction. Keep identifiable student details and raw session notes in that student’s session record. Do not paste identifying student data into general knowledge entries.
- Retrieval is transparent keyword matching. It is not embeddings, semantic RAG, or machine learning. Nothing is auto-approved or automatically learned from session notes.
- Original videos and images remain in media storage. The database stores structured text, source metadata, approval history, measurements, and references.
- The simulator’s MCP endpoint remains separate from student/session and KM database access.
- The current migration adds tables only; it does not modify or delete existing student/session columns or rows.
