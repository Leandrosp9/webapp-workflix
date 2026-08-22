# ADR 007: Hybrid OCR and versioned document acknowledgements

- Status: Accepted
- Date: 2026-08-22

## Context

Corporate policies may be scanned PDFs without a usable text layer, and completion percentages alone do not prove which exact policy version an employee acknowledged. OCR is CPU-expensive and acknowledgement evidence must survive later document revisions.

## Decision

Workers first extract native page text with PyMuPDF and invoke local Tesseract only for pages below the configured native-text threshold. OCR work has page, language, and DPI limits, and every page persists its extraction provenance.

Employee acknowledgement is a separate, idempotent transaction tied to the latest assigned document version. The evidence snapshots the user identity, fixed attestation, filename, monotonic version, SHA-256 checksum, and server timestamp. New PDF versions create a new pending state without updating prior evidence, and trainings with evidence cannot be deleted.

## Consequences

Worker images are larger and need Tesseract language packages, but the API remains responsive and OCR adds no cloud or generative-AI cost. Evidence storage grows with employee/version pairs and requires explicit retention policy before tenant offboarding. Rich exports and organization-wide audit event streams remain separate capabilities.
