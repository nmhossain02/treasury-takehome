#!/usr/bin/env python3
"""Build the deployable, metadata-only public COLA SQLite index offline."""

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from pathlib import Path

from public_cola_common import INDEX_SCHEMA_VERSION, normalize_text, read_json, validate_lock


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK = ROOT / "fixtures" / "public-cola" / "records.lock.json"
DEFAULT_OUTPUT = ROOT / "build" / "public-cola.sqlite3"
APPLICATION_ID = 0x4C4C4349  # ASCII-ish "LLCI": Label Lens COLA Index.


SCHEMA = """
CREATE TABLE dataset_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE cola_records (
    ttb_id TEXT PRIMARY KEY CHECK(length(ttb_id) = 14),
    registry_status TEXT NOT NULL,
    completed_date TEXT NOT NULL,
    approval_date TEXT,
    permit_number TEXT NOT NULL,
    serial_number TEXT NOT NULL,
    product_type TEXT NOT NULL CHECK(product_type = 'distilled_spirits'),
    source TEXT NOT NULL CHECK(source IN ('domestic', 'imported')),
    brand_name TEXT NOT NULL,
    fanciful_name TEXT,
    origin_code TEXT NOT NULL,
    origin_desc TEXT NOT NULL,
    class_type_code TEXT NOT NULL,
    class_type_desc TEXT NOT NULL,
    applicant_name TEXT NOT NULL,
    applicant_address TEXT NOT NULL,
    abv REAL,
    net_contents_ml REAL,
    application_type TEXT NOT NULL,
    detail_url TEXT NOT NULL,
    source_query_id TEXT NOT NULL,
    brand_name_normalized TEXT NOT NULL,
    fanciful_name_normalized TEXT NOT NULL,
    origin_desc_normalized TEXT NOT NULL,
    class_type_desc_normalized TEXT NOT NULL,
    search_text_normalized TEXT NOT NULL
) WITHOUT ROWID;

CREATE INDEX cola_records_brand_idx ON cola_records(brand_name_normalized);
CREATE INDEX cola_records_fanciful_idx ON cola_records(fanciful_name_normalized);
CREATE INDEX cola_records_class_idx ON cola_records(class_type_desc_normalized);
CREATE INDEX cola_records_origin_idx ON cola_records(origin_desc_normalized);
"""


def build(lock_path: Path, output_path: Path) -> None:
    lock = read_json(lock_path)
    records = validate_lock(lock)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output_path.parent, suffix=".sqlite3", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        connection = sqlite3.connect(temporary_path)
        try:
            connection.executescript(
                f"PRAGMA page_size=4096; PRAGMA application_id={APPLICATION_ID}; "
                f"PRAGMA user_version={INDEX_SCHEMA_VERSION}; PRAGMA journal_mode=OFF; {SCHEMA}"
            )
            metadata = {
                "schema_version": str(INDEX_SCHEMA_VERSION),
                "dataset_name": str(lock["dataset_name"]),
                "snapshot_date": str(lock["snapshot_date"]),
                "category": str(lock["category"]),
                "source": str(lock["source"]),
                "source_url": str(lock["source_url"]),
                "record_count": str(len(records)),
                "dataset_sha256": str(lock["dataset_sha256"]),
            }
            connection.executemany(
                "INSERT INTO dataset_meta(key, value) VALUES (?, ?)", sorted(metadata.items())
            )
            columns = [
                "ttb_id", "registry_status", "completed_date", "approval_date", "permit_number",
                "serial_number", "product_type", "source", "brand_name", "fanciful_name",
                "origin_code", "origin_desc", "class_type_code", "class_type_desc",
                "applicant_name", "applicant_address", "abv", "net_contents_ml",
                "application_type", "detail_url", "source_query_id",
            ]
            statement = (
                f"INSERT INTO cola_records ({', '.join(columns)}, brand_name_normalized, "
                "fanciful_name_normalized, origin_desc_normalized, class_type_desc_normalized, "
                f"search_text_normalized) VALUES ({', '.join('?' for _ in range(len(columns) + 5))})"
            )
            for record in sorted(records, key=lambda item: item["ttb_id"]):
                normalized = [
                    normalize_text(record.get("brand_name")),
                    normalize_text(record.get("fanciful_name")),
                    normalize_text(record.get("origin_desc")),
                    normalize_text(record.get("class_type_desc")),
                ]
                search_text = normalize_text(" ".join(str(record.get(column) or "") for column in columns))
                connection.execute(statement, [record.get(column) for column in columns] + normalized + [search_text])
            connection.commit()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"SQLite integrity check failed: {integrity}")
            connection.execute("VACUUM")
        finally:
            connection.close()
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    build(arguments.lock, arguments.output)
    print(f"built {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
