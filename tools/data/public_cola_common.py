"""Shared normalization and validation for the public COLA metadata pipeline."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


LOCK_SCHEMA_VERSION = 1
INDEX_SCHEMA_VERSION = 1
TTB_ID_PATTERN = re.compile(r"^\d{14}$")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def dataset_digest(records: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_json(sorted(records, key=lambda item: item["ttb_id"]))).hexdigest()


def parse_registry_date(value: str | None) -> str | None:
    if not value:
        return None
    return datetime.strptime(value.strip(), "%m/%d/%Y").date().isoformat()


def validate_lock(lock: dict[str, Any]) -> list[dict[str, Any]]:
    if lock.get("schema_version") != LOCK_SCHEMA_VERSION:
        raise ValueError(f"unsupported lock schema: {lock.get('schema_version')!r}")
    records = lock.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("lock must contain at least one record")
    seen: set[str] = set()
    required = {
        "ttb_id", "registry_status", "completed_date", "permit_number", "serial_number",
        "product_type", "source", "brand_name", "origin_code", "origin_desc",
        "class_type_code", "class_type_desc", "applicant_name", "applicant_address",
        "application_type", "detail_url", "source_query_id",
    }
    for record in records:
        missing = sorted(required - record.keys())
        if missing:
            raise ValueError(f"record is missing fields: {', '.join(missing)}")
        ttb_id = record["ttb_id"]
        if not isinstance(ttb_id, str) or not TTB_ID_PATTERN.fullmatch(ttb_id):
            raise ValueError(f"invalid TTB ID: {ttb_id!r}")
        if ttb_id in seen:
            raise ValueError(f"duplicate TTB ID: {ttb_id}")
        seen.add(ttb_id)
        if record["product_type"] != "distilled_spirits":
            raise ValueError(f"non-spirits record in spirits lock: {ttb_id}")
        if record.get("abv") is not None and not 0 < float(record["abv"]) <= 100:
            raise ValueError(f"invalid ABV for {ttb_id}")
        if record.get("net_contents_ml") is not None and float(record["net_contents_ml"]) <= 0:
            raise ValueError(f"invalid net contents for {ttb_id}")
    expected_digest = lock.get("dataset_sha256")
    actual_digest = dataset_digest(records)
    if expected_digest != actual_digest:
        raise ValueError(f"dataset digest mismatch: expected {expected_digest}, got {actual_digest}")
    return records


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
