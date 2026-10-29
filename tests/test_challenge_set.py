import json
import shutil
import tempfile
import unittest
from pathlib import Path

from synthesis.evaluate_challenge import load_challenge, evaluate, check_no_labels

DATA = Path(__file__).resolve().parents[1] / 'data/challenge/discharge_v1'


class ChallengeSetTests(unittest.TestCase):
    def test_provenance_and_no_fake_signoff(self):
        manifest, records, answers, reviews = load_challenge(DATA)
        self.assertEqual(len(records), 26)
        self.assertFalse(manifest['approved_for_benchmark'])
        for review in reviews.values():
            self.assertIn(review['decision'], ('pending', 'approved', 'revise', 'rejected'))
            if review['decision'] != 'pending':
                self.assertTrue(review['reviewer'])
                self.assertTrue(review['reviewed_at'])
        for record in records.values():
            check_no_labels(record)
        self.assertTrue(any(a['proposed_taxonomy_ids'] for a in answers.values()))

    def test_deliberate_unknown_missing_and_invalid_inputs_are_preserved(self):
        _, records, answers, _ = load_challenge(DATA)
        self.assertNotIn('followup_status', records['CHAL-011'])
        self.assertEqual(records['CHAL-012']['caregiver_status'], 'unknown')
        self.assertEqual(records['CHAL-022']['transport_time'], '14:75')
        self.assertEqual(answers['CHAL-009']['expected_barriers'], [])
        self.assertIn('clarify_followup_status', answers['CHAL-009']['expected_tasks'])

    def test_changed_inputs_or_answers_fail_integrity_check(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'suite'
            shutil.copytree(DATA, folder)
            case = folder/'cases/CHAL-001.json'
            original = case.read_text()
            case.write_text(original+' ')
            with self.assertRaisesRegex(ValueError, 'Patient input changed'):
                load_challenge(folder)
            case.write_text(original)
            answer = folder/'answer_keys.json'
            answer.write_text(answer.read_text()+' ')
            with self.assertRaisesRegex(ValueError, 'Answer key changed'):
                load_challenge(folder)

    def test_baseline_distinguishes_unassessed_requirements_from_matches(self):
        report = evaluate(DATA)
        self.assertEqual(report['cases'],26)
        _, _, _, ledger = load_challenge(DATA)
        self.assertEqual(sum(report['review_decisions'].values()), 26)
        self.assertEqual(report['review_decisions']['pending'], sum(r['decision'] == 'pending' for r in ledger.values()))
        self.assertGreater(report['cases_with_unassessed_requirements'],0)
        self.assertEqual(report['clinical_accuracy'],'not measured; draft labels and unassessed capabilities')
        self.assertEqual(len(report['results']),26)

    def test_label_leak_is_rejected_even_in_nested_notes(self):
        with self.assertRaises(ValueError):
            check_no_labels({'free_text_notes':{'expected_tasks':['leaked']}})
