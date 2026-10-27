"""Generate a transparent source-to-implementation mapping, including NOT IMPLEMENTED status."""
import re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(Path('/mnt/data/Untitled 20.txt') if Path('/mnt/data/Untitled 20.txt').exists() else root/'docs'/'SOURCE_EXCERPT.txt')
headings=re.findall(r'^Step (\d+) — ([^\n]+)',source.read_text(),re.M)
assert len(headings)==25
rows=[
('PARTIAL SIMULATION','None','No full systemic fraud graph; risk and incident event fixtures only.'),
('MOCK','test_01_identity','Verified account flag is synthetic; no KYBC vendor or document validation.'),
('MOCK','test_03_property','Property existence and ownership are *not* established; reviewed flag only.'),
('MOCK','test_01_identity','VI–CJT-like binding modeled by owner/property/action/country/generation.'),
('MOCK','test_02_delegation','Operation-specific delegated permissions represented in SQLite.'),
('MOCK','test_04_publication','Pending grant and actual listing checked before a mock native commit.'),
('MOCK','test_05_advertising;web/advertising.test.mjs','Paid placement metadata is contract-checked; no real ranker.'),
('MOCK','web/advertising.test.mjs','HTML string equivalence model; no actual device/UI visual verification.'),
('PARTIAL SIMULATION','test_05_advertising;test_14_audit','Versioned model metadata and hash-chain; no Article 39 ad repository.'),
('PARTIAL SIMULATION','test_06_booking','Basic booking terms and idempotence fixtures, no inventory or price engine.'),
('MOCK','test_06_booking;test_07_messaging_authorization','Booking ID, guest, property, beneficiary, amount and currency.'),
('MOCK','test_11_data_export','Purpose-based subset of mock fields, not real guest-data pipelines.'),
('PARTIAL SIMULATION','test_15_primitives','HMAC CVID helper exists; not fully wired to live messaging service.'),
('PARTIAL SIMULATION','test_07_messaging_authorization','Checks known payment URLs and declared payment purpose; no general NLP or redirect crawler.'),
('MOCK','test_08_message_sink;test_17_fastapi_roundtrip','Final message digest and fields checked at simulated outbound effect.'),
('PARTIAL SIMULATION','test_07_messaging_authorization','Allowed payment host checked; external redirection chains not resolved.'),
('MOCK','test_09_payment_intent','Synthetic booking-bound authorized merchant, amount and currency.'),
('MOCK','test_10_payment_sink;test_16_concurrent_single_use','Sink-side actual operation match and single simulated atomic effect.'),
('NOT IMPLEMENTED','None','Beneficiary amendment/refund approval workflow not built.'),
('MOCK','test_13_recovery','Explicit completion/indeterminate states; no actual PSP settlement integration.'),
('PARTIAL SIMULATION','test_12_revocation','Risk thresholds; no telemetry source integrity or model monitoring.'),
('PARTIAL SIMULATION','test_12_revocation;test_15_primitives','Generations and path-set proof; no real distributed enforcement convergence.'),
('MOCK','test_14_audit','Incident and notification state, not real notification or consumer redress.'),
('PARTIAL SIMULATION','test_14_audit','Hash-chain for event records; no signed regulatory evidence or DSA certification.'),
('PARTIAL SIMULATION','Entire tests/; reports/','200 local executable cases; no independent production deployment validation.'),
]
with (root/'docs'/'WORKFLOW_MAPPING.md').open('w') as f:
 f.write('# Mapping of the user-provided 25 marketplace fraud-prevention steps\n\n')
 f.write('**Source:** independent technical proposal, *Technical Proposal: Verifiable Marketplace Fraud Prevention and Execution-Finality Architecture*, subsequently published at https://zenodo.org/records/23689735. The statuses below are intentionally conservative. `MOCK` means runnable local model only; `PARTIAL SIMULATION` means a selected aspect is exercised; `NOT IMPLEMENTED` means the essential operation is absent. No production functionality is implied.\n\n')
 f.write('| Step | Source workflow | Level | Relevant executable tests | Important limitation |\n|---:|---|---|---|---|\n')
 for (n,name),(status,tests,limit) in zip(headings,rows):
  f.write(f'| {n} | {name.replace("|","/")} | {status} | `{tests}` | {limit} |\n')
 f.write('\nAll workflow claims are bounded by the threat model in `SECURITY_LIMITATIONS.md`. This matrix is not a patent claim chart and does not establish implementation of every technical variation in the proposal.\n')
# retain source snapshot to make mapping traceable after leaving container
(root/'docs'/'SOURCE_EXCERPT.txt').write_text(source.read_text())
