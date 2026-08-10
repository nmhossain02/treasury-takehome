#!/usr/bin/env python3
"""Create a reviewed metadata lock from public TTB COLA Registry searches.

This command is intentionally separate from deployment. The Registry is mutable and its
legacy HTML is not a release dependency; maintainers review the generated lock before it is
used by the deterministic SQLite build.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_cola_common import LOCK_SCHEMA_VERSION, canonical_json, dataset_digest, parse_registry_date, read_json


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES = ROOT / "fixtures" / "public-cola" / "index-sources.json"
DEFAULT_OUTPUT = ROOT / "fixtures" / "public-cola" / "records.lock.json"
SEARCH_FORM = "https://www.ttbonline.gov/colasonline/publicSearchColasBasic.do"
SEARCH_ACTION = "https://www.ttbonline.gov/colasonline/publicSearchColasBasicProcess.do?action=search"
CSV_EXPORT = "https://www.ttbonline.gov/colasonline/publicSaveSearchResultsToFile.do?path=/publicSearchColasBasicProcess"
DETAIL_URL = "https://www.ttbonline.gov/colasonline/viewColaDetails.do?action=publicDisplaySearchBasic&ttbid={ttb_id}"
FORM_URL = "https://www.ttbonline.gov/colasonline/viewColaDetails.do?action=publicFormDisplay&ttbid={ttb_id}"
MAX_RESPONSE_BYTES = 5_000_000


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


class FormParser(HTMLParser):
    """Extract labeled form values and checked public-form attributes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fields: list[tuple[str, str]] = []
        self.checked: set[str] = set()
        self._capture: str | None = None
        self._depth = 0
        self._buffer: list[str] = []
        self._pending_label = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "input" and "checked" in attributes:
            alt = attributes.get("alt")
            if alt:
                self.checked.add(_clean(alt))
        if tag == "div" and attributes.get("class") in {"label", "boldlabel", "data"}:
            if self._capture is None:
                self._capture = attributes["class"]
                self._depth = 1
                self._buffer = []
            else:
                self._depth += 1
        elif self._capture is not None and tag == "div":
            self._depth += 1
        if self._capture == "data" and tag == "br":
            self._buffer.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._capture is None or tag != "div":
            return
        self._depth -= 1
        if self._depth:
            return
        raw_value = "".join(self._buffer)
        if self._capture == "data":
            value = "\n".join(_clean(line) for line in raw_value.splitlines() if _clean(line))
        else:
            value = _clean(raw_value)
        if self._capture in {"label", "boldlabel"}:
            self._pending_label = value
        elif self._capture == "data" and self._pending_label:
            self.fields.append((self._pending_label, value))
        self._capture = None
        self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._buffer.append(data)

    def value_after(self, label_prefix: str) -> str:
        prefix = label_prefix.casefold()
        for label, value in self.fields:
            if label.casefold().startswith(prefix):
                return value
        return ""


def _curl(cookie_jar: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        [
            "curl", "--fail", "--silent", "--show-error", "--location",
            "--connect-timeout", "10", "--max-time", "60",
            "--retry", "3", "--retry-all-errors", "--retry-delay", "1",
            "--cookie", str(cookie_jar), "--cookie-jar", str(cookie_jar),
            "--user-agent", "label-lens-public-cola-metadata/1.0", *arguments,
        ],
        check=True,
        capture_output=True,
        timeout=65,
    )
    if len(completed.stdout) > MAX_RESPONSE_BYTES:
        raise RuntimeError("TTB response exceeded the 5 MB metadata limit")
    return completed.stdout


def _search(cookie_jar: Path, query: dict[str, Any]) -> list[dict[str, str]]:
    _curl(cookie_jar, SEARCH_FORM)
    _curl(
        cookie_jar,
        "--data-urlencode", f"searchCriteria.dateCompletedFrom={query['completed_from']}",
        "--data-urlencode", f"searchCriteria.dateCompletedTo={query['completed_to']}",
        "--data-urlencode", "searchCriteria.productOrFancifulName=",
        "--data-urlencode", "searchCriteria.productNameSearchType=E",
        "--data-urlencode", "searchCriteria.classTypeFrom=",
        "--data-urlencode", "searchCriteria.classTypeTo=",
        "--data-urlencode", "searchCriteria.originCode=",
        SEARCH_ACTION,
    )
    raw_csv = _curl(cookie_jar, CSV_EXPORT)
    rows = list(csv.DictReader(io.StringIO(raw_csv.decode("utf-8-sig"))))
    expected_count = query.get("expected_export_records")
    if expected_count is not None and len(rows) != expected_count:
        raise RuntimeError(f"{query['id']} returned {len(rows)} records; expected {expected_count}")
    canonical_rows = sorted(
        ({str(key): value for key, value in row.items() if key is not None} for row in rows),
        key=lambda row: row["TTB ID"].strip("'").strip(),
    )
    digest = hashlib.sha256(canonical_json(canonical_rows)).hexdigest()
    expected_digest = query.get("expected_export_sha256")
    if expected_digest and digest != expected_digest:
        raise RuntimeError(f"{query['id']} changed: expected {expected_digest}, got {digest}")
    return rows


def _number(value: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
    return float(match.group()) if match else None


def _milliliters(value: str) -> float | None:
    amount = _number(value)
    if amount is None:
        return None
    normalized = value.casefold()
    if "liter" in normalized and "milliliter" not in normalized:
        amount *= 1000
    return amount


def _product_type(parser: FormParser) -> str | None:
    mapping = {
        "Type of Product: Distilled Spirits": "distilled_spirits",
        "Type of Product: Wine": "wine",
        "Type of Product: Malt Beverage": "malt_beverage",
    }
    return next((value for key, value in mapping.items() if key in parser.checked), None)


def _source(parser: FormParser) -> str:
    return "imported" if "Source of Product: Imported" in parser.checked else "domestic"


def _application_type(parser: FormParser) -> str:
    checked = " ".join(sorted(parser.checked)).casefold()
    if "distinctive liquor bottle" in checked:
        return "distinctive_liquor_bottle_approval"
    if "exemption" in checked:
        return "certificate_of_exemption"
    return "certificate_of_label_approval"


def _identity_fields(parser: FormParser, row: dict[str, str]) -> dict[str, str]:
    brand_name = parser.value_after("6. BRAND NAME") or row.get("Brand Name", "").strip()
    fanciful_name = parser.value_after("7. FANCIFUL NAME") or row.get("Fanciful Name", "").strip()
    origin_code = parser.value_after("OR") or row.get("Origin", "").strip()
    class_type_code = parser.value_after("CT") or row.get("Class/Type", "").strip()
    class_type_desc = parser.value_after("CLASS/TYPE DESCRIPTION") or row.get("Class/Type Desc", "").strip()
    if row.get("Origin", "").strip() == origin_code:
        origin_desc = row.get("Origin Desc", "").strip()
    elif row.get("Origin Desc", "").strip() == origin_code:
        # The legacy export does not quote commas inside some fanciful names. In that
        # case every following cell shifts right, but the printable form lets us prove
        # the alignment and recover the human-readable origin from the next cell.
        origin_desc = row.get("Class/Type", "").strip()
    else:
        origin_desc = ""
    return {
        "brand_name": brand_name,
        "fanciful_name": fanciful_name,
        "origin_code": origin_code,
        "origin_desc": origin_desc,
        "class_type_code": class_type_code,
        "class_type_desc": class_type_desc,
    }


def _record(cookie_jar: Path, query_id: str, row: dict[str, str]) -> dict[str, Any] | None:
    ttb_id = row["TTB ID"].strip().strip("'")
    form_html = _curl(cookie_jar, FORM_URL.format(ttb_id=ttb_id)).decode("utf-8", "replace")
    parser = FormParser()
    parser.feed(form_html)
    product_type = _product_type(parser)
    if product_type != "distilled_spirits":
        return None
    applicant = parser.value_after("8. NAME AND ADDRESS")
    applicant_parts = [part.strip() for part in re.split(r"\s{2,}|\n", applicant) if part.strip()]
    applicant_name = applicant_parts[0] if applicant_parts else ""
    applicant_address = ", ".join(applicant_parts[1:])
    status_value = parser.value_after("STATUS")
    status_match = re.search(r"STATUS IS\s+([A-Z ]+?)(?:\.|$)", status_value, re.I)
    registry_status = _clean(status_match.group(1) if status_match else status_value).casefold().replace(" ", "_")
    identity = _identity_fields(parser, row)
    return {
        "ttb_id": ttb_id,
        "registry_status": registry_status,
        "completed_date": parse_registry_date(row.get("Completed Date")),
        "approval_date": parse_registry_date(
            parser.value_after("23. DATE ISSUED") or parser.value_after("19. DATE ISSUED")
        ),
        "permit_number": row.get("Permit No.", "").strip(),
        "serial_number": row.get("Serial Number", "").strip(),
        "product_type": product_type,
        "source": _source(parser),
        "brand_name": identity["brand_name"],
        "fanciful_name": identity["fanciful_name"] or None,
        "origin_code": identity["origin_code"],
        "origin_desc": identity["origin_desc"],
        "class_type_code": identity["class_type_code"],
        "class_type_desc": identity["class_type_desc"],
        "applicant_name": applicant_name,
        "applicant_address": applicant_address,
        "abv": _number(parser.value_after("13. ALCOHOL CONTENT")),
        "net_contents_ml": _milliliters(parser.value_after("12. NET CONTENTS")),
        "application_type": _application_type(parser),
        "detail_url": DETAIL_URL.format(ttb_id=ttb_id),
        "source_query_id": query_id,
    }


def sync(sources_path: Path) -> dict[str, Any]:
    sources = read_json(sources_path)
    if sources.get("schema_version") != 1:
        raise ValueError("unsupported source schema")
    records: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="public-cola-metadata-") as temporary_directory:
        cookie_jar = Path(temporary_directory) / "cookies.txt"
        cookie_jar.touch(mode=0o600)
        for query in sorted(sources["queries"], key=lambda item: item["id"]):
            include_ids = set(query.get("include_ttb_ids", []))
            rows = _search(cookie_jar, query)
            available_ids = {row["TTB ID"].strip().strip("'") for row in rows}
            missing_ids = sorted(include_ids - available_ids)
            if missing_ids:
                raise RuntimeError(f"{query['id']} did not return pinned TTB IDs: {', '.join(missing_ids)}")
            for position, row in enumerate(rows, start=1):
                if position == 1 or position % 50 == 0:
                    print(f"enriching {query['id']}: {position}/{len(rows)} rows")
                ttb_id = row["TTB ID"].strip().strip("'")
                if include_ids and ttb_id not in include_ids:
                    continue
                record = _record(cookie_jar, query["id"], row)
                if record is not None:
                    records[record["ttb_id"]] = record
    ordered = [records[key] for key in sorted(records)]
    return {
        "schema_version": LOCK_SCHEMA_VERSION,
        "dataset_name": sources["dataset_name"],
        "snapshot_date": sources["snapshot_date"],
        "category": "distilled_spirits",
        "source": "TTB Public COLA Registry",
        "source_url": SEARCH_FORM,
        "source_queries": [query["id"] for query in sources["queries"]],
        "record_count": len(ordered),
        "dataset_sha256": dataset_digest(ordered),
        "records": ordered,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    lock = sync(arguments.sources)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(json.dumps(lock, indent=2, sort_keys=True).encode() + b"\n")
    print(f"wrote {arguments.output} ({lock['record_count']} distilled-spirits records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
