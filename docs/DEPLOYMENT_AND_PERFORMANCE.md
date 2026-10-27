# VLOP deployment, legacy integration and latency feasibility

This is an engineering feasibility guide—not a measured performance claim about any deployed online platform.

## Deployment strata

1. **Slow path:** identify verified operator, real-world property evidence, correct payment beneficiaries and required compliance context. Trigger again for material changes or credible risk signals. These checks can be slow and human-assisted.
2. **Fast path:** verify operator/property/delegation/booking context and exact pending effect, bound to current revocation state, at the publication/messaging/payment/advertisement boundary.
3. **Accountability:** persist effect outcomes and appropriate evidence; conduct after-the-fact analysis and independent testing asynchronously *only where safety does not depend on completing the action synchronously*.

## Suggested boundaries for a large legacy service

| Existing component | Integration point | Proof obligation |
| --- | --- | --- |
| Provider/identity system | VI–CJT-like record adapter | Authenticated principal and accurate property authority |
| Listing publish worker | Mock/real native commit interceptor | Final content version and authorization still match |
| Ranking service | Ad classification metadata contract | Boosted placement propagated with required metadata |
| Frontend rendering | Label display contract + UI QA | Correct visible payer, sponsor, reason and controls |
| Reservation store | Booking context resolver | Current booking identity, merchant, guest and terms |
| Messaging dispatcher | Protected outbound dispatch | Actual recipient, body, links, purpose, current revocation |
| Payment connector | Native PSP API wrapper | Actual payee/amount/currency, request idempotency and reconciliation |
| Event broker/worker | Revalidation before final effect | Queued jobs do not execute under stale authority |
| Incident response | Revocation-generation coordinator | Reduction of authority reaches every in-scope path |
| Audit and risk assessment | Correlated protected event IDs | Evidence can reconstruct authorized and denied outcomes |

## Adoption stages

**Inventory → shadow mode → narrow effectuation enforcement → recovery validation → alternate-path closure → expanded rollout.** A proxy alone does not close background jobs, browser automation, batch scripts, operator consoles and independent connectors. Expand the declared guarantee only after proving these routes are controlled or disabled.

## Production pilot targets from the proposal, NOT measurements

- Advertising server-side disclosure check: *additional p95 3–15 ms*.
- Protected booking message dispatch: *additional p95 10–40 ms*.
- Payment pre-submission validation: *additional p95 15–60 ms*.
- Verified listing publication: *additional p95 20–80 ms*.

These are **illustrative targets** conditional on nearby authorization services, precomputed identity verification, low contention and suitable local transactional primitives. Component percentiles must not be added to derive an overall percentile; instrument paired end-to-end workloads instead. External fraud scoring, banking networks and real property reviews are excluded. Real systems need p99, peak-load and degradation budgets as well.

## What the included microbenchmark actually measures

`python scripts/benchmark.py` executes 1,200 synthetic local message operations through an in-process Python function and in-memory SQLite database. It reports p50/p95/p99 for digest-only, authorization, mock finality, and combined work. No network overhead, disk durability, OS process isolation, hardware key services, real payment or message provider, distributed state or regional replication is included. The digest-only trace is **not** a realistic control-group transaction and results cannot be used to claim incremental VLOP production overhead.

## Engineering objections with substantive answers

- **Too slow:** Preverify static identity/physical-property evidence and use compact operation-bound descriptors at the fast path, not expensive onboarding on every request. Benchmark persistent transactional state, not merely policy evaluation.
- **Legacy rewrites:** Add adapters and interceptors at existing publication/dispatch/processor boundaries. Do not claim an integration works if policy constraints disappear in protocol conversion.
- **Global revocation:** Use generation-bound local enforcement with authenticated convergence evidence or upstream compensating denial. Do not claim instantaneous global invalidation.
- **Outage:** High-consequence actions remain non-effective, but harmless informational operations can continue if governed by a separate applicable policy. Queue and re-evaluate on recovery.
- **Client rendering:** A backend label flag is insufficient; test actual browsers, localization, accessibility, old clients and dynamic presentation transformations.
- **False positives:** Investigate and appeal; distinguish incomplete evidence from proof of fraud. Avoid disproportionate removal or permanent restrictions without review.
- **Atomic payments:** Local authorization/dispatch can be atomic in a platform controller; external settlement is NOT atomically committed with local SQLite. Use stable PSP transaction references and reconciliation.

## Recommended independent pilot metrics

Record denied attack scenarios, false positives on legitimate operations, path coverage, actual in-scope side effects, p50/p95/p99 overhead, throughput, CPU cost, storage writes, queue delay, revocation convergence, retry ambiguity, and browser label observability. Show sample sizes, load conditions, test version, cryptographic primitives, platform/hardware versions and outstanding limitations.
