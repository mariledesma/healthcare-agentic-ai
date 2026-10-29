import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from synthesis.generate import generate, validate
from synthesis.evaluate import evaluate


class SynthesisTests(unittest.TestCase):
    def test_pilot_covers_detectors_without_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'pilot'
            result = generate(output)
            self.assertEqual(result['unique_structured_cases'], 100)
            self.assertEqual(len(result['scenario_families']), 21)
            report = evaluate(output)
            self.assertEqual(report['cases'], 100)
            self.assertEqual(report['failures'], [])
            for case in (output / 'cases').glob('*.json'):
                record = json.loads(case.read_text())
                self.assertNotIn('expected_barriers', record)
                validate(record)
            with self.assertRaises(ValueError):
                generate(output)

    def test_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / 'a', Path(temp) / 'b'
            generate(a, 25, 17)
            generate(b, 25, 17)
            for path in a.rglob('*.json'):
                self.assertEqual(path.read_bytes(), (b / path.relative_to(a)).read_bytes())

    def test_validation_rejects_leaks_and_inconsistent_transport(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'pilot'
            generate(output, 1)
            case = json.loads(next((output / 'cases').glob('*.json')).read_text())
            case['expected_tasks'] = []
            with self.assertRaises(ValueError):
                validate(case)
            del case['expected_tasks']
            case['transport_status'] = 'not_arranged'
            with self.assertRaises(ValueError):
                validate(case)

    def test_narrative_failure_is_bounded_and_leaves_no_output(self):
        from types import SimpleNamespace
        fake = SimpleNamespace(chat=lambda **kwargs: SimpleNamespace(message=SimpleNamespace(content='{"introduction":"invented medication"}')))
        with tempfile.TemporaryDirectory() as temp, patch('ollama.Client', return_value=fake):
            output = Path(temp) / 'pilot'
            with self.assertRaises(ValueError):
                generate(output, 1, model='test')
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
