"""Generate a stable visual QA sample of the Workflix certificate."""

import argparse
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.models import Certificate
from app.services.certificates import CertificateService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    certificate = Certificate(
        id=UUID("38a6af7c-3661-48e8-bdb1-ff2a96810610"),
        company_id=UUID("96c62883-e8d0-42cd-a8d3-0529919577be"),
        learning_path_id=UUID("48ee3cb4-aa49-4eae-a6e2-49bb4f7315d1"),
        user_id=UUID("41631650-923f-4d18-870a-88a1f0887f04"),
        code="WFX-1A2B3C4D5E6F7890A1B2C3D4E5F60718",
        user_full_name="Mariana Oliveira Santos",
        user_email="mariana@novatech.example.com",
        company_name="NovaTech",
        learning_path_title="Excelência em Segurança e Compliance",
        workload_minutes=225,
        issued_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(CertificateService.render_pdf(certificate))


if __name__ == "__main__":
    main()
