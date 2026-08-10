# Label Lens

This repository is my submission for the Treasury take-home assessment. Label Lens is a photo-first distilled-spirits label review prototype that uses local OCR and public TTB COLA metadata to identify likely applications, explain label checks, and record simulated decisions without changing a government system.

## Getting started

### Prerequisites

- Docker with Compose, provided by [OrbStack](https://orbstack.dev/) or Docker Desktop
- `make`, included with macOS and most Linux development environments

From the repository root, start the complete application:

```sh
make dev
```

Open **http://localhost:8080**. Choose **Try a sample** if you do not have label photos available.

Stop the application with:

```sh
make stop
```

## The submission

### What I built

The normal workflow requires only one or more unordered label photos:

```text
Photos → OCR and fact extraction → COLA candidate search → label checks → local decision
```

Label Lens combines evidence across the photos, searches a read-only snapshot of public COLA metadata, and either links a credible record or asks the reviewer to choose from a short candidate list. After the match is confirmed, it presents field-level findings and lets the reviewer record a mock approval or denial; the public Registry and COLAs Online are never modified.

The prototype implements one complete **distilled spirits** vertical slice. Wine, malt beverages, large batches, durable audit records, and official government actions remain explicit follow-on work.

### Engineering choices

| Concern | Choice | Rationale |
| --- | --- | --- |
| User interface | React, TypeScript, and Vite | A small accessible single-page workflow with fast builds, explicit state, and progressive disclosure for evidence. |
| Application API | FastAPI and Python 3.12 | Typed request boundaries and a natural fit for image-processing and OCR libraries. |
| OCR | Local Tesseract behind an `OcrProvider` contract | The default works offline and sends no label data to a third party. Ordered alternative providers can be added without changing verification logic. |
| COLA metadata | Deterministically generated, read-only SQLite index | Runtime search is fast and independent of the legacy public Registry. The reviewed source lock currently contains 42 real distilled-spirits records. |
| COLAs Online boundary | Private HTTP sidecar with local decision state | It exercises search, detail, status, and approve/deny paths while making it structurally clear that no government system is connected. |
| Deployment | Firebase Hosting in front of a multi-container Cloud Run service | Static assets stay at the edge while OCR and the metadata sidecar deploy together. Scale-to-zero and a one-instance ceiling control prototype cost. |

### Product and domain design

- **Minimal intake:** JPEG or PNG photos are the only required user input. The system infers identifying facts and photo roles.
- **Conservative identification:** automatic linking requires sufficient confidence and separation from the next candidate. Ambiguity is shown rather than guessed.
- **Explainable verification:** each check reports expected and observed values, supporting OCR evidence, applicability, and `Pass`, `Mismatch`, or `Needs review` status.
- **Human decision:** the reviewer owns the final disposition and may explain an override. Approval and denial receipts are explicitly local and simulated.
- **Extensibility:** verification sessions, OCR spans, identification clues, COLA applications, candidates, checks, decisions, and receipts are separate domain concepts. New beverage rules and OCR strategies do not require rebuilding the intake flow.

### Data and computation

Uploaded bytes and OCR text are processed transiently and are not retained. Public COLA metadata is refreshed only by an explicit maintainer command, reviewed into `fixtures/public-cola/records.lock.json`, and compiled into an immutable SQLite artifact during the sidecar image build; label images are not part of that database.

The API validates file type, encoded size, decoded pixels, aggregate work, and concurrency before OCR. A five-second application deadline prioritizes response time; uncertain or incomplete evidence becomes a review state instead of a false pass. Matching thresholds and OCR accuracy remain benchmark-driven prototype decisions rather than claims of complete legal review.

The primary action paths are:

- `POST /api/v1/enforcement-items/verifications` — process arbitrary unordered photos and search for COLA candidates.
- `POST /api/v1/verifications/{id}/application-match` — confirm an ambiguous candidate without repeating OCR.
- `POST /api/v1/verifications/{id}/decisions` — record a simulated local approval or denial.
- `GET /health/ready` and `GET /api/v1/capabilities` — expose readiness, limits, OCR strategy, and ruleset information.

The full requirements and engineering narrative live in [docs/requirements.md](docs/requirements.md) and [docs/implementation-plan.md](docs/implementation-plan.md).

## Development

### Services and ports

Docker Compose launches three containers. Only the web entry point is exposed to the host.

| Container | Responsibility | Port |
| --- | --- | --- |
| `web` | Compiled React UI, security headers, and reverse proxy | `localhost:8080` → container `8080` |
| `api` | Upload validation, OCR orchestration, matching, verification rules, and transient sessions | Container-only `8080` |
| `cola-mock` | Read-only public COLA index plus isolated in-memory decision state | Container-only `8081` |

The browser sends `/api/**` and `/health/**` through `web`; neither Python service is directly exposed. Use `make logs` to follow all three containers.

### Repository layout

| Path | Contents |
| --- | --- |
| `apps/web` | React/Vite application and component tests |
| `apps/api` | FastAPI application, domain policies, rules, adapters, and API tests |
| `apps/cola-mock` | Replaceable COLA integration boundary and metadata search |
| `packages/ocr` | Provider-neutral OCR contract, Tesseract adapter, fixtures, and metrics |
| `tools/data` | Deterministic public-metadata synchronization and SQLite build tools |
| `tools/ocr` | Corpus generation and benchmark utilities |
| `fixtures` | Bundled demo photos, provenance manifests, and reviewed metadata lock |
| `infra` | Cloud Run service template |
| `docs` | Requirements, implementation narrative, benchmark status, and deployment runbook |

### Native development and tests

Native development uses Python 3.12 and Node 22. `make setup` creates `.venv`, installs the Python workspaces, and uses Corepack to install the pinned pnpm dependencies.

```sh
make setup
make test
```

Useful focused commands:

```sh
make test-python
make test-web
make build-web
```

### UI-only mode

For interface work that does not need real OCR, run:

```sh
make dev-fixture
```

This selects deterministic fixture OCR and intentionally ignores the contents of uploaded images. It is useful for exercising UI states, but it must not be used to evaluate recognition or matching quality.

### Exercise the OCR API directly

Start the normal stack with `make dev`, then submit the included public front and back labels as one enforcement item:

```sh
curl --silent --show-error \
  --form images=@fixtures/demo/seven-fathoms-front.jpg \
  --form images=@fixtures/demo/seven-fathoms-back.jpg \
  http://localhost:8080/api/v1/enforcement-items/verifications \
  | python3 -m json.tool
```

This executes the same upload validation, local Tesseract OCR, fact extraction, public-metadata search, and verification path used by the UI.

The application bundles five proven sample sets. To reconstruct the full seven-set public evaluation corpus or rebuild the metadata database:

```sh
make samples
make cola-index
```

`make samples` downloads provenance-pinned label images for local evaluation. `make cola-index` builds the metadata-only database from the reviewed lock without contacting TTB. See [docs/public-cola-index.md](docs/public-cola-index.md) and [docs/benchmark-status.md](docs/benchmark-status.md).

## Deployment

The application is deployed at **https://label-lens-nmh-2026.web.app**. Firebase Hosting serves the compiled web application and applies same-origin `/api/**` and `/health/**` rewrites to a public Cloud Run service; Cloud Run runs the API and COLA metadata sidecar in one multi-container revision with minimum instances `0`, maximum instances `1`, and request concurrency `1`.

### Prerequisites

- A billing-enabled Google Cloud project you are permitted to administer
- Firebase added to that project
- Docker with Buildx
- `gcloud` and `firebase` CLIs

Authenticate and select a globally unique project ID:

```sh
gcloud auth login
firebase login

export PROJECT_ID="your-project-id"
export REGION="us-east1"
export RELEASE="$(git rev-parse --short HEAD)"

gcloud config set project "$PROJECT_ID"
firebase projects:addfirebase "$PROJECT_ID"
firebase use "$PROJECT_ID" --alias default
```

Enable the required services and create the private image repository and runtime identity:

```sh
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com

gcloud artifacts repositories create label-verifier \
  --repository-format=docker \
  --location="$REGION"

gcloud iam service-accounts create label-verifier-runtime \
  --display-name="Label Verifier runtime"

gcloud auth configure-docker "$REGION-docker.pkg.dev"
```

Build and push the two server images. The explicit platform produces Cloud Run-compatible images when building from an Apple Silicon machine.

```sh
export API_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/label-verifier/api:$RELEASE"
export COLA_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/label-verifier/cola-mock:$RELEASE"

docker buildx build --platform linux/amd64 \
  --file docker/api.Dockerfile --tag "$API_IMAGE" --push .

docker buildx build --platform linux/amd64 \
  --file docker/cola-mock.Dockerfile --tag "$COLA_IMAGE" --push .

export API_DIGEST="$(gcloud artifacts docker images describe "$API_IMAGE" --format='value(image_summary.digest)')"
export COLA_DIGEST="$(gcloud artifacts docker images describe "$COLA_IMAGE" --format='value(image_summary.digest)')"
```

Render and deploy the checked-in multi-container service template using immutable image digests:

```sh
mkdir -p build
sed \
  -e "s/PROJECT_ID/$PROJECT_ID/g" \
  -e "s/API_IMAGE_DIGEST/$API_DIGEST/g" \
  -e "s/COLA_MOCK_IMAGE_DIGEST/$COLA_DIGEST/g" \
  infra/cloudrun/service.template.yaml > build/cloudrun-service.yaml

gcloud run services replace build/cloudrun-service.yaml \
  --region="$REGION" \
  --project="$PROJECT_ID"

gcloud run services add-iam-policy-binding label-verifier \
  --region="$REGION" \
  --member=allUsers \
  --role=roles/run.invoker
```

Finally, build and publish the web application. `firebase.json` pins the Hosting rewrite to the deployed Cloud Run revision.

```sh
corepack pnpm install --frozen-lockfile
corepack pnpm web:build
firebase deploy --only hosting --project "$PROJECT_ID"
```

Open the Hosting URL printed by Firebase and run a bundled sample through identification and a mock decision. This is an anonymous synthetic/non-sensitive prototype: uploads are transient, decisions are in memory and may reset, and no government record is updated.

Firebase budget alerts are notifications, not hard spending caps. Before leaving a deployment active, configure billing alerts and confirm that the Cloud Run service still reports `minScale: 0` and `maxScale: 1`. The full release, smoke-test, rollback, and decommission procedure is in [docs/deployment-runbook.md](docs/deployment-runbook.md).
