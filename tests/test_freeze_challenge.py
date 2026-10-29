import json
from pathlib import Path
import shutil
import tempfile
import unittest

from synthesis.freeze_challenge import freeze, verify_snapshot
from synthesis.evaluate_challenge import load_challenge, evaluate

SOURCE = Path(__file__).resolve().parents[1] / 'data/challenge/discharge_v1'


class FreezeChallengeTests(unittest.TestCase):
    def test_snapshot_preserves_inputs_approvals_and_distinguishes_clinical_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'approved'
            index = freeze(SOURCE, output, '2026-10-28')
            manifest, records, answers, reviews = load_challenge(output)
            self.assertTrue(manifest['approved_for_workflow_regression'])
            self.assertFalse(manifest['approved_for_benchmark'])
            self.assertTrue(manifest['frozen'])
            self.assertEqual(len(records),26)
            self.assertEqual(verify_snapshot(output),index)
            for case_id in records:
                self.assertEqual((SOURCE/'cases'/f'{case_id}.json').read_bytes(),(output/'cases'/f'{case_id}.json').read_bytes())
                self.assertEqual(answers[case_id]['approval_provenance'],reviews[case_id])
            result=evaluate(output)
            self.assertTrue(result['label_status'].startswith('user-approved'))
            self.assertEqual(len(result['implementation_sha256']),5)
            with self.assertRaises(ValueError):
                freeze(SOURCE,output,'2026-10-28')

    def test_pending_review_cannot_be_frozen(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'candidate'
            shutil.copytree(SOURCE,source)
            path=source/'review_decisions.json'
            reviews=json.loads(path.read_text())
            reviews['CHAL-026']['decision']='pending'
            path.write_text(json.dumps(reviews))
            output=Path(temp)/'approved'
            with self.assertRaisesRegex(ValueError,'explicit approval'):
                freeze(source,output,'2026-10-28')
            self.assertFalse(output.exists())

    def test_review_history_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'approved'
            freeze(SOURCE,output,'2026-10-28')
            path=output/'review_decisions.json'
            path.write_text(path.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'integrity mismatch'):
                load_challenge(output)

    def test_added_files_including_nested_checksum_files_are_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'approved'
            freeze(SOURCE,output,'2026-10-28')
            (output/'provenance/checksums.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'added or removed'):
                verify_snapshot(output)
