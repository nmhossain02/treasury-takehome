# label-ocr

`label-ocr` defines the OCR boundary used by the application and two initial
providers:

- `FixtureOcrProvider` returns deterministic results keyed by the SHA-256 of
  each input image. It is intended for application development and tests.
- `TesseractOcrProvider` invokes a fixed local Tesseract executable without a
  shell, parses TSV output, and observes the request deadline.

The package targets Python 3.12. Install it with:

```sh
python3.12 -m pip install -e 'packages/ocr[test]'
```

Run tests and the benchmark:

```sh
python3.12 -m pytest packages/ocr/tests
label-ocr-benchmark --manifest data/manifest.json --provider tesseract \
  --json-out artifacts/ocr-benchmark.json \
  --markdown-out artifacts/ocr-benchmark.md
```

The benchmark manifest is validated by `label_ocr.dataset` and documented by
`schemas/dataset-manifest.schema.json`. Generate a small deterministic
synthetic corpus with `tools/ocr/generate_synthetic.py`. Benchmark output
conforms to `schemas/benchmark-report.schema.json`.
