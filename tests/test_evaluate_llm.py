import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from synthesis.evaluate_llm import RecordingLLM, check_schema, evaluate_case, governance_probes, score
from synthesis.generate import generate


class FakeLLM:
    def get_metadata(self):
        return {'provider': 'test', 'model': 'fake'}

    def generate_json(self, **kwargs):
        if kwargs['schema_name'] == 'case_analysis':
            assert 'expected_tasks' not in kwargs['user_data']
            return {'clinical_summary': 'Synthetic case.', 'discharge_summary': 'See source facts.',
                    'social_summary': 'See source facts.', 'potential_concerns': [], 'information_gaps': []}
        return {'recommendations': [dict(task_id=t['task_id'], action=t['task_name'], rationale='Addresses supplied barrier.',
                                       owner_role=t['owner_role'], priority=t['priority'],
                                       supporting_barrier_ids=t['resolves_barriers'], source_fields=[t['source_field']])
                                    for t in kwargs['user_data']['tasks']]}


class LLMEvaluationTests(unittest.TestCase):
    def test_no_persistence_imports(self):
        code = 'import sys; import synthesis.evaluate_llm; assert not any(x == "run_prototype" or x.startswith("db.") or x == "evaluation.audit_logger" for x in sys.modules)'
        subprocess.run([sys.executable, '-B', '-c', code], check=True)

    def test_separate_answers_and_pipeline_with_fake_model(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'data'
            generate(folder, count=8)
            keys = json.loads((folder / 'answer_keys.json').read_text())
            recorder = RecordingLLM(FakeLLM())
            result = evaluate_case(folder / 'cases/SYN-42-00008.json', keys['SYN-42-00008'], recorder)
            self.assertEqual(len(recorder.calls), 2)
            self.assertEqual(result['checks']['raw_recommendation_flags'], [])
            self.assertEqual(result['checks']['recommendation_coverage'], {'missed': [], 'extra': []})
            self.assertTrue(result['governance'][0]['approval']['requires_human_approval'])
            self.assertEqual(result['checks']['human_review']['status'], 'pending')
            self.assertNotIn('expected_barriers', recorder.calls[0]['input'])
            self.assertTrue(all(p['passed'] for p in governance_probes()))

    def test_raw_inventions_and_changes_survive_normalization(self):
        tasks = {'tasks': [{'task_id': 'schedule_followup', 'task_name': 'Schedule follow-up appointment',
                            'owner_role': 'Case Manager', 'resolves_barriers': ['followup_missing'], 'source_field': 'followup_status'}]}
        raw = {'recommendations': [dict(task_id='schedule_followup', action='Prescribe a drug', owner_role='Physician', supporting_barrier_ids=[], source_fields=[]),
                                   dict(task_id='invented', action='invented')]}
        checks = score({}, {'expected_barriers': [], 'expected_tasks': ['schedule_followup']},
                       {'potential_concerns': []}, {'barriers': []}, tasks, [], raw, [])
        kinds = {f['kind'] for f in checks['raw_recommendation_flags']}
        self.assertIn('invented_task', kinds)
        self.assertIn('changed_action', kinds)
        self.assertEqual(checks['recommendation_coverage']['missed'], ['schedule_followup'])

    def test_schema_rejects_wrong_types_and_extra_keys(self):
        schema = {'type': 'object', 'properties': {'items': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['items'], 'additionalProperties': False}
        for value in ({}, {'items': [7]}, {'items': [], 'extra': 1}):
            with self.assertRaises(ValueError):
                check_schema(value, schema)


if __name__ == '__main__':
    unittest.main()
