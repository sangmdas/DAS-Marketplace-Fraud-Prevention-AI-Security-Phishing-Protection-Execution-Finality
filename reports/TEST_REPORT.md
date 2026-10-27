# Actual Local Test Report — DAS Marketplace Fraud Prevention

**Results were recorded from executed code, not a proposed or generated-only test matrix.**

| Suite | Passed | Failed | Description |
|---|---:|---:|---|
| Python / pytest | 152 | 0 | 15 groups of 10 parameterized tests plus concurrency and FastAPI integration |
| Go / go test | 24 | 0 | 20 admission matrix cases, 4 standalone gateway/replay/HTTP/concurrency tests |
| JavaScript / node:test | 24 | 0 | 24 paid-placement, rendering contract, tamper, encoding cases |
| **Total** | **200** | **0** | Model-level reproducible checks only |

Python line coverage: **93.1%**; branch coverage: **90.2%**, of the small Python package included in this repository. Coverage is NOT coverage of all 25 workflows or a deployed marketplace.

## Local microbenchmark (not VLOP production latency)

1,200 synthetic message operations, in-process Python + in-memory SQLite; p95 combined authorize + effect = **0.1167 ms**, p99 = **0.2012 ms** in this container session. This result excludes inter-service networking, real money, encryption services/HSMs, production transaction coordination, durable writes, fraud models, geographical replication and actual messaging delivery. **Do not compare directly with the proposed 10–40 ms / 15–60 ms p95 production pilot budgets.**

## Evidence files

- `python-junit.xml`: Python executed cases.
- `python-coverage.xml`: Python measured line/branch coverage.
- `python-results.txt`: exact console output.
- `go-test.json` and `go-verbose.txt`: Go executed cases and individual results.
- `node-tests.tap`: JavaScript executed cases.
- `LOCAL_BENCHMARK.json`: raw synthetic p50/p95/p99 samples.
- `../docs/TEST_CATALOG.csv`: 200 stable case IDs and test names.

## Caveats

A green test cannot guarantee fraud elimination, DSA compliance, a genuine hotel/property, real payment settlement, real mobile-browser advertising disclosures, or a production non-bypassable Finality Sink. The Go gateway accepts prevalidated attributes from JSON fixtures and the local HTTP examples do not authenticate real identities. The Python in-process mock store is not a TEE or persistent multi-node protected enforcement domain. Review `SECURITY_LIMITATIONS.md` before using the result publicly.
