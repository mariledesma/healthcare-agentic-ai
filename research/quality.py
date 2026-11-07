"""Conservative source-quality checks, separate from clinical barrier labels."""
from datetime import date
import re

STATUSES = {
    'medication_reconciliation_status': {'complete', 'incomplete', 'pending', 'not_complete'},
    'medication_education_status': {'complete', 'incomplete', 'pending', 'not_complete'},
    'followup_status': {'scheduled', 'not_scheduled', 'pending'},
    'transport_status': {'arranged', 'not_arranged', 'pending'},
    'medical_stability_status': {'stable', 'unstable', 'not_stable'},
}


def assess(record):
    issues = []
    def add(field, kind, message):
        issues.append({'issue_id': f'{kind}:{field}', 'field': field, 'kind': kind,
                       'message': message, 'source_value': record.get(field), 'requires_review': True})
    for field, values in STATUSES.items():
        value = record.get(field)
        if value is None or value == '':
            add(field, 'missing', 'Required workflow status is absent; do not infer completion.')
        elif not isinstance(value, str) or value not in values:
            add(field, 'unrecognized', 'Status is outside the current research vocabulary; request clarification.')
    for field in ('pending_labs', 'pending_imaging', 'pending_consult'):
        if field in record and (not isinstance(record[field], list) or any(not isinstance(x, str) or not x.strip() for x in record[field])):
            add(field, 'malformed', 'Pending items must be a list of nonempty item names.')
    if record.get('transport_status') == 'arranged':
        if not isinstance(record.get('transport_time'), str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', record['transport_time']):
            add('transport_time', 'invalid_time', 'An arranged ride needs a valid HH:MM time.')
        if record.get('planned_discharge_window') not in ('morning', 'afternoon', 'evening'):
            add('planned_discharge_window', 'unrecognized', 'Discharge window is absent or unrecognized.')
    for field in ('planned_discharge_date', 'transport_date'):
        if field in record:
            try:
                value = record[field]
                if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    raise ValueError()
                date.fromisoformat(value)
            except ValueError:
                add(field, 'invalid_date', 'Date must be a valid ISO YYYY-MM-DD value.')
    # Explicit alternate structured observations are preserved, never silently merged.
    observations = record.get('source_observations', [])
    if not isinstance(observations, list):
        add('source_observations', 'malformed', 'Alternate observations must be a list.')
    else:
        for index, item in enumerate(observations):
            if not isinstance(item, dict) or not isinstance(item.get('field'), str) or 'value' not in item:
                add('source_observations', 'malformed', f'Observation {index} is malformed.')
            elif item['field'] in record and item['value'] != record[item['field']]:
                issues.append({'issue_id': f'conflict:{index}:{item["field"]}', 'field': item['field'],
                               'kind': 'conflicting_sources', 'message': 'Sources disagree; a reviewer must reconcile them.',
                               'source_value': record[item['field']], 'alternate_observation': item,
                               'requires_review': True})
    return {'status': 'requires_clarification' if issues else 'no_issues_detected',
            'issues': issues, 'requires_review': bool(issues),
            'scope': 'Vocabulary, format and explicit structured conflicts only; narrative contradictions are not comprehensively detected.'}
