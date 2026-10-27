"""Synthetic local microbenchmark, NOT production latency or comparison to a real VLOP."""
import json, math, platform, statistics, sys, time
from pathlib import Path
from marketguard import Marketplace, digest

N=1200
m=Marketplace()
m.register('owner',verified=True)
m.property('P1','owner',verified=True,evidence='synthetic-check')
m.booking('B1','P1','guest1','merchant1',500,'EUR','https://pay.example.test')
base={'booking':'B1','recipient':'guest1','text':'Welcome','requests_payment':False}
def compute_percentiles(arr):
    a=sorted(arr)
    def perc(p):return round(a[min(len(a)-1,math.ceil(len(a)*p/100)-1)],4)
    return {'n':len(a),'p50_ms':perc(50),'p95_ms':perc(95),'p99_ms':perc(99),'mean_ms':round(statistics.mean(a),4),'max_ms':round(a[-1],4)}
# Compare digest-only work to end-to-end protected simulated operation; not a
# controlled measurement of incremental production latency.
for _ in range(100):
    payload={**base,'sequence':_}
    g=m.authorize('owner','P1','message',payload)
    assert m.effect(g,'messaging_sink',payload).allowed
baseline=[]; authorize=[]; finality=[]; combined=[]
for i in range(N):
    body={**base,'sequence':1000+i}
    t0=time.perf_counter_ns();digest(body);t1=time.perf_counter_ns()
    g=m.authorize('owner','P1','message',body);t2=time.perf_counter_ns()
    assert m.effect(g,'messaging_sink',body).allowed;t3=time.perf_counter_ns()
    baseline.append((t1-t0)/1e6)
    authorize.append((t2-t1)/1e6)
    finality.append((t3-t2)/1e6)
    combined.append((t3-t1)/1e6)
result={'title':'SYNTHETIC IN-PROCESS SQLITE MODEL ONLY','measured':True,'production_latency_claim':False,
    'sample_count':N,'runtime':{'python':platform.python_version(),'platform':platform.platform()},
    'note':'No network, payment processor, trusted hardware, real properties, external fraud checks, service mesh or production data. No VLOP comparison. Test machine contention and disk durability differ.',
    'descriptor_digest_only':compute_percentiles(baseline),
    'authorize':compute_percentiles(authorize),
    'effect':compute_percentiles(finality),
    'authorize_plus_effect':compute_percentiles(combined)}
out=Path(__file__).resolve().parents[1]/'reports'/'LOCAL_BENCHMARK.json';out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
