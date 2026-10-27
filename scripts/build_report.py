"""Assemble a report only from actual local machine-readable executed results."""
import json, csv, re, xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parents[1];reports=root/'reports'
root_xml=ET.parse(reports/'python-junit.xml').getroot()
pycases=[e for e in root_xml.findall('.//testcase')]
py_pass=[e for e in pycases if not e.findall('failure') and not e.findall('error') and not e.findall('skipped')]
go_actions=[json.loads(l) for l in (reports/'go-test.json').read_text().splitlines() if l.strip()]
go_cases=[e['Test'] for e in go_actions if e.get('Action')=='pass' and e.get('Test') and (e['Test'].count('/') or e['Test']!='TestAdmissionMatrix')]
node_text=(reports/'node-tests.tap').read_text()
node_cases=re.findall(r'^# Subtest: (.*)$',node_text,re.M)
node_summary=re.search(r'^# pass (\d+)$',node_text,re.M)
coverage=ET.parse(reports/'python-coverage.xml').getroot()
line_cov=float(coverage.attrib['line-rate'])*100
branch_cov=float(coverage.attrib['branch-rate'])*100
bench=json.loads((reports/'LOCAL_BENCHMARK.json').read_text())
assert len(py_pass)==152,(len(py_pass),len(pycases))
assert len(go_cases)==24,(len(go_cases),go_cases)
assert len(node_cases)==24,(len(node_cases),node_cases)
assert int(node_summary.group(1))==24
rows=[]
for ix,e in enumerate(py_pass,1):
    rows.append((f'PY-{ix:03d}','Python',e.attrib['name'],e.attrib['classname'],'PASSED','pytest-junit'))
for ix,name in enumerate(go_cases,1):
    rows.append((f'GO-{ix:03d}','Go',name,'go/gateway','PASSED','go-test-json'))
for ix,name in enumerate(node_cases,1):
    rows.append((f'JS-{ix:03d}','JavaScript',name,'web/advertising.test.mjs','PASSED','node-tap'))
with (root/'docs'/'TEST_CATALOG.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['case_id','language','case_name','source','status','report_source']);w.writerows(rows)
txt=f'''# Actual Local Test Report — DAS Marketplace Fraud Prevention

**Results were recorded from executed code, not a proposed or generated-only test matrix.**

| Suite | Passed | Failed | Description |
|---|---:|---:|---|
| Python / pytest | {len(py_pass)} | 0 | 15 groups of 10 parameterized tests plus concurrency and FastAPI integration |
| Go / go test | {len(go_cases)} | 0 | 20 admission matrix cases, 4 standalone gateway/replay/HTTP/concurrency tests |
| JavaScript / node:test | {len(node_cases)} | 0 | 24 paid-placement, rendering contract, tamper, encoding cases |
| **Total** | **{len(rows)}** | **0** | Model-level reproducible checks only |

Python line coverage: **{line_cov:.1f}%**; branch coverage: **{branch_cov:.1f}%**, of the small Python package included in this repository. Coverage is NOT coverage of all 25 workflows or a deployed marketplace.

## Local microbenchmark (not VLOP production latency)

1,200 synthetic message operations, in-process Python + in-memory SQLite; p95 combined authorize + effect = **{bench['authorize_plus_effect']['p95_ms']:.4f} ms**, p99 = **{bench['authorize_plus_effect']['p99_ms']:.4f} ms** in this container session. This result excludes inter-service networking, real money, encryption services/HSMs, production transaction coordination, durable writes, fraud models, geographical replication and actual messaging delivery. **Do not compare directly with the proposed 10–40 ms / 15–60 ms p95 production pilot budgets.**

## Evidence files

- `python-junit.xml`: Python executed cases.
- `python-coverage.xml`: Python measured line/branch coverage.
- `python-results.txt`: exact console output.
- `go-test.json` and `go-verbose.txt`: Go executed cases and individual results.
- `node-tests.tap`: JavaScript executed cases.
- `LOCAL_BENCHMARK.json`: raw synthetic p50/p95/p99 samples.
- `../docs/TEST_CATALOG.csv`: {len(rows)} stable case IDs and test names.

## Caveats

A green test cannot guarantee fraud elimination, DSA compliance, a genuine hotel/property, real payment settlement, real mobile-browser advertising disclosures, or a production non-bypassable Finality Sink. The Go gateway accepts prevalidated attributes from JSON fixtures and the local HTTP examples do not authenticate real identities. The Python in-process mock store is not a TEE or persistent multi-node protected enforcement domain. Review `SECURITY_LIMITATIONS.md` before using the result publicly.
'''
(reports/'TEST_REPORT.md').write_text(txt)
print(txt)
