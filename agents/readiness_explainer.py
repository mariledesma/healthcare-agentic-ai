"""Evidence-bound wording of deterministic findings, not clinical reasoning."""
import copy
import json

from pydantic import BaseModel, ConfigDict
from agents.barrier_detector import BarrierDetector


class ExplanationItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    barrier_id: str
    explanation: str
    evidence_json: str


class ExplanationResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    explanations: list[ExplanationItem]


def source_evidence(record, barriers):
    # Reconcile with the actual detector so stale, omitted, or fabricated
    # findings cannot become authoritative explanation inputs.
    canonical = BarrierDetector().detect(record)['barriers']
    if barriers != canonical:
        raise ValueError('Findings do not match the current detector and source record.')
    rows = []
    for barrier in barriers:
        fields = barrier['source_field'].split(' + ')
        if any(field not in record for field in fields):
            raise ValueError('A cited source field is missing from the record.')
        values = {field: copy.deepcopy(record[field]) for field in fields}
        rows.append({'barrier_id': barrier['barrier_id'], 'finding': barrier['finding'],
                     'source_values': values, 'priority': barrier['priority'],
                     'allowed_wording': [barrier['finding'], 'Discharge planning issue: ' + barrier['finding']]})
    return rows


class ReadinessExplainer:
    def __init__(self, llm=None):
        self.llm = llm

    def explain(self, patient_record, barriers):
        result = {'agent': 'ReadinessExplainer', 'status': 'requires_review',
                  'authority': 'deterministic_detector', 'scope': 'Current detector rules only; not clinical clearance.',
                  'detector_evidence': [], 'explanations': [], 'raw_response': None,
                  'validation_errors': [], 'llm': None, 'requires_review': True}
        try:
            rows = source_evidence(patient_record, barriers)
        except (ValueError, KeyError, TypeError) as error:
            result['validation_errors'] = [str(error)]
            return result
        result['detector_evidence'] = rows
        if not rows:
            result.update(status='not_needed', requires_review=False,
                          finding='No discharge barriers detected by the current rules. This does not authorize discharge.')
            return result
        # All factual content comes from the detector, not the standalone LLM analyzer.
        prompt = '''Select one allowed_wording for each supplied barrier and copy its barrier_id.
Return every barrier exactly once. Copy source_values as a JSON object string in
evidence_json. Do not change wording, evidence, or IDs. Add no facts, diagnoses,
treatments, readiness decisions, tasks, or explanations outside the allowed choices.
These are detector findings for a research workflow, not clinical clearance.'''
        try:
            if self.llm is None:
                from llm.llm_client import LLMClient
                from ollama import Client
                self.llm = LLMClient()
                self.llm.client = Client(host=self.llm.host, timeout=90)
            result['llm'] = self.llm.get_metadata()
            schema = ExplanationResponse.model_json_schema()
            properties = schema['$defs']['ExplanationItem']['properties']
            properties['barrier_id']['enum'] = [row['barrier_id'] for row in rows]
            properties['explanation']['enum'] = [wording for row in rows for wording in row['allowed_wording']]
            properties['evidence_json']['enum'] = [json.dumps(row['source_values'], sort_keys=True) for row in rows]
            schema['properties']['explanations'].update(minItems=len(rows), maxItems=len(rows))
            raw = self.llm.generate_json(system_prompt=prompt, user_data={'detector_findings': rows},
                                         schema_name='grounded_readiness_explanation', schema=schema)
            result['raw_response'] = copy.deepcopy(raw)
            parsed = ExplanationResponse.model_validate(raw)
        except Exception as error:
            # No fallback explanation is represented as a successful model response.
            result['validation_errors'] = [f'{type(error).__name__}: {error}']
            return result
        expected = {row['barrier_id']: row for row in rows}
        seen = set()
        errors = []
        accepted = []
        for item in parsed.explanations:
            row = expected.get(item.barrier_id)
            if row is None or item.barrier_id in seen:
                errors.append(f'Unexpected or duplicate barrier: {item.barrier_id}')
                continue
            seen.add(item.barrier_id)
            if item.explanation not in row['allowed_wording']:
                errors.append(f'Unsupported wording: {item.barrier_id}')
            try:
                cited = json.loads(item.evidence_json)
            except (ValueError, TypeError):
                cited = None
            if json.dumps(cited, sort_keys=True) != json.dumps(row['source_values'], sort_keys=True):
                errors.append(f'Unsupported source values: {item.barrier_id}')
            accepted.append({'barrier_id': item.barrier_id, 'explanation': item.explanation,
                             'source_values': copy.deepcopy(row['source_values'])})
        missing = set(expected) - seen
        if missing:
            errors.append('Missing barriers: ' + ', '.join(sorted(missing)))
        if errors:
            result['validation_errors'] = errors
            return result
        result.update(status='validated', requires_review=False, explanations=accepted,
                      finding='Wording and evidence match the supplied detector findings.')
        return result
