"""Compare saved LLM runs without making model calls or changing reports."""
import argparse
import json
from pathlib import Path


# An explicit development rubric; used only after inference, never in prompts.
CONCERN_SOURCES = {
    'ready': set(), 'followup': {'followup_status'},
    'medication_review': {'medication_reconciliation_status'},
    'medication_access': {'medication_availability'},
    'pending_results': {'pending_labs'},
    'transport_timing': {'transport_time', 'planned_discharge_window'},
}


def concern_source_coverage(family, concerns):
    expected = CONCERN_SOURCES.get(family)
    if expected is None:
        return None
    actual = {field.strip() for concern in concerns for field in concern['source_field'].split(' + ')}
    return {'missing_source_fields': sorted(expected - actual),
            'unexpected_source_fields': sorted(actual - expected),
            'scope': 'Source-field coverage only; does not validate concern meaning.'}


def concern_evidence(record, concerns):
    """Check the requested exact JSON evidence format, not clinical truth."""
    issues = []
    for index, concern in enumerate(concerns):
        try:
            evidence = json.loads(concern['supporting_evidence'])
        except (ValueError, TypeError):
            issues.append({'concern': index, 'reason': 'Evidence is not a JSON object with field values.'})
            continue
        fields = [field.strip() for field in concern['source_field'].split(' + ')]
        if not isinstance(evidence, dict) or not evidence or set(evidence) != set(fields):
            issues.append({'concern': index, 'reason': 'Evidence keys do not match cited fields.'})
        elif any(field not in record or evidence[field] != record[field] for field in fields):
            issues.append({'concern': index, 'reason': 'Evidence values differ from source record.'})
        if concern['finding'].strip() in fields:
            issues.append({'concern': index, 'reason': 'Finding is only a field name.'})
    return issues


def load_run(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    return manifest, {case_id: (json.loads((folder / f'{case_id}.json').read_text())
                               if (folder / f'{case_id}.json').exists()
                               else {'case_id': case_id, 'status': 'not_completed'})
                      for case_id in manifest['case_ids']}


def compare_runs(baseline, candidate):
    old_manifest, old = load_run(baseline)
    new_manifest, new = load_run(candidate)
    if old_manifest['model'] != new_manifest['model'] or old_manifest['digest'] != new_manifest['digest']:
        raise ValueError('Model name or digest differs; this is not a prompt-only comparison')
    common = sorted(old.keys() & new.keys())
    if not common:
        raise ValueError('No shared cases')
    rows = []
    for case_id in common:
        a, b = old[case_id], new[case_id]
        row = {'case_id': case_id, 'before_status': a['status'], 'after_status': b['status']}
        if a['status'] == b['status'] == 'completed':
            if a['patient_record'] != b['patient_record']:
                raise ValueError(f'Input changed for {case_id}')
            for label, result in [('before', a), ('after', b)]:
                concerns = result['analysis']['potential_concerns']
                row[label] = {'concerns': concerns, 'information_gaps': result['analysis']['information_gaps'],
                              'evidence_format_issues': concern_evidence(result['patient_record'], concerns),
                              'concern_source_coverage': concern_source_coverage(result['scenario_family'], concerns),
                              'seconds': result['seconds'],
                              'prompt_sha256': result['llm_calls'][0]['prompt_sha256'],
                              'recommendation_coverage': result['checks']['recommendation_coverage'],
                              'raw_recommendation_flags': result['checks']['raw_recommendation_flags'],
                              'approval_mismatches': result['checks']['approval_mismatches']}
        rows.append(row)
    extra_ids = sorted(new.keys() - old.keys())
    return {'model': new_manifest['model'], 'digest': new_manifest['digest'], 'shared_cases': rows,
            'additional_candidate_cases': extra_ids, 'baseline_only_cases': sorted(old.keys() - new.keys()),
            'limitations': ['Evidence-format checks applied equally to saved outputs; baseline was not instructed to use JSON evidence.',
                           'Exact evidence values do not establish that a concern is valid or complete.',
                           'This is a prompt-development comparison on reused synthetic cases, not independent clinical validation.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare_runs(args.baseline, args.candidate), indent=2))


if __name__ == '__main__':
    main()
