import json
import unittest
from agents.case_analyzer import CaseAnalyzer
from agents.barrier_detector import BarrierDetector
from synthesis.compare_llm import concern_evidence, concern_source_coverage


class CaptureLLM:
    def generate_json(self, **kwargs):
        self.request = kwargs
        return dict(clinical_summary='Source summary.', discharge_summary='Source summary.',
                    social_summary='Source summary.', potential_concerns=[], information_gaps=[])

    def get_metadata(self):
        return {'provider': 'test', 'model': 'fake'}


class AnalyzerPromptTests(unittest.TestCase):
    def test_analyzer_preserves_input_and_detector_transport_boundaries(self):
        analyzer = CaseAnalyzer()
        analyzer.llm = CaptureLLM()
        record = {'case_id': 'test', 'planned_discharge_window': 'afternoon', 'transport_time': '14:00'}
        result = analyzer.analyze(record)
        prompt = analyzer.llm.request['system_prompt']
        self.assertIn('Use only information explicitly contained', prompt)
        self.assertIs(analyzer.llm.request['user_data'], record)
        self.assertEqual(result['potential_concerns'], [])
        detector = BarrierDetector()
        for time, conflict in [('11:59', True), ('12:00', False), ('14:00', False), ('16:59', False), ('17:00', True), ('19:00', True)]:
            self.assertEqual(detector.has_transport_timing_conflict('afternoon', time), conflict)

    def test_empty_concerns_do_not_pass_positive_case_coverage(self):
        self.assertEqual(concern_source_coverage('followup', [])['missing_source_fields'], ['followup_status'])
        concern = {'source_field': 'transport_time'}
        self.assertEqual(concern_source_coverage('ready', [concern])['unexpected_source_fields'], ['transport_time'])
        self.assertIsNone(concern_source_coverage('unreviewed_family', []))

    def test_evidence_requires_exact_values_and_fields(self):
        record = {'followup_status': 'not_scheduled'}
        concern = dict(finding='Follow-up is not scheduled.', source_field='followup_status',
                       supporting_evidence=json.dumps(record))
        self.assertEqual(concern_evidence(record, [concern]), [])
        for evidence in ('followup_status', '{"followup_status":"scheduled"}', '{}', '[]'):
            bad = dict(concern, supporting_evidence=evidence)
            self.assertTrue(concern_evidence(record, [bad]))

    def test_compatible_timing_with_exact_evidence_is_still_not_semantically_validated(self):
        record = {'transport_time': '14:00', 'planned_discharge_window': 'afternoon'}
        concern = dict(finding='These times conflict.', source_field='transport_time + planned_discharge_window', supporting_evidence=json.dumps(record))
        self.assertEqual(concern_evidence(record, [concern]), [])
        # The evidence checker deliberately does not claim factual concern validity.


if __name__ == '__main__':
    unittest.main()
