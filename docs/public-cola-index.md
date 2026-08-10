# Public COLA Metadata Index

## Purpose

Compare OCR observations with real, public TTB COLA metadata without writing to a government system or making the running application depend on the legacy Registry website.

The index contains metadata only. It does not download or store registry label images, user uploads, or OCR output. The images under `fixtures/demo/` remain independent test inputs.

## Reproducible flow

Two steps deliberately separate mutable upstream data from releases:

1. `make cola-index-sync` reads bounded searches from the [TTB Public COLA Registry](https://www.ttb.gov/online-services/public-cola-registry), downloads each CSV result, loads the public printable form for every returned row, keeps only rows whose form identifies them as distilled spirits, normalizes the fields, and writes `fixtures/public-cola/records.lock.json`.
2. `make cola-index` performs no network access. It validates the lock digest and builds `build/public-cola.sqlite3` with a fixed schema, sorted inserts, integrity check, and deterministic vacuum.

Container builds run only step 2. A release therefore cannot change because TTB data changed or the Registry was unavailable.

## Source controls

`fixtures/public-cola/index-sources.json` defines:

- the Registry completion-date query;
- expected result count and canonical CSV digest;
- the reviewed snapshot date.

Synchronization fails closed if the result count or canonical export digest changes. Optional explicit TTB IDs may narrow a query for a focused fixture. Updating a snapshot requires intentionally changing the source definition, rerunning synchronization, and reviewing the lock diff.

The lock records provenance plus TTB ID, public status, completion and approval dates, permit and serial numbers, product source, brand and fanciful names, origin, class/type, applicant, ABV, net contents, application type, and official detail URL. Fields remain null when the public form does not expose a structured value; label-image OCR is not used to manufacture registry metadata. The Registry's CSV export is documented in the [Public COLA Registry manual](https://www.ttb.gov/system/files/images/pdfs/labeling/colas_ol_pcr_um.pdf).

## Runtime boundary

The generated SQLite file is copied into the COLA sidecar image and opened with SQLite `mode=ro&immutable=1`. Public registry status remains immutable. Approve/deny actions are local review state and never alter the index or contact TTB.

All locked records remain searchable even when the public form omits structured ABV or net contents. Missing facts are represented as null, and the corresponding verification checks are marked `unable`; records are never dropped and values are never inferred from label artwork during the metadata build.

The reviewed snapshot contains all 42 distilled-spirits records found in one digest-pinned, 346-row completion-date export: 41 approved records and one surrendered record. This exceeds the initial 30-record prototype target while remaining comfortably below the Registry's documented 500-result export limit. Expand coverage with additional bounded, digest-pinned queries; do not silently broaden a query past that limit.

## Verification

```bash
make cola-index
sqlite3 build/public-cola.sqlite3 'PRAGMA integrity_check; SELECT * FROM dataset_meta ORDER BY key;'
make test-python
```

The tests build the database twice and require byte-identical output, verify the logical dataset digest and SQLite integrity, and assert that the schema contains no image or OCR payload columns.
