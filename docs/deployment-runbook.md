# Firebase and Cloud Run Deployment Runbook

**Status:** Deployed and smoke-tested on 2026-08-09  
**Region:** `us-east1`  
**Cost posture:** Request-based billing, scale to zero, maximum one instance, approximately $10/month ceiling

## Current release

- **Firebase project:** `label-lens-nmh-2026`
- **Public URL:** https://label-lens-nmh-2026.web.app
- **Cloud Run service:** `label-verifier`
- **Cloud Run revision:** `label-verifier-00001-hv2`
- **Application image:** `sha256:62a13569fe61923cc55097f3e40530f2cb90d366fa81a323bd1afbfe4d70db01`
- **COLA sidecar image:** `sha256:75dec81e687a5c031c7c31d26186f4cea7e0791c8043347a5a134e893c7b9455`
- **Budget notifications:** 50%, 80%, and 100% of $10 monthly project spend

The release gate completed with 51 passing Python tests, 11 passing web tests, and a successful production build. Public smoke testing confirmed security headers, readiness, real two-image Tesseract OCR, automatic Seven Fathoms identification, cross-reference results, a mock Needs Correction receipt, and a clean browser console. The measured warm verification completed in 3.1 seconds.

## 1. Authorization checkpoint

Do not execute cloud or GitHub creation commands until the owner explicitly approves the project/repository names, public visibility, billing account, and exact release. Local builds and emulator/dry-run checks are allowed.

The anonymous demo accepts synthetic/non-sensitive test images only. It stores no uploads or OCR text after the request. Public COLA metadata is a locked, read-only build artifact; local decisions may reset whenever Cloud Run restarts.

## 2. Target topology

- Firebase Hosting: immutable React/Vite assets and `/api/**` rewrite with `pinTag`.
- Cloud Run: FastAPI/Tesseract ingress plus the public-metadata/local-decision sidecar.
- Artifact Registry: immutable API and mock images.
- Cloud Logging/Monitoring: content-safe logs, latency/resource dashboards, and alerts.
- GitHub Actions: tests and image builds; cloud deploy remains manually approved.

Initial Cloud Run controls are minimum instances `0`, maximum instances `1`, concurrency `1`, request-based billing, and startup CPU boost. The template assigns 2 vCPU/2 GiB to OCR/API and 1 vCPU/256 MiB to the mock sidecar. Cloud Run requires at least 1 vCPU per container for this second-generation multi-container shape; scale-to-zero and the one-instance ceiling are therefore essential cost controls. The UI warms `/health/ready` on load. Resources remain provisional until the target benchmark.

## 3. Required owner inputs

- GCP billing account and approved Firebase/GCP project ID.
- GitHub organization/user, repository name, and public/private visibility.
- Whether a custom domain is needed; Firebase's generated domain is sufficient for the prototype.
- Confirmation that an anonymous synthetic-only demo is acceptable.
- Explicit authorization for recurring spend and public deployment.

## 4. Provisioning outline

1. Create the GCP project in `us-east1`, attach billing, and enable Firebase.
2. Set a monthly budget alert at 50%, 80%, and 100% of $10. A budget alert is not a hard cap; maximum instances and monitoring are the primary safeguards.
3. Enable Cloud Run, Artifact Registry, Cloud Build, Firebase Hosting, Cloud Logging, and Cloud Monitoring APIs.
4. Create the `label-verifier` Artifact Registry repository.
5. Create a least-privilege `label-verifier-runtime` service account. Do not grant editor/owner.
6. Build the locked COLA metadata index, then build and scan immutable service images; record their digests and dataset digest.
7. Replace placeholders in `infra/cloudrun/service.template.yaml` and deploy a named revision.
8. Permit public invocation only because application input is synthetic-only; keep every non-ingress container private.
9. Build the web app, create a Firebase preview channel, and pin its rewrite to the candidate revision.
10. Run smoke, cleanup, latency, and accessibility checks before production promotion.

## 5. Pre-deploy gates

- All unit, integration, web, OCR conformance, security, and container tests pass.
- Images run as non-root and contain no secrets or high-severity known vulnerabilities.
- `/health/live` and `/health/ready` pass with `cola-mock` and warmed Tesseract.
- Synthetic upload success, ambiguity, mismatch, approve, deny, timeout, and cleanup paths pass.
- Cold landing-to-ready and warm post-upload latency are measured on the selected Cloud Run profile.
- The release manifest records git SHA, image digests, ruleset/OCR versions, configuration, and results.

## 6. Deployment and smoke

Deploy the exact tested image digests. Do not rebuild during promotion. Wait for Cloud Run readiness, then publish the pinned Firebase Hosting release.

Smoke with repository-owned synthetic images only:

1. Load the Firebase URL and observe verifier readiness.
2. Submit a unique clean item and confirm automatic mock COLA identification.
3. Submit an ambiguous item and choose a candidate without rerunning OCR.
4. Exercise Needs review, Approve, and Needs Correction flows.
5. Confirm receipt mock markers and per-browser demo state.
6. Verify no upload remains after success, error, timeout, or container restart.
7. Confirm headers, body limits, rate/capacity behavior, and content-safe logs.

## 7. Monitoring and cost

Monitor request count, 429/5xx, cold starts, readiness, OCR/full-request p95, CPU, memory, instance count, restarts, and billable instance time. Alert on sustained errors, latency over budget, memory pressure, or estimated spend above thresholds.

The cost ceiling may conflict with a permanently warm OCR instance. First use scale-to-zero plus page-load warm-up. If the five-second post-upload experience still fails, stop and present the measured minimum-instance price before changing the configuration.

## 8. Rollback and decommission

Rollback restores the previous Cloud Run image digests and pinned Firebase Hosting release, waits for readiness, and reruns synthetic smoke. Mock state resets are expected.

To decommission, disable Hosting, delete the Cloud Run service and images after retaining the release manifest/benchmark, remove IAM bindings/service accounts, and verify billing shows no active resources. Do not delete an owner project or repository without separate explicit approval.
