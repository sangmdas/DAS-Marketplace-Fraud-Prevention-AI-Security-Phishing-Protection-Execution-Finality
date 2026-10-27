# Threat model, trusted boundaries and limitations

## Trust assumptions

The repository is a deliberately scoped educational model. The Python protected enforcement domain is an ordinary in-process SQLite connection protected by a Python lock, **not hardware-enforced protected state**. Its security assumes the Python process and its local database cannot be modified by an attacker. The `sink` string in the REST demo is caller supplied: **it is not an authenticated sink identity**. The Go admission service accepts `verified_actor`, `verified_property`, `authorized_destination` and generation fields in its JSON input: these are fixture inputs, **not trustworthy attestations**. Its replay map is process-local, not durable across restart. The JavaScript gate compares an expected HTML string to a given string and is not a real DOM or native mobile presentation attestation. CVID uses HMAC with a test-only in-process key; its distribution and replay lifecycle are not represented.

## Modeled attacker capabilities

- Controls a hotel login, tries unauthorized payment request to guest.
- Provides unverified property and counterfeit listing draft.
- Alters material payment fields between authorization and mock effectuation.
- Replays used grants; races duplicate requests; tries stale revocation generation.
- Supplies paid ranking result missing legally relevant disclosure metadata.
- Exploits malformed URLs, missing booking details, changed recipients and disallowed data fields.

## Important unmodeled attacker capabilities

- Operating-system/host administrator compromise, kernel bypass, HSM/TEE/IOMMU attacks.
- Forged trusted-service authentication or direct access to the mock SQLite store.
- Network proxies, DNS rebinding, redirect chains and Unicode/IDN homoglyphs.
- SSRF, malicious HTML beyond the demonstrated encoding invariants, XSS in a complete web app.
- Underlying property authenticity, stolen legitimate business credentials or beneficial-ownership deception.
- Off-platform messaging and off-platform payment initiated independently by a consumer.
- Payment-processor settlement guarantees, refunds and chargebacks.
- Multi-region distributed consensus, pending queue continuation, clock rollback, crash consistency to durable storage.
- Live user accessibility and actual rendered advertising compliance on mobile/browser devices.

## Assertions that SHOULD NOT be made

Do not claim the project has implemented a production non-bypassable Finality Sink, enforceable non-bearer capability, actual HSM-backed PED, Booking.com fraud defenses, native iOS/Android app integration, or proven DSA legal compliance. The simulated single-use grants depend on control of the entire program and store. An attacker who can call the unauthenticated example API and manipulate its trusted environment can bypass the research assumptions.

## Security path to production

For a real deployment, separate trusted authorization from caller-controlled data; bind service identity with mTLS/SPIFFE or equivalent; authenticate sink identity at a boundary outside the workload; run independently measured canonicalization of the *actual* final operation; protect key state and monotonic generations against rollback; use durable transactional consumption and external processor idempotency; inventory alternate egress/publication paths; enforce message and payment verification for all relevant services; implement suitable privacy-preserving telemetry; verify performance and denial/recovery behavior under failures; and commission independent penetration tests, property-verification reviews, and accessibility/ad-label UI audits. When mandatory evidence is missing, high-consequence effects should be held or denied without representing detection as certainty.
