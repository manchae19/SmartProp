"""Strict snapshot replay, comparing undirected edges independent of order."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import review_property_expansion as source
from market_observations import canonical


def edge_multiset(edges):
    result = Counter()
    for edge in edges:
        left,right = sorted([edge['left'],edge['right']])
        result[canonical(dict(edge,left=left,right=right))] += 1
    return result


def verify(directory):
    decisions,failed,features,proofs,links,summary,inputs,protected = source.artifacts()
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf8'))
    if manifest['input_sha256'] != inputs or manifest['protected_sha256'] != protected:
        raise ValueError('Source/protection identity differs')
    expected_id = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16]
    if directory.name != expected_id:raise ValueError('Run fingerprint differs')
    source.collect.audit.c.verify(manifest['output_sha256'],directory)
    for path,expected in {**inputs,**protected}.items():
        actual = Path(path) if Path(path).is_absolute() else source.BASE/path
        if source.collect.cafe.sha(actual) != expected:raise ValueError('Protected/input file differs')
    sets = dict(decisions_private_DO_NOT_TRAIN=decisions,parse_failures=failed,
                current_snapshots_DO_NOT_TRAIN=features,evidence_private_DO_NOT_TRAIN=proofs)
    for name,rows in sets.items():
        fields = list(dict.fromkeys(k for r in rows for k in r))
        if name=='parse_failures':fields=['record_key','observed_at','source','response_sha256','reason','training_allowed']
        expected = [{k:source.grouping.previous.scalar(r.get(k)) for k in fields} for r in rows]
        if source.collect.audit.c.read(directory/(name+'.csv')) != expected:
            raise ValueError('Snapshot/claim/quote replay differs: '+name)
    saved_links = json.loads((directory/'group_links.json').read_text(encoding='utf8'))
    # set iteration in the archived shingle matcher changes edge order between
    # processes. Keep every edge/rule/score/duplicate; only direction/order is
    # immaterial for this undirected grouping graph.
    if edge_multiset(saved_links) != edge_multiset(links):raise ValueError('Group edge/rule/score replay differs')
    if json.loads((directory/'summary.json').read_text(encoding='utf8')) != dict(summary,run_id=directory.name):
        raise ValueError('Summary replay differs')
    receipt = dict(verified=True,run=directory.name,snapshots=len(features),proofs=len(proofs),
        edges=len(links),undirected_graph_order_normalized=True,
        source_manifest_sha256=source.collect.cafe.sha(directory/'manifest.json'),
        verifier_sha256=source.collect.cafe.sha(Path(__file__)),no_network_or_model_scoring=True)
    source.collect.audit.c.write_json(source.OUT/'verification.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=='__main__':
    verify(source.OUT/json.loads((source.OUT/'latest.json').read_text(encoding='utf8'))['run'])
