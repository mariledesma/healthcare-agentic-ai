"""Offline detector evaluation: no LLM calls, audit logs, or database writes."""
import argparse
import json
from pathlib import Path

from agents.input_reader import InputReader
from agents.barrier_detector import BarrierDetector
from agents.task_detector import TaskDetector
from synthesis.generate import validate


def evaluate(folder):
    keys = json.loads((folder / 'answer_keys.json').read_text())
    rows = []
    totals = {kind: dict(tp=0, fp=0, fn=0) for kind in ('barriers', 'tasks')}
    for path in sorted((folder / 'cases').glob('*.json')):
        record = json.loads(path.read_text())
        validate(record)
        loaded = InputReader().read(path)
        if loaded['status'] != 'success':
            raise ValueError(f'{path.name}: {loaded}')
        record = loaded['patient_record']
        expected = keys[record['case_id']]
        barriers = BarrierDetector().detect(record)['barriers']
        tasks = TaskDetector().detect(record, barriers)['tasks']
        row = {'case_id': record['case_id'], 'scenario_family': expected['scenario_family']}
        for kind, actual in [('barriers', {x['barrier_id'] for x in barriers}), ('tasks', {x['task_id'] for x in tasks})]:
            wanted = set(expected['expected_' + kind])
            missed, extra = sorted(wanted - actual), sorted(actual - wanted)
            row[kind] = {'missed': missed, 'extra': extra}
            totals[kind]['tp'] += len(wanted & actual)
            totals[kind]['fp'] += len(extra)
            totals[kind]['fn'] += len(missed)
        rows.append(row)
    if not rows or len(rows) != len(keys) or len({r['case_id'] for r in rows}) != len(rows):
        raise ValueError('Missing cases, duplicate IDs, or unmatched answer keys')
    for scores in totals.values():
        tp, fp, fn = scores['tp'], scores['fp'], scores['fn']
        scores['precision'] = tp / (tp + fp) if tp + fp else None
        scores['recall'] = tp / (tp + fn) if tp + fn else None
    return {'cases': len(rows), 'totals': totals, 'failures': [r for r in rows if any(r[k]['missed'] or r[k]['extra'] for k in totals)], 'scope': 'Deterministic workflow regression only; does not evaluate MedGemma recommendations, governance, or clinical validity'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    report = evaluate(args.folder)
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report['failures']))


if __name__ == '__main__':
    main()
