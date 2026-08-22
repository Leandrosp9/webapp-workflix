# ADR 008: Learning paths, immutable certificates, and read-model reports

- Status: Accepted
- Date: 2026-08-22

## Context

Workflix needs guided multi-content journeys, completion proof, and management visibility without duplicating the training player, introducing paid services, or weakening tenant boundaries. Certificate issuance must tolerate repeated completion events and reports must be based on operational data rather than fake dashboard values.

## Decision

Model a learning path as an ordered set of required or optional existing trainings. Published paths freeze their item order and path assignment creates any missing underlying training assignments in the same transaction. Employee availability is sequential for guidance, while the existing assignment remains the authorization source for each training.

When all required items reach 100%, issue one certificate per employee/path. The row snapshots employee, company, path title, workload, server issue time, and a high-entropy verification code. A database uniqueness constraint plus a nested transaction makes repeated evaluation idempotent. Authenticated users download a stateless ReportLab PDF; the verification endpoint discloses only the certificate's public proof fields.

Management analytics and CSV exports are read models over company-scoped assignments, progress, paths, users, and certificates. CSV cells that can be interpreted as spreadsheet formulas are escaped before UTF-8 BOM encoding.

## Consequences

- Paths reuse existing content, authorization, progress, and quiz workflows.
- Certificate evidence survives later user or path-name edits because relevant values are snapshotted.
- Report results remain auditable against source rows and consume no AI quota.
- Published path content cannot currently be versioned; a future curriculum revision should create a new path version instead of mutating issued-certificate history.
- Sequential locking is a product cue, not a separate authorization boundary, because the same training may be assigned independently.
