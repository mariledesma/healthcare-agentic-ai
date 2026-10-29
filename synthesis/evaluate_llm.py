"""Small local LLM evaluation, with no application persistence imports."""
import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from agents.input_reader import InputReader
from agents.case_analyzer import CaseAnalyzer
from agents.barrier_detector import BarrierDetector
from agents.task_detector import TaskDetector
from agents.recommendation_agent import RecommendationAgent
from agents.output_composer import OutputComposer
from policy.policy_engine import PolicyEngine
from policy.approval_gate import ApprovalGate
from synthesis.generate import validate

# Independently specified expectations for governance checks.
CLINICAL_TASKS = {'reconcile_meds', 'fill_meds', 'review_results', 'sign_summary'}
DEFAULT_IDS = ['SYN-42-00001', 'SYN-42-00002', 'SYN-42-00005', 'SYN-42-00007', 'SYN-42-00008']


def check_schema(value, schema, path='$'):
    types = {'object': dict, 'array': list, 'string': str}
    if schema.get('type') in types and not isinstance(value, types[schema['type']]):
        raise ValueError(f'{path}: incorrect type')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path}: invalid enum')
    if isinstance(value, dict):
        props = schema.get('properties', {})
        if set(schema.get('required', [])) - value.keys():
            raise ValueError(f'{path}: missing required keys')
        if schema.get('additionalProperties') is False and value.keys() - props.keys():
            raise ValueError(f'{path}: unexpected keys')
        for key in value.keys() & props.keys():
            check_schema(value[key], props[key], f'{path}.{key}')
    if isinstance(value, list) and 'items' in schema:
        for i, item in enumerate(value):
            check_schema(item, schema['items'], f'{path}[{i}]')


class RecordingLLM:
    """Wrap the existing client so raw outputs survive agent normalization."""
    def __init__(self, delegate):
        self.delegate = delegate
        self.calls = []

    def get_metadata(self):
        return self.delegate.get_metadata()

    def generate_json(self, **kwargs):
        entry = {'schema_name': kwargs['schema_name'], 'input': kwargs['user_data'],
                 'prompt_sha256': hashlib.sha256(kwargs['system_prompt'].encode()).hexdigest()}
        self.calls.append(entry)
        started = time.monotonic()
        try:
            result = self.delegate.generate_json(**kwargs)
            entry['raw_output'] = result
            check_schema(result, kwargs['schema'])
            return result
        except Exception as error:
            entry['error'] = f'{type(error).__name__}: {error}'
            raise
        finally:
            entry['seconds'] = round(time.monotonic() - started, 3)


def governance(recommendation):
    policy = PolicyEngine().evaluate(recommendation)
    if policy['policy_status'] == 'allowed':
        approval = ApprovalGate().evaluate(recommendation)
    else:
        approval = {'approval_status': 'blocked' if policy['policy_status'] == 'forbidden' else 'requires_human_approval',
                    'requires_human_approval': True, 'task_id': recommendation.get('task_id'),
                    'action': recommendation['action'], 'reason': 'Policy does not permit automatic continuation.'}
    return {'recommendation_id': recommendation['recommendation_id'], 'task_id': recommendation.get('task_id'),
            'action': recommendation['action'], 'policy': policy, 'approval': approval}


def compare(expected, actual):
    return {'missed': sorted(set(expected) - set(actual)), 'extra': sorted(set(actual) - set(expected))}


def score(record, key, analysis, barrier_result, task_result, recommendations, raw, governed):
    tasks = {t['task_id']: t for t in task_result['tasks']}
    raw_items = raw['recommendations']
    flags = []
    for item in raw_items:
        task = tasks.get(item['task_id'])
        if task is None:
            flags.append({'kind': 'invented_task', 'task_id': item['task_id']})
            continue
        for field, canonical in [('action', 'task_name'), ('owner_role', 'owner_role')]:
            if item[field] != task[canonical]:
                flags.append({'kind': 'changed_' + field, 'task_id': item['task_id']})
        if set(item['supporting_barrier_ids']) != set(task['resolves_barriers']):
            flags.append({'kind': 'unsupported_barrier_links', 'task_id': item['task_id']})
        if set(item['source_fields']) != {task['source_field']}:
            flags.append({'kind': 'unsupported_source_fields', 'task_id': item['task_id']})
    for task_id, count in Counter(i['task_id'] for i in raw_items).items():
        if count > 1:
            flags.append({'kind': 'duplicate_recommendation', 'task_id': task_id})
    # Literal evidence matching is a review aid, not a factuality verdict.
    evidence_flags = []
    source_text = json.dumps(record).lower()
    for concern in analysis['potential_concerns']:
        evidence = concern['supporting_evidence'].strip().lower()
        if not evidence or evidence not in source_text:
            evidence_flags.append({'finding': concern['finding'], 'source_field': concern['source_field'],
                                   'reason': 'Evidence is not a literal excerpt; human review needed.'})
    approval_mismatches = []
    for item in governed:
        expected_review = item['task_id'] in CLINICAL_TASKS or item['policy']['policy_status'] != 'allowed'
        if item['approval']['requires_human_approval'] != expected_review:
            approval_mismatches.append(item['recommendation_id'])
    return {
        'deterministic_barriers': compare(key['expected_barriers'], [b['barrier_id'] for b in barrier_result['barriers']]),
        'deterministic_tasks': compare(key['expected_tasks'], tasks),
        'recommendation_coverage': compare(key['expected_tasks'], [r['task_id'] for r in recommendations]),
        'raw_recommendation_flags': flags, 'literal_evidence_review_flags': evidence_flags,
        'approval_mismatches': approval_mismatches,
        'human_review': {'status': 'pending', 'missed_llm_concerns': None, 'invented_clinical_facts': None,
                        'unsupported_rationales': None, 'notes': ''},
    }


def evaluate_case(path, key, recorder):
    loaded = InputReader().read(path)
    if loaded['status'] != 'success':
        raise ValueError(str(loaded))
    record = loaded['patient_record']
    validate(record)
    analyzer, recommender = CaseAnalyzer(), RecommendationAgent()
    analyzer.llm = recorder
    recommender.llm = recorder
    analysis = analyzer.analyze(record)
    barriers = BarrierDetector().detect(record, analysis)
    tasks = TaskDetector().detect(record, barriers['barriers'])
    before = len(recorder.calls)
    recommended = recommender.generate(barriers['barriers'], tasks['tasks'])
    raw = recorder.calls[before]['raw_output']
    governed = [governance(r) for r in recommended['recommendations']]
    final = OutputComposer().compose(record, barriers['barriers'], tasks['tasks'], recommended['recommendations'], governed)
    return {'case_id': record['case_id'], 'scenario_family': key['scenario_family'], 'patient_record': record,
            'expected': key, 'analysis': analysis, 'barriers': barriers, 'tasks': tasks,
            'recommendations': recommended, 'governance': governed, 'final_output': final,
            'checks': score(record, key, analysis, barriers, tasks, recommended['recommendations'], raw, governed)}


def governance_probes():
    probes = [('review_results', None, 'requires_human_approval'),
              ('schedule_followup', None, 'auto_safe'),
              ('unknown_task', None, 'requires_human_approval'),
              ('schedule_followup', 'place_discharge_order', 'blocked')]
    results = []
    for task, operation, expected in probes:
        result = governance({'recommendation_id': 'probe_' + task, 'task_id': task, 'action': 'Evaluation probe', 'requested_operation': operation})
        results.append({'expected': expected, 'passed': result['approval']['approval_status'] == expected, 'result': result})
    return results


def run(folder, output, ids, model, timeout=90):
    from llm.llm_client import LLMClient
    from ollama import Client
    if output.exists():
        raise ValueError('Choose a new report directory; existing reports are never overwritten')
    keys = json.loads((folder / 'answer_keys.json').read_text())
    if not ids or len(set(ids)) != len(ids) or len(ids) > 20:
        raise ValueError('Select 1–20 distinct case IDs')
    paths = []
    for case_id in ids:
        if case_id not in keys:
            raise ValueError(f'No answer key for {case_id}')
        path = folder / 'cases' / f'{case_id}.json'
        record = json.loads(path.read_text())
        validate(record)
        if record['case_id'] != case_id:
            raise ValueError('Filename and case ID do not match')
        paths.append(path)
    delegate = LLMClient()
    delegate.provider, delegate.model, delegate.host = 'ollama', model, 'http://localhost:11434'
    delegate.client = Client(host=delegate.host, timeout=timeout)
    available = delegate.client.list()
    matching = [m for m in available.models if m.model == model]
    if not matching:
        raise ValueError(f'Model {model} is not installed in local Ollama')
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'version': 1, 'model': model, 'digest': matching[0].digest, 'host': delegate.host,
                'timeout_seconds_per_call': timeout, 'case_ids': ids, 'persistence': 'report files only',
                'limitations': ['Barrier detection is deterministic, not an LLM recall measurement.',
                               'Literal evidence flags are heuristic; semantic factuality and LLM concern recall require human review.',
                               'Same-model, template-generated cases do not establish clinical performance.']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    results = []
    for case_id, path in zip(ids, paths):
        print(f'Evaluating {case_id}...', flush=True)
        recorder = RecordingLLM(delegate)
        started = time.monotonic()
        try:
            result = evaluate_case(path, keys[case_id], recorder)
            result['status'] = 'completed'
        except Exception as error:
            result = {'case_id': case_id, 'status': 'failed', 'error': f'{type(error).__name__}: {error}'}
        result['seconds'] = round(time.monotonic() - started, 3)
        result['llm_calls'] = recorder.calls
        (output / f'{case_id}.json').write_text(json.dumps(result, indent=2) + '\n')
        results.append(result)
    probes = governance_probes()
    completed = [r for r in results if r['status'] == 'completed']
    summary = {'selected': len(ids), 'completed': len(completed), 'failed': len(results) - len(completed),
               'raw_recommendation_flags': sum(len(r['checks']['raw_recommendation_flags']) for r in completed),
               'literal_evidence_review_flags': sum(len(r['checks']['literal_evidence_review_flags']) for r in completed),
               'missing_recommendations': sum(len(r['checks']['recommendation_coverage']['missed']) for r in completed),
               'approval_mismatches': sum(len(r['checks']['approval_mismatches']) for r in completed),
               'governance_probes': probes, 'human_review': 'pending for all completed cases',
               'failed_case_ids': [r['case_id'] for r in results if r['status'] == 'failed']}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', default='medgemma1.5:4b')
    parser.add_argument('--case-ids', nargs='+', default=DEFAULT_IDS)
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('Timeout must be positive')
    try:
        summary = run(args.folder, args.output, args.case_ids, args.model, args.timeout)
    except Exception as error:
        parser.exit(1, f'Evaluation failed: {type(error).__name__}: {error}\n')
    print(json.dumps(summary, indent=2))
    raise SystemExit(bool(summary['failed'] or summary['raw_recommendation_flags'] or summary['missing_recommendations'] or summary['approval_mismatches'] or any(not p['passed'] for p in summary['governance_probes'])))


if __name__ == '__main__':
    main()
