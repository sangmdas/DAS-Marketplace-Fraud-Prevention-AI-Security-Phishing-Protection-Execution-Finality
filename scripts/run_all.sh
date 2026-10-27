#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p reports
python -m pytest -q --junitxml=reports/python-junit.xml --cov=marketguard --cov-branch --cov-report=term-missing --cov-report=xml:reports/python-coverage.xml | tee reports/python-results.txt
(cd go/gateway && go test -count=1 -v ./...) | tee reports/go-verbose.txt
(cd go/gateway && go test -count=1 -json ./...) > reports/go-test.json
(cd web && npm test) | tee reports/node-tests.tap
python scripts/benchmark.py > reports/LOCAL_BENCHMARK.stdout.txt
python scripts/build_report.py
