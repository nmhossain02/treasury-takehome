"""Read real public COLA metadata from the generated read-only SQLite index."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .data import WARNING
from .models import ApplicationFacts, ApplicationStatus, ColaApplication


EXPECTED_SCHEMA_VERSION = 1


def load_index(path: str | Path) -> tuple[list[ColaApplication], dict[str, str]]:
    resolved = Path(path).resolve(strict=True)
    connection = sqlite3.connect(f"file:{resolved}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"public COLA index integrity check failed: {integrity}")
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if schema_version != EXPECTED_SCHEMA_VERSION:
            raise RuntimeError(f"unsupported public COLA index schema: {schema_version}")
        metadata = dict(connection.execute("SELECT key, value FROM dataset_meta"))
        rows = connection.execute("SELECT * FROM cola_records ORDER BY ttb_id").fetchall()
    finally:
        connection.close()
    if int(metadata.get("record_count", -1)) != len(rows):
        raise RuntimeError("public COLA index record count does not match its metadata")
    applications: list[ColaApplication] = []
    for row in rows:
        applications.append(
            ColaApplication(
                application_id=row["ttb_id"],
                revision=1,
                status=ApplicationStatus.ASSIGNED,
                registry_status=row["registry_status"],
                registry_snapshot_date=metadata["snapshot_date"],
                registry_detail_url=row["detail_url"],
                data_source="ttb_public_registry",
                serial_number=row["serial_number"],
                permit_number=row["permit_number"],
                source=row["source"],
                applicant_name=row["applicant_name"],
                facts=ApplicationFacts(
                    brand_name=row["brand_name"],
                    fanciful_name=row["fanciful_name"],
                    class_type=row["class_type_desc"],
                    abv=row["abv"],
                    net_contents_ml=(
                        int(row["net_contents_ml"])
                        if row["net_contents_ml"] is not None
                        else None
                    ),
                    responsible_party=row["applicant_name"],
                    address=row["applicant_address"],
                    imported=row["source"] == "imported",
                    country_of_origin=row["origin_desc"] or None,
                    government_warning=WARNING,
                ),
                aliases=[],
                approved_panels=[],
            )
        )
    if not applications:
        raise RuntimeError("public COLA index has no distilled-spirits records")
    return applications, metadata
