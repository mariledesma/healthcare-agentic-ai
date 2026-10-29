"""Generate controlled cases without invoking the application or database."""
import argparse
import copy
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Scenario expectations are authored here, independently of the production detectors.
SCENARIOS = [
    ('ready', {}, [], []),
    ('followup', {'followup_status': 'not_scheduled'}, ['followup_missing'], ['schedule_followup']),
    ('transport', {'transport_status': 'not_arranged', 'transport_time': None}, ['transport_missing'], ['arrange_transport']),
    ('transport_timing', {'transport_time': '19:00'}, ['transport_timing'], ['arrange_transport']),
    ('medication_review', {'medication_reconciliation_status': 'incomplete'}, ['med_reconciliation_missing'], ['reconcile_meds']),
    ('medication_education', {'medication_education_status': 'incomplete'}, ['med_education_missing'], ['teach_meds']),
    ('medication_access', {'medication_availability': 'not_available'}, ['med_unavailable'], ['fill_meds']),
    ('pending_results', {'pending_labs': ['Repeat laboratory panel']}, ['pending_results'], ['review_results']),
    ('patient_education', {'patient_education_status': 'incomplete'}, ['patient_education_missing'], ['teach_condition']),
    ('diet_education', {'diet_education_status': 'incomplete'}, ['diet_education_missing'], ['teach_diet']),
    ('mobility_education', {'mobility_device_education_status': 'incomplete'}, ['mobility_education_missing'], ['teach_mobility_device']),
    ('device_education', {'medical_device_education_status': 'incomplete'}, ['device_education_missing'], ['teach_device']),
    ('caregiver', {'caregiver_status': 'unavailable'}, ['caregiver_missing'], ['confirm_caregiver']),
    ('therapy', {'outpatient_therapy_status': 'not_arranged'}, ['therapy_missing'], ['arrange_therapy']),
    ('pcp', {'pcp_notification_status': 'incomplete'}, ['pcp_notification_missing'], ['notify_pcp']),
    ('finances', {'financial_status': 'barrier'}, ['financial_barrier'], ['address_finances']),
    ('home_safety', {'home_safety_status': 'needs_assessment'}, ['home_safety_issue'], ['check_home_safety']),
    ('case_manager', {'case_manager_status': 'unavailable'}, ['case_manager_missing'], []),
    ('paperwork', {'discharge_summary_status': 'unsigned'}, ['paperwork_pending'], ['sign_summary']),
    ('mobility', {'physical_function': 'needs_assistance'}, ['physical_support_needed'], ['assess_function']),
    ('multiple', {'followup_status': 'not_scheduled', 'transport_status': 'not_arranged', 'transport_time': None, 'medication_availability': 'not_available'}, ['followup_missing', 'transport_missing', 'med_unavailable'], ['schedule_followup', 'arrange_transport', 'fill_meds']),
]
BASE = dict(
    pending_labs=[], pending_imaging=[], pending_consult=[], medical_stability_status='stable',
    medication_reconciliation_status='complete', medication_education_status='complete',
    medication_availability='available', patient_education_status='complete', diet_education_status='not_required',
    mobility_device_education_status='not_required', medical_device_education_status='not_required',
    followup_status='scheduled', caregiver_status='available', transport_status='arranged',
    transport_time='14:00', planned_discharge_window='afternoon', financial_status='no_concern',
    case_manager_status='available', home_safety_status='safe', outpatient_therapy_status='not_required',
    pcp_notification_status='complete', physical_function='independent', discharge_summary_status='signed',
)
ALLOWED = {key: {str(value)} for key, value in BASE.items() if isinstance(value, str)}
for _, changes, _, _ in SCENARIOS:
    for key, value in changes.items():
        if key in ALLOWED:
            ALLOWED[key].add(value)


def validate(record):
    for key in ('case_id', 'condition', 'discharge_summary'):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f'Invalid {key}')
    for key in ('diagnoses', 'pending_labs', 'pending_imaging', 'pending_consult'):
        if not isinstance(record.get(key), list) or any(not isinstance(x, str) for x in record[key]):
            raise ValueError(f'Invalid {key}')
    if not record['diagnoses'] or not isinstance(record.get('medications'), list):
        raise ValueError('Missing clinical fixture')
    for medication in record['medications']:
        if not isinstance(medication, dict) or any(not isinstance(medication.get(k), str) or not medication[k] for k in ('name', 'dose', 'frequency')):
            raise ValueError('Invalid medication')
    if not isinstance(record.get('labs'), dict) or any(not isinstance(v, str) for v in record['labs'].values()):
        raise ValueError('Invalid labs')
    for key, values in ALLOWED.items():
        if record.get(key) not in values:
            raise ValueError(f'Invalid {key}')
    if record['transport_status'] == 'not_arranged' and record['transport_time'] is not None:
        raise ValueError('Unarranged transport must have no time')
    if record['transport_status'] == 'arranged' and record['transport_time'] not in ('14:00', '19:00'):
        raise ValueError('Invalid transport time')
    notes = record.get('free_text_notes')
    if not isinstance(notes, dict) or not notes or any(not isinstance(v, str) or not v.strip() for v in notes.values()):
        raise ValueError('Invalid notes')
    if any(k in record for k in ('expected_barriers', 'expected_tasks', 'distractors')):
        raise ValueError('Evaluation metadata leaked into patient record')


def narrative(record, rng, model=None):
    # Exact source facts remain in every accepted narrative. The optional model
    # may only choose among prevalidated introductions, never change clinical facts.
    intros = ['Synthetic discharge coordination snapshot.', 'Fictional discharge planning review.', 'Synthetic case for discharge workflow testing.']
    intro = rng.choice(intros)
    if model:
        from ollama import Client
        client = Client(host='http://localhost:11434', timeout=60)
        schema = {'type': 'object', 'properties': {'introduction': {'type': 'string', 'enum': intros}}, 'required': ['introduction'], 'additionalProperties': False}
        last_error = None
        for _ in range(2):
            try:
                response = client.chat(model=model, messages=[{'role': 'user', 'content': 'Choose one introduction for a fictional discharge workflow test. Return JSON. Choices: ' + json.dumps(intros)}], format=schema, options={'temperature': 0})
                value = json.loads(response.message.content)
                if set(value) != {'introduction'} or value['introduction'] not in intros:
                    raise ValueError('Unsupported narrative output')
                intro = value['introduction']
                break
            except Exception as error:
                last_error = error
        else:
            raise ValueError(f'Narrative generation failed after two attempts: {last_error}')
    facts = {key: record[key] for key in ('condition', 'diagnoses', 'medications', 'labs', *BASE)}
    record['discharge_summary'] = intro + ' Medical stability: ' + record['medical_stability_status'] + '. Discharge readiness requires separate workflow review.'
    record['free_text_notes'] = {'case_manager_note': 'Source facts: ' + json.dumps(facts, sort_keys=True)}


def generate(output, count=100, seed=42, model=None):
    if count < 1:
        raise ValueError('Count must be positive')
    if output.exists():
        raise ValueError('Output directory already exists; choose a new directory')
    templates = []
    for name in ('case_001_hf.json', 'case_002_copd.json', 'case_003_pneumonia.json', 'case_004_ortho.json', 'case_005_stroke.json'):
        path = ROOT / 'data/synthetic' / name
        raw = path.read_bytes()
        templates.append((name, json.loads(raw), hashlib.sha256(raw).hexdigest()))
    rng = random.Random(seed)
    planned = []
    seen = set()
    for i in range(count):
        name, template, digest = templates[(i // len(SCENARIOS)) % len(templates)]
        family, changes, barriers, tasks = SCENARIOS[i % len(SCENARIOS)]
        record = {k: copy.deepcopy(template[k]) for k in ('condition', 'diagnoses', 'medications', 'labs')}
        record.update(copy.deepcopy(BASE))
        record.update(copy.deepcopy(changes))
        record['case_id'] = f'SYN-{seed}-{i + 1:05d}'
        narrative(record, rng, model)
        validate(record)
        fingerprint = hashlib.sha256(json.dumps({k: v for k, v in record.items() if k not in ('case_id', 'discharge_summary', 'free_text_notes')}, sort_keys=True).encode()).hexdigest()
        duplicate = fingerprint in seen
        seen.add(fingerprint)
        planned.append((record, {'scenario_family': family, 'template': name, 'template_sha256': digest, 'expected_barriers': barriers, 'expected_tasks': tasks, 'split_group': f'{name}:{family}', 'structured_duplicate': duplicate}))
    # Prepare everything before writing; never overwrite existing output.
    output.mkdir(parents=True, exist_ok=False)
    (output / 'cases').mkdir()
    answers = {}
    for record, answer in planned:
        (output / 'cases' / f"{record['case_id']}.json").write_text(json.dumps(record, indent=2) + '\n')
        answers[record['case_id']] = answer
    (output / 'answer_keys.json').write_text(json.dumps(answers, indent=2) + '\n')
    manifest = {'schema_version': 1, 'generator_version': '1.0', 'seed': seed, 'count': count, 'mode': 'restricted_medgemma_wording' if model else 'template', 'model': model, 'clinical_review': 'required; fixtures are not clinically validated', 'unique_structured_cases': len(seen), 'scenario_families': sorted({a['scenario_family'] for _, a in planned}), 'limitations': ['No learned population distribution', 'No missing-information or contradiction cases in v1', 'MedGemma selects a validated introduction only; clinical facts are rendered deterministically']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--model', help='Optional installed local Ollama model for restricted narrative wording')
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.output, args.count, args.seed, args.model), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f'Generation failed: {error}\n')


if __name__ == '__main__':
    main()
