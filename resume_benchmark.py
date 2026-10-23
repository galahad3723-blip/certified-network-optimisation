"""Resume a complete-anchor checkpoint without changing the benchmark methods.

The original driver remains intact. The substitutions below only restore its
accumulators, skip already saved anchors, and distinguish segment wall time
from the unavailable total wall time of the interrupted execution.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    source_path = ROOT / 'run_benchmark.py'
    source = source_path.read_text()
    destination = ROOT / 'results' / 'preresume_checkpoint'
    destination.mkdir(exist_ok=True)
    files = ['anchors.csv', 'cases.csv', 'runs.csv', 'failures.json', 'protocol.json']
    for name in files:
        target = destination / name
        if not target.exists():
            shutil.copy2(ROOT / 'results' / name, target)
    original = 'anchors=[];cases=[];runs=[];failures=[];topology_info={};route_cache={}'
    restore = '''anchors=pd.read_csv(OUT/'anchors.csv',float_precision='round_trip').to_dict('records')
    cases=pd.read_csv(OUT/'cases.csv',float_precision='round_trip').to_dict('records')
    runs=pd.read_csv(OUT/'runs.csv',float_precision='round_trip').to_dict('records')
    failures=json.loads((OUT/'failures.json').read_text())
    topology_info={name:topology(DATA/(name+'.graphml'))[2] for name in TOPOLOGIES}
    route_cache={}
    completed={row['anchor'] for row in anchors}
    assert len(completed)==len(anchors)
    for row in anchors:
        key=row['anchor'];expected=4 if row['split']=='core' else 2
        assert sum(c['anchor']==key for c in cases)==expected
        assert sum(r['anchor']==key for r in runs)==12*expected
        assert (saved/(key+'.npz')).exists()
    print(f'Resuming {len(anchors)} saved anchors, {len(cases)} cases and {len(runs)} runs',flush=True)'''
    assert source.count(original) == 1
    source = source.replace(original, restore)
    keyline = "key=f'{split}_{tname}_{seed}_{d}_{family}_xi{xi:g}'"
    assert source.count(keyline) == 1
    source = source.replace(keyline, keyline + '\n        if key in completed:continue')
    elapsed = "'total_seconds':time.perf_counter()-began,"
    assert source.count(elapsed) == 1
    source = source.replace(elapsed, "'total_seconds':None,'resume_segment_seconds':time.perf_counter()-began,")
    scope = {'resume_date_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
             'reason':'Previous execution ended after 154 complete anchors; remaining two scaling anchors resumed.',
             'original_benchmark_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
             'resume_driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'executed_instrumented_driver_sha256':hashlib.sha256(source.encode()).hexdigest(),
             'checkpoint_sha256':{n:hashlib.sha256((destination/n).read_bytes()).hexdigest() for n in files},
             'timing_scope':'Original within-case repetitions retained; resumed cases measured in a later process. Original full wall time unavailable.'}
    (ROOT/'results'/'resume_history.json').write_text(json.dumps(scope,indent=2)+'\n')
    namespace = {'__file__':str(source_path),'__name__':'__main__'}
    exec(compile(source,str(source_path),'exec'),namespace)


if __name__ == '__main__':
    main()
