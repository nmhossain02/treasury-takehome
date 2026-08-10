from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "data"))

from build_public_cola_index import build  # noqa: E402
from sync_public_cola_metadata import FormParser, _identity_fields  # noqa: E402


LOCK = ROOT / "fixtures" / "public-cola" / "records.lock.json"
SAMPLE_MANIFEST = ROOT / "fixtures" / "public-cola" / "manifest.json"


def test_locked_index_build_is_byte_deterministic_and_metadata_only(tmp_path: Path) -> None:
    first = tmp_path / "first.sqlite3"
    second = tmp_path / "second.sqlite3"
    build(LOCK, first)
    build(LOCK, second)

    assert first.read_bytes() == second.read_bytes()
    connection = sqlite3.connect(first)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT value FROM dataset_meta WHERE key='record_count'").fetchone()[0] == "42"
        record = connection.execute(
            "SELECT ttb_id, brand_name, registry_status, abv, net_contents_ml "
            "FROM cola_records WHERE ttb_id = '11038001000659'"
        ).fetchone()
        assert record == ("11038001000659", "SEVEN FATHOMS", "surrendered", 40.0, 750.0)
        shifted_export_record = connection.execute(
            "SELECT brand_name, fanciful_name, origin_code, origin_desc, class_type_code, class_type_desc "
            "FROM cola_records WHERE ttb_id = '24359001000182'"
        ).fetchone()
        assert shifted_export_record == (
            "MASHBUILD",
            "SIGNATURE FINISH, DOUBLE BARRELED",
            "29",
            "MISSOURI",
            "649",
            "OTHER SPECIALTIES & PROPRIETARIES",
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(cola_records)")}
        assert not {"image", "image_url", "attachment", "ocr_text"} & columns
    finally:
        connection.close()


def test_build_rejects_a_modified_lock(tmp_path: Path) -> None:
    tampered = json.loads(LOCK.read_text())
    tampered["records"][0]["brand_name"] = "Changed"
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(tampered))

    with pytest.raises(ValueError, match="dataset digest mismatch"):
        build(path, tmp_path / "invalid.sqlite3")


def test_public_image_samples_reference_records_without_entering_the_index() -> None:
    lock = json.loads(LOCK.read_text())
    manifest = json.loads(SAMPLE_MANIFEST.read_text())
    record_ids = {record["ttb_id"] for record in lock["records"]}
    sample_ids = [sample["ttb_id"] for sample in manifest["samples"]]

    assert len(sample_ids) == len(set(sample_ids))
    assert set(sample_ids) <= record_ids
    assert all(sample["attachments"] for sample in manifest["samples"])


def test_form_identity_recovers_columns_shifted_by_an_unquoted_comma() -> None:
    parser = FormParser()
    parser.fields = [
        ("6. BRAND NAME", "MASHBUILD"),
        ("7. FANCIFUL NAME", "SIGNATURE FINISH, DOUBLE BARRELED"),
        ("OR", "29"),
        ("CT", "649"),
        ("CLASS/TYPE DESCRIPTION", "OTHER SPECIALTIES & PROPRIETARIES"),
    ]
    shifted_row = {
        "Fanciful Name": "SIGNATURE FINISH",
        "Brand Name": "DOUBLE BARRELED",
        "Origin": "MASHBUILD",
        "Origin Desc": "29",
        "Class/Type": "MISSOURI",
        "Class/Type Desc": "649",
    }

    assert _identity_fields(parser, shifted_row) == {
        "brand_name": "MASHBUILD",
        "fanciful_name": "SIGNATURE FINISH, DOUBLE BARRELED",
        "origin_code": "29",
        "origin_desc": "MISSOURI",
        "class_type_code": "649",
        "class_type_desc": "OTHER SPECIALTIES & PROPRIETARIES",
    }
