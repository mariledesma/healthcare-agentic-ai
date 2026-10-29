"""Provisional challenge gap audit; no LLM or production persistence calls."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from agents.input_reader import InputReader
from agents.barrier_detector import BarrierDetector
from agents.task_detector import TaskDetector
from policy.policy_engine import PolicyEngine
from policy.approval_gate import ApprovalGate

FORBIDDEN_INPUT_KEYS = {'expected_barriers', 'expected_tasks', 'rationale', 'review_status',
                        'scenario_family', 'proposed_taxonomy_ids', 'expected_information_gaps',
                        'required_review_categories', 'expected_human_approval_tasks'}
NARRATIVE_FAMILIES = {'negation', 'resolved_problem', 'historical_context', 'narrative_only_transport',
                      'narrative_only_followup', 'contradictory_caregiver', 'contradictory_followup',
                      'instruction_in_note', 'resolved_result'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_no_labels(value):
    if isinstance(value, dict):
        if FORBIDDEN_INPUT_KEYS & value.keys():
            raise ValueError('Evaluation metadata in patient input')
        for item in value.values():
            check_no_labels(item)
    elif isinstance(value, list):
        for item in value:
            check_no_labels(item)


def load_challenge(folder):
    manifest = read_json(folder / 'manifest.json')
    if manifest.get('frozen'):
        from synthesis.freeze_challenge import verify_snapshot
        verify_snapshot(folder)
    if hash_file(folder / 'answer_keys.json') != manifest['answer_keys_sha256']:
        raise ValueError('Answer key changed; create an adjudicated version instead of changing this baseline')
    answers = read_json(folder / 'answer_keys.json')
    decisions = read_json(folder / 'review_decisions.json')
    if set(answers) != set(manifest['case_sha256']) or set(answers) != set(decisions):
        raise ValueError('Manifest, answers, and review ledger IDs differ')
    if set(p.stem for p in (folder / 'cases').glob('*.json')) != set(answers):
        raise ValueError('Missing or extra patient files')
    if manifest['case_count'] != len(answers):
        raise ValueError('Incorrect case count')
    records = {}
    for case_id, key in answers.items():
        if not re.fullmatch(r'CHAL-\d{3}', case_id):
            raise ValueError('Invalid case ID')
        path = folder / 'cases' / f'{case_id}.json'
        if hash_file(path) != manifest['case_sha256'][case_id]:
            raise ValueError(f'Patient input changed: {case_id}')
        record = read_json(path)
        check_no_labels(record)
        if record.get('case_id') != case_id:
            raise ValueError('Patient ID mismatch')
        for field in ('expected_barriers', 'expected_tasks', 'expected_information_gaps',
                      'expected_human_approval_tasks', 'required_review_categories', 'proposed_taxonomy_ids'):
            values = key[field]
            if not isinstance(values, list) or any(not isinstance(x, str) for x in values) or len(values) != len(set(values)):
                raise ValueError(f'Invalid answer values: {case_id}/{field}')
        if not set(key['expected_human_approval_tasks']) <= set(key['expected_tasks']):
            raise ValueError('Approval expectation refers to a task outside the proposed answer')
        for field, value in key['evidence'].items():
            actual = record
            for part in field.split('.'):
                if not isinstance(actual, dict) or part not in actual:
                    raise ValueError(f'Answer cites nonexistent field: {case_id}/{field}')
                actual = actual[part]
            if actual != value:
                raise ValueError(f'Answer evidence differs from patient source: {case_id}/{field}')
        decision = decisions[case_id]
        if decision['decision'] not in ('pending', 'approved', 'revise', 'rejected'):
            raise ValueError('Unknown review decision')
        if decision['decision'] != 'pending' and (not decision.get('reviewer') or not decision.get('reviewed_at')):
            raise ValueError('Completed decisions need an actual reviewer and review date')
        records[case_id] = record
    return manifest, records, answers, decisions


def compare(expected, actual):
    return {'missing': sorted(set(expected) - set(actual)), 'unexpected': sorted(set(actual) - set(expected))}


def evaluate(folder):
    manifest, records, answers, decisions = load_challenge(folder)
    approved = bool(manifest.get('approved_for_workflow_regression')) and all(r['decision'] == 'approved' for r in decisions.values())
    label_status = 'user-approved workflow expectations; not clinical validation' if approved else 'provisional; domain review pending'
    results = []
    for case_id in sorted(records):
        key = answers[case_id]
        loaded = InputReader().read(folder / 'cases' / f'{case_id}.json')
        if loaded['status'] != 'success':
            results.append({'case_id': case_id, 'title': key['title'], 'input_error': loaded,
                            'id_match': False, 'unassessed_requirements': ['Pipeline input rejected']})
            continue
        record = loaded['patient_record']
        barriers = BarrierDetector().detect(record)['barriers']
        tasks = TaskDetector().detect(record, barriers)['tasks']
        barrier_diff = compare(key['expected_barriers'], [b['barrier_id'] for b in barriers])
        task_diff = compare(key['expected_tasks'], [t['task_id'] for t in tasks])
        approvals = []
        for task_id in key['expected_human_approval_tasks']:
            task = next((t for t in tasks if t['task_id'] == task_id), None)
            if task is None:
                approvals.append({'task_id': task_id, 'status': 'unassessed_missing_task'})
                continue
            recommendation = {'task_id': task_id, 'action': task['task_name']}
            policy = PolicyEngine().evaluate(recommendation)
            approval = ApprovalGate().evaluate(recommendation) if policy['policy_status'] == 'allowed' else {'requires_human_approval': True}
            approvals.append({'task_id': task_id, 'status': 'human_review_required' if approval['requires_human_approval'] else 'approval_mismatch'})
        unassessed = []
        if key['scenario_family'] in NARRATIVE_FAMILIES:
            unassessed.append('Narrative meaning/negation/chronology: not assessed by rule-only runner')
        if key['expected_information_gaps'] or any(x in key['required_review_categories'] for x in ('contradiction', 'invalid_source_value', 'missing_information')):
            unassessed.append('Information-gap/contradiction handling: requires LLM or human review; not assessed here')
        result = {'case_id': case_id, 'title': key['title'], 'scenario_family': key['scenario_family'],
                  'labels': label_status,
                  'review_decision': decisions[case_id]['decision'], 'barriers': barrier_diff, 'tasks': task_diff,
                  'actual_barriers': barriers, 'actual_tasks': tasks, 'approval_checks': approvals,
                  'expected_information_gaps': key['expected_information_gaps'],
                  'required_review_categories': key['required_review_categories'],
                  'unassessed_requirements': unassessed,
                  'id_match': not any(barrier_diff.values()) and not any(task_diff.values())}
        results.append(result)
    return {'dataset': manifest['dataset_id'], 'label_status': label_status,
            'implementation_sha256': {name: hash_file(Path(__file__).resolve().parents[1] / name)
                                      for name in ('agents/input_reader.py', 'agents/barrier_detector.py', 'agents/task_detector.py', 'policy/policy_engine.py', 'policy/approval_gate.py')},
            'cases': len(results), 'case_ids_with_mismatches': [r['case_id'] for r in results if not r['id_match']],
            'cases_with_unassessed_requirements': sum(bool(r['unassessed_requirements']) for r in results),
            'review_decisions': {status: sum(d['decision'] == status for d in decisions.values()) for status in ('pending','approved','revise','rejected')},
            'clinical_accuracy': 'not measured; workflow-only labels and unassessed capabilities' if approved else 'not measured; draft labels and unassessed capabilities',
            'results': results}


def save_report(report, output):
    if output.exists():
        raise ValueError('Choose a new report directory')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'baseline.json').write_text(json.dumps(report, indent=2) + '\n')
    approved = report['label_status'].startswith('user-approved')
    lines = ['# Approved workflow regression baseline' if approved else '# Provisional challenge baseline', '',
             f"{report['cases']} cases; {len(report['case_ids_with_mismatches'])} have barrier/task ID mismatches against the recorded expectations.", '',
             'Targets are user-approved workflow expectations. These counts are not clinical accuracy.' if approved else 'All targets are assistant-authored proposals awaiting domain adjudication. These counts are not clinical accuracy.', '',
             f"{report['cases_with_unassessed_requirements']} cases also contain requirements this rule-only runner does not assess.", '',
             '| Case | Recorded target comparison | Unassessed requirements |', '|---|---|---|']
    for row in report['results']:
        differences = []
        for kind in ('barriers','tasks'):
            if kind in row:
                for category, values in row[kind].items():
                    if values:
                        differences.append(f"{category} {kind}: {', '.join(values)}")
        if row.get('input_error'):
            differences.append('input rejected')
        lines.append(f"| {row['case_id']} — {row['title']} | {'; '.join(differences) or 'IDs match recorded targets'} | {'; '.join(row['unassessed_requirements']) or 'None listed by this narrow runner'} |")
    lines += ['', 'Read the case evidence and rationale in the review packet before accepting or rejecting any proposed answer.',
              'No LLM inference, PostgreSQL persistence, production audit writes, rule changes, or reviewer sign-off were performed.']
    (output / 'BASELINE_REVIEW.md').write_text('\n'.join(lines)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        if read_json(args.folder / 'manifest.json').get('frozen') and args.output.resolve().is_relative_to(args.folder.resolve()):
            raise ValueError('Reports must be saved outside the frozen snapshot')
        report = evaluate(args.folder)
        save_report(report, args.output)
    except Exception as error:
        parser.exit(1, f'Challenge baseline failed: {type(error).__name__}: {error}\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'results'}, indent=2))
    raise SystemExit(bool(report['case_ids_with_mismatches']))


if __name__ == '__main__':
    main()
