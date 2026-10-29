"""Evaluate the evidence-bound explainer locally, with report-only writes."""
import argparse
import hashlib
import json
from pathlib import Path

from agents.barrier_detector import BarrierDetector
from agents.input_reader import InputReader
from agents.readiness_explainer import ReadinessExplainer
from synthesis.evaluate_llm import RecordingLLM
from synthesis.generate import validate

DEFAULT_IDS = ['SYN-42-00001', 'SYN-42-00002', 'SYN-42-00005', 'SYN-42-00007',
               'SYN-42-00008', 'SYN-42-00004', 'SYN-42-00021', 'SYN-42-00022']


def run(folder, output, ids, model):
    from llm.llm_client import LLMClient
    from ollama import Client
    if output.exists():
        raise ValueError('Choose a new report directory')
    if not ids or len(set(ids)) != len(ids) or len(ids) > 20:
        raise ValueError('Choose 1–20 distinct case IDs')
    keys = json.loads((folder / 'answer_keys.json').read_text())
    prepared = []
    for case_id in ids:
        if case_id not in keys:
            raise ValueError(f'Unknown case: {case_id}')
        path = folder / 'cases' / f'{case_id}.json'
        loaded = InputReader().read(path)
        if loaded['status'] != 'success':
            raise ValueError(str(loaded))
        record = loaded['patient_record']
        validate(record)
        if record['case_id'] != case_id:
            raise ValueError('Case ID and filename differ')
        prepared.append((record, path))
    delegate = LLMClient()
    delegate.provider, delegate.model, delegate.host = 'ollama', model, 'http://localhost:11434'
    delegate.client = Client(host=delegate.host, timeout=90)
    matches = [m for m in delegate.client.list().models if m.model == model]
    if not matches:
        raise ValueError('Model is not installed locally')
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'model': model, 'digest': matches[0].digest, 'case_ids': ids,
                'scope': 'Grounded explainer only; standalone analyzer is not rerun or repaired.',
                'wording_mode': 'Detector-supplied choices with exact validation; not free clinical prose',
                'persistence': 'report files only'}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    reports = []
    for record, path in prepared:
        case_id = record['case_id']
        print(f'Evaluating grounded explanation: {case_id}', flush=True)
        barriers = BarrierDetector().detect(record)['barriers']
        recorder = RecordingLLM(delegate)
        result = ReadinessExplainer(recorder).explain(record, barriers)
        expected = set(keys[case_id]['expected_barriers'])
        detected = {b['barrier_id'] for b in barriers}
        report = {'case_id': case_id, 'patient_record': record,
                  'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'expected_barriers': sorted(expected), 'detected_barriers': sorted(detected),
                  'detector_matches_answer_key': expected == detected,
                  'readiness_explanation': result, 'llm_calls': recorder.calls}
        (output / f'{case_id}.json').write_text(json.dumps(report, indent=2) + '\n')
        reports.append(report)
    summary = {'selected': len(reports),
               'validated': sum(r['readiness_explanation']['status'] == 'validated' for r in reports),
               'not_needed': sum(r['readiness_explanation']['status'] == 'not_needed' for r in reports),
               'requires_review': sum(r['readiness_explanation']['requires_review'] for r in reports),
               'detector_mismatches': sum(not r['detector_matches_answer_key'] for r in reports),
               'clinical_validation': 'not established'}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--model', default='medgemma1.5:4b')
    parser.add_argument('--case-ids', nargs='+', default=DEFAULT_IDS)
    args = parser.parse_args()
    try:
        summary = run(args.folder, args.output, args.case_ids, args.model)
    except Exception as error:
        parser.exit(1, f'Evaluation failed: {type(error).__name__}: {error}\n')
    print(json.dumps(summary, indent=2))
    raise SystemExit(bool(summary['requires_review'] or summary['detector_mismatches']))


if __name__ == '__main__':
    main()
