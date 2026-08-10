# OCR Benchmark Status

**Last run:** 2026-08-08  
**Purpose:** Record what is measured now and prevent smoke results from being mistaken for OCR accuracy claims.

## Current evidence

The benchmark harness generated nine deterministic synthetic label images (three product families, three variants each) and replayed their digest-keyed ground truth through the provider-neutral OCR contract.

| Metric | Fixture smoke result |
| --- | ---: |
| Images | 9 |
| Mean character error rate | 0.0000 |
| Mean word error rate | 0.0000 |
| Critical-field recall | 1.000 |
| Latency p50 | 0.0 ms |
| Latency p95 | 0.1 ms |

This validates dataset loading, normalized spans, metric calculation, report generation, and the application workstream's deterministic seam. It does **not** measure Tesseract or real enforcement-photo accuracy.

## Container verification

OrbStack provides the local Docker runtime. All three application images build successfully, the Compose services become healthy, and the API image includes Tesseract with English language data. The host itself does not install Tesseract, so host-only real-provider tests remain skipped by design.

A container smoke test of Tesseract 5.3.0 on one 900 × 1200 synthetic label completed OCR in 299 ms and the full request in 379 ms. It returned the correct application among three candidates but required user identification, so this is latency and integration evidence—not an accuracy pass or automatic-match result.

A two-image public COLA smoke test used the provenance-pinned Seven Fathoms front and back labels described in `fixtures/public-cola/manifest.json`. Tesseract completed OCR in 965 ms and the full request in 1,115 ms. The application automatically selected the corresponding isolated mock record with a 0.8843 score using brand, class/type, ABV, net contents, and origin evidence. All structured identity checks passed; OCR damage in the warning text produced a conservative warning mismatch. This remains a single-sample integration result, not an accuracy benchmark.

The public fixture set now contains seven records and sixteen images. A live local smoke pass confirmed that Crown Royal, Muralist, and Dark Arts return the expected real candidates from the 42-record metadata snapshot. Dark Arts correctly exposes two close approvals for reviewer resolution. Turtle Rabbit, 44° North, and Terra Brasilis are retained as hard typography/contrast cases that currently return no match. These observations are fixture checks, not an aggregate accuracy claim; the planned frozen corpus and benchmark report remain outstanding.

## Remaining release evidence

Before an accuracy or five-second release claim:

1. Run the Tesseract benchmark inside the API image with the Cloud Run limits (2 vCPU, 2 GiB).
2. Curate the pilot corpus defined in [OCR Optimization Plan](./ocr-optimization-plan.md), keeping captured, degraded, collision-heavy, and no-match slices separate.
3. Publish CER/WER, critical-field recall, top-3 retrieval, auto-link precision, false-Pass count, p50/p95 latency, and peak memory with sample counts.
4. Use the locked test set only after configuration and thresholds are selected.

Raw smoke artifacts are reproducible with:

```sh
python tools/ocr/generate_synthetic.py --output benchmark-results/synthetic-smoke --variants 3 --seed 20260806
python tools/ocr/benchmark.py --manifest benchmark-results/synthetic-smoke/manifest.json --provider fixture --json-out benchmark-results/synthetic-smoke/fixture-report.json --markdown-out benchmark-results/synthetic-smoke/fixture-report.md
```
