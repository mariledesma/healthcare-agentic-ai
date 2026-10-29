import copy
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents.barrier_detector import BarrierDetector
from agents.readiness_explainer import ReadinessExplainer, source_evidence
from agents.output_composer import OutputComposer

ROOT = Path(__file__).resolve().parents[1]


def fixture(number=2):
    return json.loads((ROOT / f'data/generated/pilot_100/cases/SYN-42-{number:05d}.json').read_text())


class FakeExplainerLLM:
    def __init__(self, mode='valid'):
        self.mode = mode
        self.calls = []

    def get_metadata(self):
        return {'provider': 'test', 'model': 'fake'}

    def generate_json(self, **kwargs):
        self.calls.append(kwargs)
        if self.mode == 'offline':
            raise ConnectionError('Model unavailable')
        rows = kwargs['user_data']['detector_findings']
        items = [{'barrier_id': row['barrier_id'], 'explanation': row['allowed_wording'][0],
                  'evidence_json': json.dumps(row['source_values'], sort_keys=True)} for row in rows]
        if self.mode == 'invented':
            items[0]['explanation'] = 'Patient can be discharged now.'
        elif self.mode == 'changed_value':
            items[0]['evidence_json'] = '{"followup_status":"scheduled"}'
        elif self.mode == 'missing':
            items = []
        elif self.mode == 'duplicate':
            items.append(copy.deepcopy(items[0]))
        elif self.mode == 'unknown_id':
            items[0]['barrier_id'] = 'fabricated'
        elif self.mode == 'extra':
            items[0]['new_diagnosis'] = 'invented'
        elif self.mode == 'wrong_type':
            return {'explanations': 'invalid'}
        return {'explanations': items}


class ReadinessExplainerTests(unittest.TestCase):
    def test_ready_case_does_not_call_model_or_claim_discharge_clearance(self):
        llm = FakeExplainerLLM()
        record = fixture(1)
        result = ReadinessExplainer(llm).explain(record, [])
        self.assertEqual(result['status'], 'not_needed')
        self.assertEqual(llm.calls, [])
        self.assertIn('does not authorize discharge', result['finding'])

    def test_all_pilot_findings_have_exact_evidence_and_complete_coverage(self):
        for path in sorted((ROOT / 'data/generated/pilot_100/cases').glob('*.json')):
            record = json.loads(path.read_text())
            barriers = BarrierDetector().detect(record)['barriers']
            original = copy.deepcopy(record)
            llm = FakeExplainerLLM()
            result = ReadinessExplainer(llm).explain(record, barriers)
            self.assertIn(result['status'], ('validated', 'not_needed'))
            self.assertEqual(record, original)
            self.assertEqual({r['barrier_id'] for r in result['explanations']}, {b['barrier_id'] for b in barriers})
            if llm.calls:
                supplied = llm.calls[0]['user_data']
                self.assertEqual(set(supplied), {'detector_findings'})
                self.assertNotIn('expected_barriers', json.dumps(supplied))
                self.assertNotIn('medications', json.dumps(supplied))

    def test_invalid_model_output_is_preserved_and_not_silently_repaired(self):
        record = fixture(2)
        barriers = BarrierDetector().detect(record)['barriers']
        for mode in ('invented', 'changed_value', 'missing', 'duplicate', 'unknown_id', 'extra', 'wrong_type'):
            with self.subTest(mode=mode):
                result = ReadinessExplainer(FakeExplainerLLM(mode)).explain(record, barriers)
                self.assertEqual(result['status'], 'requires_review')
                self.assertTrue(result['requires_review'])
                self.assertTrue(result['validation_errors'])
                self.assertIsNotNone(result['raw_response'])
                self.assertEqual(result['explanations'], [])
                self.assertEqual(result['detector_evidence'][0]['source_values'], {'followup_status': 'not_scheduled'})

    def test_stale_findings_and_missing_fields_are_not_sent_to_model(self):
        llm = FakeExplainerLLM()
        record = fixture(2)
        self.assertTrue(ReadinessExplainer(llm).explain(record, [])['requires_review'])
        self.assertEqual(llm.calls, [])
        record.pop('followup_status')
        fake = [{'barrier_id': 'followup_missing', 'source_field': 'followup_status'}]
        self.assertTrue(ReadinessExplainer(llm).explain(record, fake)['requires_review'])
        self.assertEqual(llm.calls, [])

    def test_model_unavailable_is_visible_without_fallback(self):
        record = fixture(2)
        result = ReadinessExplainer(FakeExplainerLLM('offline')).explain(record, BarrierDetector().detect(record)['barriers'])
        self.assertTrue(result['requires_review'])
        self.assertIn('ConnectionError', result['validation_errors'][0])
        self.assertEqual(result['explanations'], [])

    def test_timing_boundaries_and_two_field_evidence(self):
        record = fixture(1)
        for time, conflicting in [('11:59', True), ('12:00', False), ('16:59', False), ('17:00', True), ('19:00', True)]:
            record['transport_time'] = time
            barriers = BarrierDetector().detect(record)['barriers']
            result = ReadinessExplainer(FakeExplainerLLM()).explain(record, barriers)
            self.assertEqual(result['status'], 'validated' if conflicting else 'not_needed')
            if conflicting:
                self.assertEqual(result['explanations'][0]['source_values'], {'planned_discharge_window': 'afternoon', 'transport_time': time})

    def test_composer_surfaces_review_without_changing_governance(self):
        record = fixture(2)
        result = OutputComposer().compose(record, [], [], [], [], {'requires_review': True})
        self.assertTrue(result['explanation_review_required'])
        self.assertEqual(result['human_approval_required'], [])

    def test_pipeline_preserves_raw_analyzer_and_integrates_grounded_output(self):
        # Import application orchestration with a fake persistence module; never
        # import the actual DB module or create an audit logger directory.
        stub = types.ModuleType('db.repository')
        stub.save_pipeline_run = MagicMock(return_value={'status': 'test_stub'})
        with patch.dict(sys.modules, {'db.repository': stub}):
            spec = importlib.util.spec_from_file_location('grounded_pipeline_test', ROOT / 'run_prototype.py')
            pipeline = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pipeline)
        raw = {'agent': 'CaseAnalyzer', 'status': 'success', 'llm': {'provider': 'test', 'model': 'fake'},
               'finding': 'Unverified.', 'potential_concerns': [{'finding': 'An unsupported concern.'}]}
        analyzer = MagicMock()
        analyzer.analyze.return_value = raw
        analyzer.llm.get_metadata.return_value = {'provider': 'test', 'model': 'fake'}
        recommendation = MagicMock()
        recommendation.generate.return_value = {'llm': {'provider': 'test', 'model': 'fake'},
                                                 'status': 'success', 'recommendations': []}
        with patch.object(pipeline, 'CaseAnalyzer', return_value=analyzer), \
             patch.object(pipeline, 'RecommendationAgent', return_value=recommendation), \
             patch.object(pipeline, 'ReadinessExplainer', return_value=ReadinessExplainer(FakeExplainerLLM())), \
             patch.object(pipeline, 'AuditLogger') as audit:
            path = ROOT / 'data/generated/pilot_100/cases/SYN-42-00001.json'
            result = pipeline.run_pipeline(path)
            self.assertEqual(result['case_analyzer'], raw)
            analysis_log = next(call.kwargs for call in audit.return_value.log.call_args_list
                                if call.kwargs['module'] == 'CaseAnalyzer')
            self.assertEqual(analysis_log['details']['raw_analysis'], raw)
            explanation_log = next(call.kwargs for call in audit.return_value.log.call_args_list
                                   if call.kwargs['module'] == 'ReadinessExplainer')
            self.assertIn('raw_response', explanation_log['details'])
            self.assertEqual(result['readiness_explanation']['status'], 'not_needed')
            self.assertEqual(result['case_analyzer_role'], 'unverified_research_comparison')
            self.assertEqual(result['final_output']['readiness_explanation'], result['readiness_explanation'])
            analyzer.analyze.side_effect = RuntimeError('research model failed')
            result = pipeline.run_pipeline(path)
            self.assertEqual(result['case_analyzer']['status'], 'error')
            self.assertEqual(result['readiness_explanation']['status'], 'not_needed')
            self.assertTrue(audit.return_value.log.called)
        self.assertEqual(stub.save_pipeline_run.call_count, 2)
