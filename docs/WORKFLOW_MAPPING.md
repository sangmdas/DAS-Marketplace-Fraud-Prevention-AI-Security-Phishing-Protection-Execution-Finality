# Mapping of the user-provided 25 marketplace fraud-prevention steps

**Source:** independent technical proposal, *Technical Proposal: Verifiable Marketplace Fraud Prevention and Execution-Finality Architecture*, subsequently published at https://zenodo.org/records/23689735. The statuses below are intentionally conservative. `MOCK` means runnable local model only; `PARTIAL SIMULATION` means a selected aspect is exercised; `NOT IMPLEMENTED` means the essential operation is absent. No production functionality is implied.

| Step | Source workflow | Level | Relevant executable tests | Important limitation |
|---:|---|---|---|---|
| 1 | Platform-wide fraud-risk and threat-model establishment | PARTIAL SIMULATION | `None` | No full systemic fraud graph; risk and incident event fixtures only. |
| 2 | Accommodation-provider identity verification | MOCK | `test_01_identity` | Verified account flag is synthetic; no KYBC vendor or document validation. |
| 3 | Property existence, operating legitimacy and control verification | MOCK | `test_03_property` | Property existence and ownership are *not* established; reviewed flag only. |
| 4 | Create the property-bound Virtual Identity (VI) and Compliance Jurisdiction Context (CJT/CJS) | MOCK | `test_01_identity` | VI–CJT-like binding modeled by owner/property/action/country/generation. |
| 5 | Delegated personnel and third-party software authorization | MOCK | `test_02_delegation` | Operation-specific delegated permissions represented in SQLite. |
| 6 | Protected listing creation and publication | MOCK | `test_04_publication` | Pending grant and actual listing checked before a mock native commit. |
| 7 | Determine whether ranking is commercially influenced | MOCK | `test_05_advertising;web/advertising.test.mjs` | Paid placement metadata is contract-checked; no real ranker. |
| 8 | Verify the advertisement label at the display boundary | MOCK | `web/advertising.test.mjs` | HTML string equivalence model; no actual device/UI visual verification. |
| 9 | Record advertising explanations and repository evidence | PARTIAL SIMULATION | `test_05_advertising;test_14_audit` | Versioned model metadata and hash-chain; no Article 39 ad repository. |
| 10 | Validate actual price, availability and booking terms | PARTIAL SIMULATION | `test_06_booking` | Basic booking terms and idempotence fixtures, no inventory or price engine. |
| 11 | Establish an authoritative reservation context | MOCK | `test_06_booking;test_07_messaging_authorization` | Booking ID, guest, property, beneficiary, amount and currency. |
| 12 | Restrict guest-data access and export | MOCK | `test_11_data_export` | Purpose-based subset of mock fields, not real guest-data pipelines. |
| 13 | Verify communication origin through CVID | PARTIAL SIMULATION | `test_15_primitives` | HMAC CVID helper exists; not fully wired to live messaging service. |
| 14 | Evaluate message content and downstream effects | PARTIAL SIMULATION | `test_07_messaging_authorization` | Checks known payment URLs and declared payment purpose; no general NLP or redirect crawler. |
| 15 | Enforce outbound message finality | MOCK | `test_08_message_sink;test_17_fastapi_roundtrip` | Final message digest and fields checked at simulated outbound effect. |
| 16 | Govern external payment links and off-platform redirection | PARTIAL SIMULATION | `test_07_messaging_authorization` | Allowed payment host checked; external redirection chains not resolved. |
| 17 | Establish the booking-bound payment intent | MOCK | `test_09_payment_intent` | Synthetic booking-bound authorized merchant, amount and currency. |
| 18 | Validate at the actual payment-effectuation boundary | MOCK | `test_10_payment_sink;test_16_concurrent_single_use` | Sink-side actual operation match and single simulated atomic effect. |
| 19 | Control payment-detail changes and refunds | NOT IMPLEMENTED | `None` | Beneficiary amendment/refund approval workflow not built. |
| 20 | Reconcile asynchronous payments and uncertain outcomes | MOCK | `test_13_recovery` | Explicit completion/indeterminate states; no actual PSP settlement integration. |
| 21 | Continuously evaluate compromise and observation coverage | PARTIAL SIMULATION | `test_12_revocation` | Risk thresholds; no telemetry source integrity or model monitoring. |
| 22 | Revoke authority across all consequential paths | PARTIAL SIMULATION | `test_12_revocation;test_15_primitives` | Generations and path-set proof; no real distributed enforcement convergence. |
| 23 | Notify affected users and provide remediation | MOCK | `test_14_audit` | Incident and notification state, not real notification or consumer redress. |
| 24 | Maintain evidence of risk assessment and effective mitigation | PARTIAL SIMULATION | `test_14_audit` | Hash-chain for event records; no signed regulatory evidence or DSA certification. |
| 25 | Independent testing, regulatory reporting and corrective deployment | PARTIAL SIMULATION | `Entire tests/; reports/` | 200 local executable cases; no independent production deployment validation. |

All workflow claims are bounded by the threat model in `SECURITY_LIMITATIONS.md`. This matrix is not a patent claim chart and does not establish implementation of every technical variation in the proposal.
