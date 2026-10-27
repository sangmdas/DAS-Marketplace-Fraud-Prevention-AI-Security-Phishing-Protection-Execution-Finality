# DAS Marketplace Fraud Prevention — Executable VLOP Reference Architecture

**Stop fraud before it executes: VI–CJT / CVID / Protected Authorization / Finality Sink / Advertising Accountability / Revocation**

> **Research-only, non-production reference implementation.** This repository uses **synthetic hotels, guests, bookings, payment beneficiaries and URLs**. It performs **zero real payments, sends zero real messages, verifies zero real properties and does not connect to any live marketplace**. It is not an implementation, audit or assessment of Booking.com, Airbnb, or any other platform. Do not expose the demo HTTP services on the public internet.

**Source proposal:** *Stop Fraud Before It Executes: A Deployable 25-Step Safety Architecture for EU Online Marketplaces*, https://zenodo.org/records/23689735. The accompanying original text is mapped step-by-step in [`docs/WORKFLOW_MAPPING.md`](docs/WORKFLOW_MAPPING.md). This repository is a **new, separate experiment**, not a rebranding of the previous 400-test/759-check DAS projects. The Zenodo publication and this repository may be updated on different schedules.

## One-screen technical summary

The platform may have valid login credentials, an approved listing draft, or an authorized payment intent, yet the **actual** consequential operation could be invalid by the time it reaches publication, messaging, payment or advertising. The prototype represents this gap by constructing candidate operations, recording scoped authorization in a protected-*simulated* database, and performing a second check against the **actual pending request** at a mock effectuation boundary. Malicious substitutions or revoked authority are denied. A separate Go gateway models edge admission and a JavaScript gate models paid-ranking disclosure, including a strict final-presentation contract.

**Core principle:** *Authentication is not authority to perform every consequential action; an upstream approval is not necessarily approval of the final operation.*

## Repository layout

```text
src/marketguard/core.py       Python VI-CJT/booking/authorization/finality mock engine
src/marketguard/api.py        Local FastAPI demo service
examples/demo.py              Scenarios A/B/C end-to-end, with mock outcomes
tests/test_workflows.py       152 pytest cases, including concurrency and HTTP

go/gateway/gateway.go         Go fixture-based gateway admission evaluator
go/gateway/gateway_test.go    20 matrix subcases + 4 standalone cases
go/gateway/main.go            Optional local Go HTTP service
web/advertising.mjs          JavaScript paid-placement metadata + display gate
web/advertising.test.mjs     24 Node built-in tests
web/demo.mjs                 Runnable browser-markup demonstration

scripts/benchmark.py         Local SQLite in-process timing, not production latency
scripts/run_all.sh           Run Python, Go, JS tests and generate reports
reports/                     Actual local test and benchmark artifacts
docs/WORKFLOW_MAPPING.md     Step-by-step mapping of all 25 proposed steps
docs/SECURITY_LIMITATIONS.md Trust assumptions, important missing guarantees
docs/DEPLOYMENT_AND_PERFORMANCE.md  VLOP integration and feasibility
LICENSE                      Custom source-available non-commercial terms
.github/workflows/ci.yml     Reproducible GitHub Actions jobs
```

## System requirements

- Python **3.11+** (3.11 or 3.12 recommended); `pytest`, `pytest-cov`, FastAPI and `httpx` for full tests.
- Go **1.23+**; no third-party Go dependencies.
- Node.js **20+**; no third-party JavaScript dependencies.
- Internet access is needed for *first-time installation* of Python test packages, not for runtime operation with dependencies already installed.

## Fast start: demo and all tests

From the **repository root**, in a POSIX terminal:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,api]'
python examples/demo.py
python -m pytest -q
(cd go/gateway && go test -v ./...)
(cd web && npm test)
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` and run the individual commands.

Or run `bash scripts/run_all.sh` after installing Python dependencies. The script outputs fresh reports in `reports/` and stops if a test command fails.

**Expected case counts in this version:** **152 Python**, **24 Go**, **24 JavaScript** = **200 distinct recorded checks**. The Go count excludes the aggregate `TestAdmissionMatrix` parent and includes its 20 named subtests plus four standalone tests. Python parameterized variants are independently collected pytest tests. Case IDs and descriptions are in [`docs/TEST_CATALOG.csv`](docs/TEST_CATALOG.csv). Test reports record executed results, not a proposed test list.

## Run the local interactive API

```bash
uvicorn marketguard.api:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000/docs` (automatically generated OpenAPI documentation). The `/demo/seed` endpoint populates one fictional operator, property, reservation, customer and verified merchant. `/v1/authorize` creates a scoped grant and `/v1/effect` attempts a mock consequential effect. `/v1/audit` returns the chain-integrity flag and counts. Stop the server with Ctrl+C.

Example CLI exchange after `POST /demo/seed`:

```bash
curl -s -X POST http://127.0.0.1:8000/v1/authorize \
  -H 'Content-Type: application/json' \
  -d '{"actor":"HOTEL-1","property":"PROP-1","kind":"message", "body":{"booking":"BOOK-1","recipient":"GUEST-1","text":"Welcome","requests_payment":false}}'
# Copy the returned grant identifier into the next command:
curl -s -X POST http://127.0.0.1:8000/v1/effect \
  -H 'Content-Type: application/json' \
  -d '{"grant":"REPLACE_WITH_GRANT_ID","sink":"messaging_sink","actual_body":{"booking":"BOOK-1","recipient":"GUEST-1","text":"Welcome","requests_payment":false}}'
```

**Local API security warning:** `/demo/seed`, `/v1/authorize`, `/v1/effect` are *intentionally not production-authenticated*. The trusted sink identity is supplied by the test harness. Anyone able to call these endpoints can attempt actions in the mock simulator; this is **not** an externally secure implementation of a non-bearer capability. Real systems require mutually authenticated services, protected execution/storage, independently bound sink identity, key rotation and validated completeness of resource paths.

## Three end-to-end fraud scenarios

**A — Fake property + promoted placement.** An authenticated but unverified property cannot obtain a publication grant; a legitimate property can be published via the listing sink. Paid promotion separately requires sponsor, payer, why-shown metadata and the actual user-facing label. The Python system simulates verification status; it cannot prove a real building exists. The JavaScript module enforces its abstract rendering contract but does not prove actual visual perception on physical browsers.

**B — Legitimate account used for phishing.** A real operator account with a real booking can propose an unauthorized payment link, but message validation checks booking-to-recipient binding, permitted payment host, merchant and the actual content before simulated dispatch. Content scanning also checks obvious URLs regardless of a caller-supplied `requests_payment` flag. This is **not** a complete phishing classifier; sophisticated obfuscation, redirect chains, look-alike hosts and external phishing routes require additional real-world safeguards.

**C — Approved payment beneficiary substituted.** A correct beneficiary/amount/currency is approved first. If a connector changes the final merchant before the mock payment submission, the Finality Sink rejects it. A successfully consumed grant cannot be replayed, and concurrent uses result in a single mock effect. No external payment processor is invoked or synchronously committed.

Other demonstrations cover scoped delegation, restricted guest-data export, risky operators, revoked authority, property revocation, indeterminate payment outcomes, incident notification, malformed operation descriptors and hash-chained audit records.

## What counts as an implemented control?

**Implemented as executable models:** SQLite-backed verification flags; synthetic VI–CJT-like context; bounded operation grants; digest-based pending/actual request matching; finality sinks; controlled mock publication and dispatch; basic booking-to-merchant check; HMAC CVID helper; risk/revocation generations; mocked outcome reconciliation; ad metadata and rendering contracts; concurrent single-use grant tests.

**NOT implemented as production enforcement:** physical property verification or KYBC; sovereign jurisdiction determinations; production CVID envelope issuance across channels; comprehensive semantic phishing detection; independent trusted hardware PED/TEE/HSM; network-level path closure; actual PSP transaction finality; distributed cryptographic revocation convergence; browser end-to-end visual verification; iOS/Android application security; real consumer-notification delivery; an actual regulatory DSA compliance assessment.

These distinctions are critical. Tests that pass in this simulator do not establish that an untrusted host cannot spoof sink identities, bypass protected execution, restore database snapshots or redirect through an unmonitored interface. See [`docs/SECURITY_LIMITATIONS.md`](docs/SECURITY_LIMITATIONS.md).

## Design rationale / performance

Most *costly* onboarding and property validation happens outside the latency-sensitive request path. Fast-path enforcement compares compact operation descriptors to local authority records and the actual operation. Protected SQLite state and the mock effect are committed within one local transaction in the Python implementation. This gives testable **in-process** atomicity, **not** payment-processor or multi-service atomicity.

The repository includes `scripts/benchmark.py`, which measures `digest`, `authorize`, `effect` and `authorize + effect` on synthetic messages in a single-process in-memory SQLite model. Its output is retained in `reports/LOCAL_BENCHMARK.json`. **Do not report these microbenchmark results as incremental p95 latency for a production VLOP**—there are no cross-region network hops, external payment rails, real fraud scoring, production databases, fault injection or trusted hardware operations. The proposal's latency ranges are separate *unvalidated production engineering targets*.

For plausible VLOP integration, use the staged path **observe → shadow-evaluate → enforce selected boundary → verify bypass closure → expand**, preserving existing authentication, payment/fraud detection and business workflows. [`docs/DEPLOYMENT_AND_PERFORMANCE.md`](docs/DEPLOYMENT_AND_PERFORMANCE.md) sets out the engineering assumptions and failure modes.

## CI and results

`.github/workflows/ci.yml` runs Python, Go and JavaScript independently and uploads reports from each environment. The checked-in `reports/TEST_REPORT.md` states the exact validation performed in this local environment. `reports/python-junit.xml`, `reports/go-test.json`, `reports/node-tests.tap` and coverage artifacts are included for reproducibility. Run tests on your GitHub account to confirm results independently.

## Licensing, attribution and research boundaries

**Copyright (c) 2026 Sangam Kumar Das.** This repository uses a **custom Non-Commercial Research and Evaluation License** (`LICENSE`), not an OSI-approved license. It permits non-production research, inspection, reproducibility and restricted sharing under its terms. **Commercial deployment and integration require separate written permission.** No patent license is granted by this software license. Third-party packages retain their own licenses. The copyright/license terms for this repository do **not** change the license or accessibility of the separately published Zenodo work or any patent/IETF disclosure.

This code is provided without warranty. Consider qualified counsel review before relying on custom license provisions. There is no relationship to or endorsement from Booking.com, Google, the European Commission or any other marketplace.

## Citation

Project: *DAS Marketplace Fraud Prevention — Multi-Language Reference Implementation with 200 Automated Checks* (2026). Related proposal: [Zenodo Record 23689735](https://zenodo.org/records/23689735). This repository's software tests are a subsequent reference implementation and should not be described as previously executed in the Zenodo proposal.
