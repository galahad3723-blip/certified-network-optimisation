"""Recompute every saved reference and reusable certificate from stored arrays."""
from pathlib import Path
import ast
import hashlib
import json
from certified_num import NUM, PriceRay
import numpy as np
import pandas as pd
from scipy import sparse


def numerical_ast_hash(source):
    """Hash the complete AST apart from module prose and status descriptions."""
    class PresentationText(ast.NodeTransformer):
        def visit_Module(self, node):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body = node.body[1:]
            return self.generic_visit(node)

        def visit_Dict(self, node):
            self.generic_visit(node)
            for i, key in enumerate(node.keys):
                if (isinstance(key, ast.Constant) and key.value == 'status'
                        and isinstance(node.values[i], ast.Constant)
                        and isinstance(node.values[i].value, str)):
                    node.values[i] = ast.Constant(value='status description')
            return node

    tree = PresentationText().visit(ast.parse(source))
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()


def verify_source_identity(root, name, executed_digest, revisions):
    path = root/name
    current = hashlib.sha256(path.read_bytes()).hexdigest()
    if current == executed_digest:
        return {'mode':'exact', 'executed_sha256':executed_digest, 'current_sha256':current}
    record = revisions['files'][name]
    assert record['executed_sha256'] == executed_digest
    assert record['current_sha256'] == current
    assert record['numerical_ast_sha256'] == numerical_ast_hash(path.read_text())
    assert record['numerical_ast_unchanged'] is True
    return {'mode':'documented_text_revision', **record}


def main():
    root = Path(__file__).resolve().parent
    folder = root/'results'
    env = json.loads((folder/'environment.json').read_text())
    revision_path = folder/'source_text_revision.json'
    revisions = json.loads(revision_path.read_text()) if revision_path.exists() else {}
    cases = pd.read_csv(folder/'cases.csv')
    runs = pd.read_csv(folder/'runs.csv')
    anchors = pd.read_csv(folder/'anchors.csv')
    assert (len(anchors), len(cases), len(runs)) == (156, 600, 7200)
    assert not runs.duplicated(['case','method','repeat']).any()
    assert runs.groupby('case').size().eq(12).all()
    assert cases.groupby('anchor').size().isin([2,4]).all()
    assert int((cases.split=='core').sum()) == 576
    assert int((cases.split=='scaling').sum()) == 24
    assert np.isfinite(runs[['seconds','amortized_seconds','gap_per_weight']]).all().all()
    assert (runs.seconds>0).all()
    assert (runs[runs.converged].gap_per_weight<=1e-3+1e-12).all()
    checkpoint = folder/'preresume_checkpoint'
    checkpoint_counts = {}
    if checkpoint.exists():
        for name, final in [('anchors',anchors),('cases',cases),('runs',runs)]:
            previous = pd.read_csv(checkpoint/(name+'.csv'),float_precision='round_trip')
            current = pd.read_csv(folder/(name+'.csv'),float_precision='round_trip')
            pd.testing.assert_frame_equal(previous,current.iloc[:len(previous)].reset_index(drop=True),
                                          check_exact=True)
            checkpoint_counts[name]=len(previous)
        history=json.loads((folder/'resume_history.json').read_text())
        assert history['original_benchmark_sha256']==env['benchmark_sha256']
        assert history['resume_driver_sha256']==hashlib.sha256((root/'resume_benchmark.py').read_bytes()).hexdigest()
        for name,digest in history['checkpoint_sha256'].items():
            assert digest==hashlib.sha256((checkpoint/name).read_bytes()).hexdigest()
    source_identity = {
        name:verify_source_identity(root, name, env[field], revisions)
        for field, name in [('source_sha256','certified_num.py'), ('benchmark_sha256','run_benchmark.py')]
    }
    maximum_reference_error = 0.
    maximum_reuse_error = 0.
    maximum_reference_overload = 0.
    maximum_reuse_overload = 0.
    maximum_anchor_overload = 0.
    checked = 0
    for anchor, group in cases.groupby('anchor', sort=False):
        with np.load(folder/'instances'/(anchor+'.npz'), allow_pickle=False) as data:
            A = sparse.csr_matrix((data['A_data'], data['A_indices'], data['A_indptr']),
                                  shape=tuple(data['A_shape']))
            model = NUM(A, data['w'], data['xi'])
            x0, lam0, c0 = data['anchor_x'], data['anchor_lam'], data['c0']
            maximum_anchor_overload = max(maximum_anchor_overload, model.overload(x0,c0))
            cache = PriceRay(model,lam0)
            for row in group.itertuples():
                c = data[row.shock+'_c']
                ref_x = data[row.shock+'_reference_x']
                ref_lam = data[row.shock+'_reference_lam']
                candidate = data[row.shock+'_reuse_x']
                upper = model.dual(ref_lam,c)[0]
                reference_gap = max(0.,(upper-model.utility(ref_x))/model.W)
                query = cache.query(c,x0)
                maximum_reference_error = max(maximum_reference_error,abs(reference_gap-row.reference_gap))
                maximum_reuse_error = max(maximum_reuse_error,abs(query['gap_per_weight']-row.precheck_gap))
                assert np.allclose(candidate,query['x'],rtol=1e-12,atol=1e-12)
                assert np.allclose(max(0.,(upper-model.utility(candidate))/model.W),row.actual_regret_upper,rtol=1e-8,atol=1e-12)
                assert query['upper']-model.utility(candidate)>=-1e-8*model.W
                maximum_reference_overload = max(maximum_reference_overload,model.overload(ref_x,c))
                maximum_reuse_overload = max(maximum_reuse_overload,model.overload(candidate,c))
                checked += 1
    assert maximum_reference_error<1e-10
    assert maximum_reuse_error<1e-10
    assert max(maximum_anchor_overload,maximum_reference_overload,maximum_reuse_overload)<1e-9
    manifest = json.loads((root/'data'/'InternetTopologyZoo'/'SOURCE_MANIFEST.json').read_text())
    graph_hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((root/'data'/'InternetTopologyZoo').glob('*.graphml'))}
    assert len(graph_hashes)==6
    for item in manifest['files']:
        assert graph_hashes[item['name']+'.graphml']==item['sha256']
        raw=(root/'data'/'InternetTopologyZoo'/(item['name']+'.graphml')).read_bytes()
        git_hash=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        assert git_hash==item['git_blob_sha1']
    result = {'passed':True, 'anchors':len(anchors), 'capacity_cases_recomputed':checked,
              'timing_records':len(runs),
              'source_hashes_match_executed_code':all(v['mode']=='exact' for v in source_identity.values()),
              'numerical_source_unchanged':True, 'source_identity':source_identity,
              'preresume_checkpoint_values_preserved_exactly':True if checkpoint_counts else None,
              'preresume_checkpoint_counts':checkpoint_counts,
              'maximum_reference_gap_recomputation_error':maximum_reference_error,
              'maximum_reuse_gap_recomputation_error':maximum_reuse_error,
              'maximum_anchor_overload':maximum_anchor_overload,
              'maximum_reference_overload':maximum_reference_overload,
              'maximum_reuse_overload':maximum_reuse_overload,
              'graph_sha256':graph_hashes, 'graph_sha256_and_git_blob_hashes_match_manifest':True,
              'scope':'float64 consistency checks, not interval arithmetic or an independent novelty review'}
    (folder/'saved_result_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
