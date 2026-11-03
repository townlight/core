# CivicCore Longmont Ingestion Proof - 2026-05-21

Purpose: prove the shared CivicCore ingestion pipeline parses a real municipal PDF, chunks it, embeds every chunk with the local Ollama embedding model, and persists rows into the CivicCore `documents` and `document_chunks` pgvector schema.

Command class: local proof script using `testcontainers.postgres.PostgresContainer("pgvector/pgvector:pg17")`, `civiccore.migrations.runner.upgrade_to_head()`, and `civiccore.ingest.ingest_file()`.

Corpus:

- `C:\Users\scott\OneDrive\Desktop\Claude\longmont-code-corpus\Longmont, CO Code of Ordinances.pdf`
- Size: `12394756` bytes
- Codified through December 2025 per the PDF front matter

Output:

```text
LONGMONT-INGEST-PROOF
pdf=C:\Users\scott\OneDrive\Desktop\Claude\longmont-code-corpus\Longmont, CO Code of Ordinances.pdf
pdf_size_bytes=12394756
document_id=f7f625bc-7bb5-48dc-bbd3-6d1670b6dcae
document_status=completed
document_file_type=pdf
document_chunk_count=1789
documents_rows=1
document_chunks_rows=1789
embedded_chunks_rows=1789
parsed_chunk_chars=4566678
sample_chunk_index=0
sample_page_number=1
sample_token_count=296
sample_vector_dim=768
sample_chunk_text=SUPPLEMENT NO. 8 March 2026 CODE OF ORDINANCES City of LONGMONT, COLORADO Looseleaf Supplement This Supplement contains all ordinances deemed advisable to be included at this time through: Ordinance No. O-2025-83, enacted December 16, 2025. See the Code Comparative Table for further information. Remove Old Pages Insert New Pages lxv-lxxii lxv-lxxii Checklist of up-to-date pages Checklist of up-to-date pages (following Table of Contents) SH:5, SH:6 SH:5, SH:6 CD2:10.1-CD2:20.3 CD2:11-CD2:20.4 CD4:11-CD4:14 CD4:11-CD4:14 CD4:64.9, CD4:64.10 CD4:64.9, CD4:64.10 CD4:117, CD4:118 CD4:117, CD4:118 CD4:135 CD4:135, CD4:136 CD14:1, CD14:2 CD14:1, CD14:2 CD14:9, CD14:10 CD14:9, CD14:10 CD14:23-CD14:3
```

Acceptance facts:

- Real PDF parser path used: yes.
- Sentence-aware chunk rows persisted: `1789`.
- Ollama `nomic-embed-text` vectors persisted: `1789`.
- Vector dimensionality: `768`.
- Database schema: CivicCore baseline migration `documents` / `document_chunks` on pgvector PostgreSQL.

