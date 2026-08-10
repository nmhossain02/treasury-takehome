# Alcohol Label Verification — Requirements

**Status:** Requirements baseline  
**Last updated:** 2026-08-09

## 1. Goal

Help a TTB compliance agent evaluate a distilled-spirits enforcement item from its photos. The system identifies the most likely public COLA record, determines which cross-references apply, compares the observed label with public metadata and objective federal rules, and then lets the agent record a local disposition.

The product is decision support. It must show its evidence and uncertainty; the agent makes the final decision.

Prototype success means a first-time user can submit photos without classifying them or entering application data, understand the result, and receive it within five seconds after upload under documented representative conditions.

## 2. How we narrowed the problem

The [project brief](https://github.com/treasurytakehome-rgb/instructions) emphasizes repetitive matching, human judgment, a roughly five-second response, an obvious workflow, and eventual batches of 200–300 applications. It excludes direct COLAs Online integration from the prototype.

Federal requirements differ across distilled spirits, wine, and malt beverages. The prototype therefore implements one complete **distilled spirits** vertical slice. It checks only facts supported by the photos, matched application, and curated rules; it does not claim full legal compliance.

Source precedence is:

1. Current eCFR text.
2. Current TTB guidance and forms.
3. Stakeholder notes and the project brief.

Every implemented rule retains its citation and retrieval or effective date.

## 3. Users and outcome

**Primary user:** TTB label compliance agent.  
**Supporting user:** Compliance owner who approves rule changes and evaluation cases.

The agent needs to answer:

1. Which COLA application most likely belongs to this item?
2. What matches, what does not, and what remains uncertain?
3. Which checks applied, and why?

## 4. Key user stories

### Must — prototype

#### US-01 — Submit an enforcement item from photos

As an agent, I want to submit the photos I have without completing a form so that intake is fast and does not depend on my knowing the application record.

Acceptance criteria:

- The only required input is one or more JPEG or PNG photos.
- The user may add or remove any number of photos; the user does not identify panel type, category, expected fields, or application ID.
- Image order does not affect the result. Duplicate or overlapping views do not create duplicate evidence.
- The product validates individual files and aggregate resource use, explains any rejected input, and preserves accepted photos.
- No fixed semantic panel count is required. Configurable aggregate byte, pixel, concurrency, and processing limits protect the five-second target and service availability.

#### US-02 — Identify the corresponding COLA application

As an agent, I want the system to find the database entry represented by the photos so that I do not search or transcribe it manually.

Acceptance criteria:

- OCR and fact extraction combine evidence across all photos, including brand and fanciful names, class/type, ABV, net contents, responsible party, address, origin, and visible identifiers.
- The system searches a versioned, read-only index derived from public TTB COLA metadata and returns the strongest candidates with score, distinguishing fields, and photo evidence.
- It links a record automatically only when both a confidence threshold and a separation from the next candidate are met.
- A low-confidence, ambiguous, or absent match is never guessed; it returns **Needs identification**.
- Identification is invariant to photo order and conservative when photos disagree.

#### US-03 — Resolve an uncertain identification

As an agent, I want a short list of plausible applications when identification is uncertain so that I can resolve the case without re-entering its data.

Acceptance criteria:

- Show at most three ranked candidates and the fields that support or distinguish them.
- The agent may select a candidate or add clearer photos.
- Candidate selection reuses retained OCR results and reruns cross-references without requiring another upload.
- If no candidate is credible, the product says what identifying evidence is missing and does not enable a disposition.

#### US-04 — Select and run applicable cross-references

As an agent, I want the system to determine which comparisons and rules apply so that I do not configure the review.

Acceptance criteria:

- The matched application supplies the expected values, beverage category, domestic/import status, application type, and trusted label metadata.
- A versioned applicability plan selects checks from those facts and the available photo evidence.
- Each check records why it was applied, skipped, or could not be determined.
- A missing inapplicable field is not reported as a mismatch.

#### US-05 — Compare label and application facts

As an agent, I want each supported field compared separately so that I can find discrepancies without rereading the label.

Acceptance criteria:

- Each check returns **Pass**, **Mismatch**, or **Needs review**.
- Each result shows expected value, observed value, photo evidence, and a short reason.
- Case, spacing, and insignificant punctuation differences do not cause a mismatch.
- Numeric and unit equivalents are compared semantically; for example, `750 mL` equals `0.75 L`.
- Unreadable, contradictory, or ambiguous evidence returns **Needs review**, never a guessed **Pass**.

#### US-06 — Check objective distilled-spirits rules

As an agent, I want objective mandatory-label checks applied automatically so that I can focus on nuanced issues.

| Check | Prototype behavior |
| --- | --- |
| Brand name | Present and equivalent to the matched application. |
| Class/type | Present and equivalent to the matched application. The system does not infer whether the formula qualifies for that class/type. |
| Alcohol content | Present and numerically equal to the application. Proof, when shown, is consistent with twice the ABV. |
| Same field of vision | Brand name, class/type, and alcohol content appear together in one observed label view or a reliably reconstructed panel. |
| Net contents | Present and equivalent to the application. |
| Name and address | Present and equivalent to the application. |
| Country of origin | Present when the matched application is imported. |
| Government warning text | Complete statement matches [27 CFR 16.21](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16/subpart-C/section-16.21); line wrapping and insignificant whitespace may differ. |
| Government warning format | `GOVERNMENT WARNING` is uppercase and bold, the remainder is not bold, and separation/contrast are evaluated when determinable. |

Physical size, characters per inch, contrast, or placement returns **Needs review** when the photos and trusted record metadata cannot support a reliable measurement.

#### US-07 — Review evidence and improve the case

As an agent, I want to inspect the evidence and add or replace photos so that I can resolve uncertainty without starting over.

Acceptance criteria:

- Selecting an identification signal or check highlights the supporting region and provides equivalent text.
- The system infers photo roles such as front, back, neck, or unknown; the user is not required to label them.
- Adding, removing, or replacing photos reruns identification and verification.
- A failed extraction does not erase accepted photos or other completed results.

#### US-08 — Recover from poor input

As an agent, I want clear recovery guidance when photos cannot be evaluated so that I know whether to retry or review manually.

Acceptance criteria:

- Distinguish unsupported media, resource-limit rejection, processing failure, low-confidence OCR, ambiguous match, and missing evidence.
- Give a specific next action, such as photographing the brand or government-warning panel more clearly.
- Never convert a processing or identification failure into a compliance mismatch.

#### US-09 — Record a local disposition

As an agent, I want to approve or deny the reviewed application so that I can complete the prototype workflow.

Acceptance criteria:

- **Approve** and **Deny** are available only after an application match is confirmed and verification completes; both are visibly local actions.
- Approve moves the local review state to **Approved**.
- Deny requires a reason and defaults to **Needs Correction**; eligible final denial moves local review state to **Rejected**.
- The agent may override automated results with an explanation.
- The UI confirms status, timestamp, and receipt ID and prevents accidental duplicate submission.
- A stale status or integration failure leaves the application undecided and offers retry.
- No decision request reaches TTB or COLAs Online, and the public Registry status never changes.

### Should — next increments

#### US-10 — Cover other beverage categories

Add separate wine and malt-beverage identification features and rule sets. They must not inherit distilled-spirits rules by default.

#### US-11 — Verify a batch

Accept up to 300 independent enforcement items, preserving each item's identification, status, and evidence. Batch performance and limits require separate validation.

#### US-12 — Export a review record

Export photos' references, application match and confidence, check results, evidence, rule versions, and timings. Retention and official-record status remain undefined.

## 5. Quality requirements

- **Latency:** Return identification and verification within five seconds after upload for the documented representative image envelope. This is not a promise of constant time for unbounded bytes or pixels.
- **Optimization order:** Meet latency first, then maximize accuracy without regressing it. Avoiding false **Pass** and incorrect automatic record links takes priority over reducing review work.
- **Minimal input:** Photos are the sole required user input on the normal path.
- **Clarity:** A first-time user can complete a case without training or hidden controls.
- **Conservative outcomes:** Uncertain identification or evidence is surfaced explicitly; it is never silently resolved.
- **Traceability:** Every match signal and rule result identifies its evidence, algorithm/ruleset version, and source where applicable.
- **Resilience:** A failed image or independent check does not erase other useful results.
- **Data minimization:** Uploaded photos and OCR text are transient. Runtime state contains only local decision metadata and short-lived verification references; the deployed COLA index contains metadata, not label images.
- **Connectivity:** The core workflow requires no live COLAs Online or regulatory website access.
- **Operational security:** Validate untrusted files, constrain aggregate work, avoid content logging, patch dependencies, and ship without embedded secrets or known high-severity vulnerabilities.
- **Accessibility:** Target WCAG 2.2 AA; all photo evidence and status information must have nonvisual equivalents.

Matching and OCR thresholds remain provisional until measured on a labeled evaluation corpus.

## 6. Assumptions

1. The prototype serves compliance agents, not producers or the public.
2. The first release covers distilled spirits intended for U.S. sale.
3. Input may contain any number and order of bottle or label photos, including partial, overlapping, and duplicate views. The user does not classify them.
4. At least one photo contains enough identifying text to retrieve a plausible application. Otherwise the correct outcome is **Needs identification**.
5. The versioned public-metadata index contains the relevant application and enough normalized structured facts to retrieve and compare it. Deliberate near-match records remain necessary for evaluation.
6. Expected values come from the confirmed public COLA metadata record; manual transcription is not part of the normal flow.
7. JPEG and PNG, at most 1.5 MB per image, form the initial profile based on current COLAs Online guidance. No semantic image-count cap is imposed, but configurable aggregate encoded bytes, decoded pixels, and work limits apply.
8. Basic orientation, deskewing, contrast, and duplicate detection are supported. Severe reflection, occlusion, curvature, or blur may require another photo.
9. Comparisons ignore case, insignificant punctuation, and repeated whitespace except where exact wording or formatting is legally significant.
10. Physical measurements require trusted scale from application metadata or a reliable reference; photos alone normally cannot establish them.
11. Rules are curated into a versioned local catalog; runtime internet access is not assumed.
12. The five-second target starts after upload completes, is measured on warmed target-like hardware, and applies to a documented image-count/size/quality envelope rather than unlimited computational work.
13. Results and dispositions are advisory and local; public Registry data is read-only and no government record is changed.
14. Public or synthetic data is sufficient for the prototype. Application-level accounts, long-term retention, PII controls, and federal records management are deferred. A persistent internet deployment uses edge access control unless anonymous access is explicitly accepted with synthetic-only data and stronger abuse limits.

## 7. Data sources

| Source | Needed for | Prototype access |
| --- | --- | --- |
| Enforcement-item photos | Identification clues, observed label facts, layout, and evidence | Sole runtime user input; transient processing. |
| [TTB Public COLA Registry](https://www.ttb.gov/online-services/public-cola-registry) | Candidate retrieval and expected application facts | Explicit maintainer synchronization to a reviewed lock; deterministic offline build to a read-only SQLite index. No runtime Registry access and no label images in the index. |
| [27 CFR Part 5](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-5) | Distilled-spirits labeling rules | Versioned local rule catalog; no runtime fetch. |
| [27 CFR 16.21](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16/subpart-C/section-16.21) and [16.22](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16/subpart-C/section-16.22) | Warning wording, format, legibility, and size | Same local catalog. |
| [TTB distilled-spirits guidance](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-brand-label) and [checklist](https://www.ttb.gov/system/files/images/labeling-ds/ds-labeling-checklist.pdf) | Interpret regulations and derive tests | Design/test reference; eCFR controls conflicts. |
| [TTB Form 5100.31](https://www.ttb.gov/media/70320/download?inline=) | Align field names and cross-references with COLA terminology | Design reference only. |
| [COLAs Online image guidance](https://www.ttb.gov/faqs/colas-and-formulas-online-faqs) | Initial media profile | JPEG/PNG, 1.5 MB per image, 120–170 dpi recommended; configurable limits. |
| Synthetic, public, and hand-labeled fixtures | Matching collisions, known discrepancies, degraded photos, and regression tests | Versioned corpus with provenance and expected outcomes. |
| [TTB wine guidance](https://www.ttb.gov/regulated-commodities/beverage-alcohol/wine/labeling) and [malt-beverage guidance](https://www.ttb.gov/regulated-commodities/beverage-alcohol/beer/labeling/malt-beverage-mandatory-label-information) | Later category-specific extraction and rules | Research only for the first release. |

Regulatory sources must be rechecked before implementation and the catalog stamped with the retrieval date.

## 8. Out of scope for the prototype

- Issuing, predicting, or representing an official government decision.
- Direct COLAs Online integration or modification of government records.
- Full legal compliance evaluation, including formulas, standards of identity, claims, age statements, ingredients, and state law.
- Wine, malt-beverage, batch, durable audit, user-administration, and production-accreditation features.
- Guaranteed matching when the record is absent or distinguishing text is not visible.
- Reliable physical measurement without scale metadata.
- Guaranteed recovery of severely blurred, reflective, curved, occluded, or incomplete labels.
- A five-second guarantee for unbounded image bytes, pixels, or concurrent load.

## 9. Decisions recorded

1. Distilled spirits is the first supported category; other beverages follow.
2. The normal path requires photos only. The system infers photo roles, finds the COLA record, and plans cross-references.
3. Users may supply any number of photos; service protection is expressed through aggregate resource and deadline limits, not a required panel count.
4. Automatic record linking requires conservative confidence and candidate-separation thresholds. Ambiguity goes to the agent.
5. Five-second processing is the first engineering gate; false **Pass** and incorrect record links are the highest-risk errors.
6. The prototype defaults to fully local OCR so it works without network access. OCR remains behind a provider-neutral contract with ordered, configurable strategies; a self-hosted HTTP adapter can be enabled later without changing identification or rule logic.
7. A private sidecar searches an immutable, generated public COLA metadata index. Approval/denial remains isolated local state behind the same replaceable integration boundary.
8. Baseline secure engineering is required; production accreditation is not.
9. The deployment target is Firebase Hosting plus a multi-container Cloud Run service in `us-east1`, using scale-to-zero, a one-instance ceiling, and anonymous synthetic-only access. The approximate monthly cost ceiling is $10; public creation/deployment still requires explicit authorization.

Remaining discovery: establish the candidate-search scoring thresholds, representative aggregate image envelope, collision-heavy evaluation corpus, acceptable false-link/false-pass rates, and measured accuracy/latency baselines.
