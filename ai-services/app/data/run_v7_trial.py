"""Operational entry point: member-level evaluation guard and safe pointer repair."""
import argparse
import json
from pathlib import Path
import train_v7_trial as archived


def assert_fresh(lock,all_rows,receipts):
    members=lock['members'];ids={r['record_key'] for r in members};groups={r['property_candidate_group'] for r in members}
    current={r['record_key']:r['property_candidate_group'] for r in all_rows}
    for receipt in receipts:
        used={r['record_key'] if isinstance(r,dict) else r for r in receipt['members']}
        if used-current.keys():raise ValueError('Grouping view is missing previously evaluated IDs')
        used_groups={current[k] for k in used}|set(receipt.get('property_groups',[]))
        if ids&used or groups&used_groups:
            raise ValueError('Cohort includes previously evaluated/reserved records or property groups; verify the saved trial instead')


def restore_prepared_pointer():
    prep=archived.preparation;cohort=archived.latest(prep.cohort.OUT)
    wanted=(cohort/'manifest.json').relative_to(prep.BASE.parents[2]).as_posix()
    matches=[]
    for manifest in (prep.OUT/'runs').glob('*/manifest.json'):
        folder=manifest.parent
        if folder.name.startswith('.building_'):continue
        saved=json.loads(manifest.read_text(encoding='utf8'))
        if saved['input_sha256'].get(wanted)!=archived.data.sha(cohort/'manifest.json'):continue
        if json.loads((folder/'protocol.json').read_text(encoding='utf8'))!=prep.PROTOCOL:continue
        if any(archived.data.sha(prep.BASE.parents[2]/p)!=h for p,h in saved['input_sha256'].items()):continue
        if any(archived.data.sha(folder/p)!=h for p,h in saved['output_sha256'].items()):continue
        matches.append(folder)
    if len(matches)!=1:raise ValueError('Expected exactly one complete preparation matching current inputs')
    prep.cohort.collector.source.atomic(prep.OUT/'latest.json',dict(run='runs/'+matches[0].name))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    if args.verify:
        import verify_v7_trial
        verify_v7_trial.verify();return
    cohort=archived.latest(archived.preparation.cohort.OUT)
    lock=json.loads((cohort/'cohort_lock.json').read_text(encoding='utf8'))
    rows=archived.data.read(cohort/'all_decisions.csv')
    receipts=[json.loads(p.read_text(encoding='utf8')) for p in archived.LEDGER.glob('*.json')]
    if not args.prepare:assert_fresh(lock,rows,receipts)
    archived.preparation.main();restore_prepared_pointer()
    if args.prepare:return
    archived.main()


if __name__=='__main__':main()
