# OCR Optimization and Validation Plan

**Status:** Harness and local adapter implemented; corpus optimization pending  
**Last updated:** 2026-08-08  
**Depends on:** [Requirements](./requirements.md) and [Implementation plan](./implementation-plan.md)  
**Current evidence:** [OCR Benchmark Status](./benchmark-status.md)

## 1. Outcome and boundary

Develop a local OCR workflow that extracts traceable text from an arbitrary set of enforcement-item photos while fitting inside the application's five-second response target. Local Tesseract is the first production strategy. The application may develop in parallel against a deterministic OCR stub; neither application logic nor API schemas may depend on Tesseract.

This workstream owns image preparation, OCR execution, normalized text spans, OCR benchmarks, and recommendations for safe image-work limits. It does not own COLA search scoring, rule evaluation, the user interface, or agent decisions, but it must measure how OCR errors affect application identification and compliance checks.

### Definition of done

- Tesseract and the deterministic stub pass the same provider-conformance suite.
- Warm OCR latency is at or below **2.9 seconds p95** for the documented representative aggregate image envelope on named target-like hardware.
- The complete integrated request remains at or below **5.0 seconds p95** on that envelope.
- OCR accuracy and downstream identification metrics meet the release gates in Section 8.
- Timeouts, unreadable text, and contradictory photos produce partial/uncertain results rather than guessed text or a false match.
- The benchmark corpus, provenance, configurations, raw results, and known limitations are reproducible and documented.

The image envelope is an empirical release artifact, not a semantic photo-count limit. Requests outside it remain accepted only while aggregate byte, decoded-pixel, memory, concurrency, and deadline safeguards permit useful work.

## 2. Parallel delivery model

The application and OCR tracks share only a stable contract and test fixtures.

| Application track | OCR track |
| --- | --- |
| Implements intake, identification, rules, evidence UI, and mock decisions. | Builds the corpus, benchmark harness, preprocessing pipeline, and Tesseract adapter. |
| Uses the deterministic OCR stub for automated application tests and explicit fixture scenarios. | Uses a small matcher evaluation harness to measure downstream effects without the application UI. |
| Runs provider-conformance tests in CI. | Publishes versioned OCR fixtures and performance/accuracy reports. |

Integrate at milestone boundaries rather than waiting for OCR optimization to finish. The stub must support clean, low-confidence, partial, timeout, duplicate-photo, conflicting-photo, and provider-failure outcomes.

## 3. Provider-neutral contract

```text
OcrProvider.recognize(request: OcrRequest, deadline: ProcessingDeadline) -> OcrOutcome
```

`OcrRequest` contains immutable image IDs, decoded or normalized image references, language hints supplied by trusted configuration, and a monotonic deadline. `OcrOutcome` contains:

- `status`: `success`, `partial`, or `failed`;
- ordered `TextSpan` values with UTF-8 text, provider confidence, image ID, normalized bounding box, line/block order, and optional rotation;
- per-image warnings and stable failure codes;
- total and per-stage timings;
- a non-sensitive strategy/version trace.

Coordinates use `[0,1]` image-relative values and remain tied to the original accepted image after any transform. Provider confidence is retained but is not treated as calibrated probability. Domain code consumes only normalized spans and outcomes; it must not import OCR libraries, branch on provider names, or parse provider payloads.

Provider selection, ordering, model paths, and timeouts are trusted startup configuration. Requests cannot select an engine or endpoint. Every adapter must honor cancellation/deadlines, return partial work safely, avoid content logging, and pass the same contract tests.

### Deterministic development stub

The stub maps fixture image digests to versioned `OcrOutcome` JSON. It can inject bounded delays and stable errors without invoking OCR. Fixture JSON is reviewed like source code and includes evidence boxes, confidence, ordering, and expected warnings. This gives the application track fast, repeatable tests while preserving a drop-in path to Tesseract.

## 4. Corpus plan

### Sources and coverage

Build the corpus in stages:

1. **Public approved-label material:** use the [TTB COLA Public Registry](https://www.ttb.gov/regulated-commodities/labeling/cola-public-registry) and other TTB-published examples for label text, layouts, and deliberate near-match groups.
2. **Controlled captures:** photograph printed or synthetic distilled-spirits labels under representative distance, angle, curvature, rotation, glare, shadow, blur, background, and resolution conditions. Include front, back, neck, partial, overlapping, repeated, and irrelevant views.
3. **Synthetic variants:** add deterministic geometric and photometric transformations to isolate failure modes. Synthetic variants supplement rather than replace captured photos.
4. **Adversarial identification cases:** include the same brand across class/type, ABV, volume, applicant, and imported/domestic variants; near-identical names; absent records; and contradictory photos.

Start with a pilot sufficient to expose dominant errors (at least 75 application families and 300 photos), then size the locked evaluation set from the claimed error bound. For example, claiming a false-link rate below 0.5% requires roughly 600 independent automatic-link decisions with zero observed false links under the rule-of-three approximation; otherwise report the exact confidence interval and narrow the claim.

### Provenance manifest

Every source image and derived artifact has an immutable ID and manifest entry containing:

- source URL or capture owner, retrieval/capture date, and permitted use;
- public, controlled-capture, or synthetic classification;
- source application/family and collision-group IDs;
- original file digest, dimensions, media type, and transformation lineage;
- redaction/restriction notes and annotator/reviewer versions;
- assigned dataset split and reason for any exclusion.

Do not place unreviewed third-party images, personal data, or unclear-license material in the repository. Keep redistributable fixtures small; store restricted corpus data outside source control and publish a reproducible acquisition/derivation manifest.

## 5. Annotation schema and quality

Annotate at the image, region, span, field, and enforcement-item levels.

| Level | Required labels |
| --- | --- |
| Enforcement item | Ground-truth application ID or `no_match`; collision group; constituent image IDs. |
| Image | Inferred panel/view role or `unknown`; quality conditions; duplicate/overlap group; orientation. |
| Text region | Polygon or box; line/block order; `legible`, `partially_legible`, or `illegible`. |
| Text span | Exact visible transcription preserving punctuation/case; normalized comparison text stored separately; ignore reason where appropriate. |
| Field | Brand/fanciful name, class/type, ABV/proof, net contents, responsible party/address, origin, government warning, visible identifier, or `other`; canonical parsed value when applicable. |

Never invent obscured characters. Mark uncertainty at the smallest region possible. Preserve exact transcription independently from normalization so warning-text and formatting checks remain testable.

Write annotation guidance with positive and edge examples. Double-annotate the locked test set; adjudicate disagreements without exposing model output to annotators. Report character-level agreement, field-label agreement, and box agreement before using the set as a release gate.

## 6. Splits and leakage controls

- Split by application family/product artwork, not by image. All captures, crops, transformations, and duplicates derived from one artwork stay in one split.
- Keep collision groups together so near-identical families cannot leak across training and evaluation.
- Use development data for experiment selection and threshold tuning. Keep a locked test set untouched until a release candidate is chosen.
- Keep a separate small regression set of previously discovered failures; do not report it as unbiased test performance.
- Record all dataset and split manifests by digest. Any corrected test label increments the dataset version and triggers a clearly labeled rerun.
- Candidate application records remain in the search index because retrieval requires them, but test images, transcriptions, and derived variants must not influence OCR tuning or match thresholds.
- Report results by source and difficulty slice, not only as an aggregate. At minimum: clean/controlled, captured bottle, degraded, partial, duplicate-heavy, collision-heavy, and no-match.

## 7. Optimization experiments

Use controlled, one-change-at-a-time experiments first, followed by a small factorial confirmation of interacting winners. Every run pins container image, Tesseract/language-data versions, configuration, CPU/memory limits, worker count, dataset digest, and random seeds.

### Baseline

Establish a no-tuning local baseline using Tesseract 5 TSV output, `--oem 1`, pinned English `tessdata_fast`, EXIF orientation only, one bounded OCR pass per unique image, and no application-specific text correction. Measure cold start separately; the service warms at startup and release latency uses warm runs.

### Preprocessing candidates

Evaluate with ablations rather than enabling all transforms:

- safe decode, EXIF rotation, color/grayscale choice, and scale cap;
- contrast normalization or CLAHE;
- global versus adaptive thresholding;
- deskew and coarse orientation detection;
- perspective correction for planar label regions;
- lightweight denoise/sharpen;
- curvature-aware crops only if bottle captures show material benefit;
- perceptual deduplication and information-rich image ordering.

Reject a transform when it improves average OCR but damages a critical slice, removes punctuation required by regulation, makes evidence coordinates unreliable, or consumes more downstream value than its latency cost.

### Recognition and scheduling candidates

- Compare `tessdata_fast` with `tessdata_best` and page-segmentation modes suited to full, block, and sparse label text (`--psm 3`, `6`, and `11`) on the development set. Keep `fast` unless `best` produces material downstream improvement inside the latency budget.
- Prefer one general pass. Add a second pass only for a detected information-rich region and only when its measured field/linking gain fits the deadline.
- Evaluate bounded worker counts on target hardware; stop increasing parallelism when tail latency, memory, or contention worsens.
- Budget work by remaining monotonic deadline. Return completed spans with explicit warnings at expiry.
- Use field parsers and dictionaries after OCR for candidate generation, never to silently rewrite evidence. Preserve the original span beside every normalized value.

Official technical references: [Tesseract command-line and TSV usage](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [Tesseract image-quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html), [Tesseract data files](https://tesseract-ocr.github.io/tessdoc/Data-Files.html), [OpenCV thresholding](https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html), [morphology](https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html), and [geometric transforms](https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html).

## 8. Metrics, gates, and reporting

### OCR and evidence metrics

- Character error rate (CER) and word error rate (WER), micro and per-image macro, using one declared normalization and edit-distance implementation. See the [OCR-D evaluation specification](https://ocr-d.de/en/spec/ocrd_eval.html).
- Exact and normalized field-value accuracy, plus recall for each identification-critical field.
- Government-warning exact/normalized accuracy reported separately.
- Text-region recall and evidence-box overlap at a declared IoU threshold.
- Success, partial, timeout, and hard-failure rates.

### Downstream metrics

- Top-1 and top-3 application retrieval accuracy.
- Automatic-link precision, recall/coverage, false-link count, and no-match accuracy.
- Identification changes caused by OCR versus ground-truth transcription.
- Per-check false **Pass**, false **Mismatch**, and **Needs review** rates attributable to OCR.
- Image-order invariance and duplicate-photo sensitivity.

### Performance metrics

- Decode, preprocessing, OCR, normalization, and total elapsed time at p50/p90/p95/p99.
- Cold-start latency separately from warmed latency.
- Peak resident memory, CPU utilization, decoded pixels, images attempted/completed, and worker count.
- Results at one request and at the prototype's declared concurrent-load level.

### Initial release gates

| Gate | Threshold |
| --- | --- |
| Warm OCR latency | p95 ≤ 2.9 s for the published representative envelope. |
| Integrated latency | p95 ≤ 5.0 s for the same envelope. |
| Automatic linking | ≥99.5% precision point estimate and a reported one-sided 95% confidence bound; any false link is investigated before release. |
| Candidate retrieval | ≥98% top-3 accuracy when the correct record exists and identifying evidence is legible. |
| Critical-field extraction | ≥95% normalized recall overall, with no critical slice below 90%. |
| Compliance safety | Zero known OCR-caused false **Pass** outcomes in the locked release corpus. |
| Stability | No material result change from photo ordering or exact duplicate photos. |

Thresholds are provisional product-risk decisions, not claims about all real-world images. Publish sample counts and exact or Wilson confidence intervals with every rate; do not hide failures inside averages. A result outside the supported image envelope must be labeled, not mixed into the release-gate claim.

Each benchmark report includes the git revision, UTC date, host CPU/RAM/OS, container limits, corpus/split digest, engine and data versions, full configuration, run count/warm-up, envelope, raw machine-readable results, metric tables by slice, error taxonomy, selected configuration, rejected alternatives, and remaining gaps.

## 9. Training or fine-tuning decision

Do **not** train initially. Tesseract's own [image-quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html) says retraining is unlikely to help unless fonts or language are unusual. First exhaust measured improvements from image capture guidance, preprocessing, segmentation, officially distributed language data, scheduling, parsing, and conservative uncertainty thresholds.

Train custom Tesseract data only when all are true:

1. The best non-trained pipeline misses an agreed release gate on the locked development data while meeting latency.
2. Errors are repeated recognition errors in learnable glyph/font/language patterns, not mainly blur, glare, occlusion, curvature, layout, bad ground truth, or match-scoring defects.
3. There is enough correctly segmented, rights-cleared line-level ground truth for separate training and validation families.
4. A small pilot demonstrates a statistically meaningful downstream gain without worsening critical slices, confidence calibration, evidence fidelity, or latency.
5. Model lineage, license, reproducible training command, and rollback artifact can be maintained.

Do not train to memorize brands, application IDs, or the evaluation registry. Do not train when conservative candidate selection or an additional photo solves the risk more safely. Never train from scratch for this prototype.

If the gate passes:

1. Fine-tune from `tessdata_best`, the official retrainable model family.
2. Use rights-cleared, family-separated line PNG/TIFF images with same-name `.gt.txt` transcriptions.
3. Use the official [`tesstrain`](https://github.com/tesseract-ocr/tesstrain) workflow and record data/model versions, seed, commands, checkpoints, and train/evaluation CER.
4. Select a checkpoint on development CER plus critical-field and downstream metrics—not training loss alone.
5. Compare candidate artifacts with the frozen non-trained baseline on the untouched test set, including latency and every critical slice; retain the baseline as rollback.

The official [Tesseract 5 training guide](https://tesseract-ocr.github.io/tessdoc/TrainingTesseract-5.html) governs any fine-tuning experiment.

## 10. Milestones and artifacts

### M0 — Contract and harness

Deliver provider models, deterministic stub, conformance tests, benchmark CLI, timing instrumentation, and report schema. **Exit:** the application can complete all workflows without real OCR.

### M1 — Corpus and local baseline

Deliver provenance/annotation guides, pilot corpus, frozen splits, Tesseract container, and baseline report. **Exit:** dominant error and latency slices are known.

### M2 — Optimize without training

Run preprocessing, segmentation, language-data, scheduling, and concurrency experiments. Deliver ablation report and recommended image envelope/configuration. **Exit:** a reproducible candidate meets latency or has a quantified gap.

### M3 — Downstream validation

Run collision-heavy retrieval and rule-impact tests with ground-truth versus OCR text. Tune uncertainty thresholds outside the OCR adapter. **Exit:** false-link and false-Pass risks are measured by slice.

### M4 — Training gate

Record a decision memo: no training, or a bounded training experiment meeting Section 9. **Exit:** the decision is evidence-based and reproducible.

### M5 — Integration and release

Replace the application stub through configuration, run contract/integration/end-to-end tests, lock the evaluation set, and publish the release benchmark. **Exit:** all gates pass or exceptions are explicitly accepted with user-visible limitations.

Required artifacts are versioned provider schemas, stub fixtures, corpus and split manifests, annotation guide, dataset card, preprocessing configuration, Tesseract/model manifest, conformance and regression tests, raw benchmark results, human-readable benchmark report, error catalog, training decision memo, and integration runbook.

## 11. Handoff and operational constraints

The OCR track hands the application track:

- an adapter package implementing the provider contract;
- a pinned local Tesseract runtime and readiness/warm-up check;
- recommended per-file and aggregate byte/pixel limits, representative envelope, worker count, and deadline allocation;
- stable failure codes and user-action guidance;
- fixture outcomes for application tests;
- version and timing fields for `/capabilities` and verification responses.

The application supplies already validated images, the request deadline, cancellation, and bounded temporary storage. It retains normalized spans only for the short verification TTL and never logs label text or image content. OCR processes use fixed executable/model paths, argument arrays, CPU/memory limits, and request-scoped cleanup.

Enabling a future OCR strategy requires only a new adapter, registration/configuration, conformance tests, and comparative benchmark. It must not change application domain models, candidate-search contracts, compliance rules, or the public intake API.

## 12. Primary risks and responses

| Risk | Response |
| --- | --- |
| Public artwork does not resemble enforcement photos | Add controlled bottle captures and report source slices separately. |
| Synthetic data inflates accuracy | Keep synthetic derivatives grouped and maintain an untouched captured-photo test slice. |
| Near-match brands turn one OCR character into a false link | Build collision groups, measure downstream precision, and require score separation/agent confirmation. |
| Preprocessing destroys punctuation or small warning text | Preserve originals, run ablations, and gate critical fields separately. |
| More photos exhaust the deadline | Deduplicate, prioritize informative views, bound parallelism, and return explicit partial results. |
| Custom training overfits registry labels | Split by family/collision group, prohibit test-derived training, and retain a frozen baseline. |
| Hardware-dependent results | Pin resources and publish target hardware, limits, cold/warm results, and raw timings. |
| Provider confidence is misleading | Calibrate decisions on held-out data and use confidence only with evidence and downstream score margins. |
