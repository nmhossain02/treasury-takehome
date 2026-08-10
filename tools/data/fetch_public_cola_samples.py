#!/usr/bin/env python3
"""Download pinned public COLA label samples with provenance and hash checks."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "fixtures" / "public-cola" / "manifest.json"
OUTPUT = ROOT / "fixtures" / "public-cola" / "images"
SEARCH_FORM = "https://www.ttbonline.gov/colasonline/publicSearchColasBasic.do"
SEARCH_ACTION = "https://www.ttbonline.gov/colasonline/publicSearchColasBasicProcess.do?action=search"
ATTACHMENT = "https://www.ttbonline.gov/colasonline/publicViewAttachment.do"
MAX_DOWNLOAD_BYTES = 5_000_000


def _curl(cookie_jar: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        [
            "curl", "--fail", "--silent", "--show-error", "--location",
            "--connect-timeout", "10", "--max-time", "60",
            "--retry", "3", "--retry-all-errors", "--retry-delay", "1",
            "--cookie", str(cookie_jar),
            "--cookie-jar", str(cookie_jar),
            "--user-agent", "treasury-takehome-fixture-fetcher/1.0",
            *arguments,
        ],
        check=True,
        capture_output=True,
        timeout=65,
    )
    content = completed.stdout
    if len(content) > MAX_DOWNLOAD_BYTES:
        raise RuntimeError("TTB response exceeded the 5 MB fixture limit")
    return content


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="public-cola-") as temporary_directory:
        cookie_jar = Path(temporary_directory) / "cookies.txt"
        cookie_jar.touch(mode=0o600)
        for sample in manifest["samples"]:
            # The legacy registry resolves attachments within a search session.
            _curl(cookie_jar, SEARCH_FORM)
            search_date = sample["completed_search_date"]
            _curl(
                cookie_jar,
                "--data-urlencode", f"searchCriteria.dateCompletedFrom={search_date}",
                "--data-urlencode", f"searchCriteria.dateCompletedTo={search_date}",
                "--data-urlencode", "searchCriteria.productOrFancifulName=",
                "--data-urlencode", "searchCriteria.productNameSearchType=E",
                "--data-urlencode", "searchCriteria.classTypeFrom=",
                "--data-urlencode", "searchCriteria.classTypeTo=",
                "--data-urlencode", "searchCriteria.originCode=",
                SEARCH_ACTION,
            )
            _curl(cookie_jar, sample["detail_url"])
            _curl(
                cookie_jar,
                f"https://www.ttbonline.gov/colasonline/viewColaDetails.do?action=publicFormDisplay&ttbid={sample['ttb_id']}",
            )

            destination = OUTPUT / sample["ttb_id"]
            destination.mkdir(parents=True, exist_ok=True)
            for attachment in sample["attachments"]:
                content = _curl(
                    cookie_jar, "--get",
                    "--data-urlencode", f"filename={attachment['registry_filename']}",
                    "--data-urlencode", "filetype=l", ATTACHMENT,
                )
                digest = hashlib.sha256(content).hexdigest()
                if not (content.startswith(b"\xff\xd8\xff") or content.startswith(b"\x89PNG\r\n\x1a\n")):
                    raise RuntimeError(f"TTB returned unsupported image content for {attachment['role']}")
                if digest != attachment["sha256"]:
                    raise RuntimeError(
                        f"hash changed for {attachment['role']}: expected {attachment['sha256']}, got {digest}"
                    )
                target = destination / attachment["output_filename"]
                with tempfile.NamedTemporaryFile(dir=destination, delete=False) as temporary:
                    temporary.write(content)
                    temporary_path = Path(temporary.name)
                temporary_path.replace(target)
                print(f"downloaded {target.relative_to(ROOT)} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
