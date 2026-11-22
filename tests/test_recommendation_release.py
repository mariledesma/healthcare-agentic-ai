import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from agents.barrier_detector import BarrierDetector
from agents.input_reader import InputReader
from agents.task_detector import TaskDetector
from research.experiments import proposals_for
from research.provenance import verify
import run_prototype


class RecommendationReleaseTests(unittest.TestCase):
    def test_plan_omits_unverified_text_and_research_snapshot_preserves_it(self):
        base = Path(__file__).resolve().parents[1] / "data" / "synthetic"
        for case_file in sorted(base.glob("case_*.json")):
            with self.subTest(case=case_file.name):
                self.check_release(case_file)

    def check_release(self, case_file):
        record = InputReader().read(case_file)["patient_record"]
        barriers = BarrierDetector().detect(record)["barriers"]
        tasks = TaskDetector().detect(record, barriers)["tasks"]
        proposals = proposals_for(tasks)
        self.assertTrue(proposals)
        rationale = "The patient requested a printed copy yesterday."
        proposals[0].update(rationale=rationale, arbitrary_note=rationale)
        proposals[0]["supporting_task_ids"] = ["not-a-verified-task"]
        raw = {"recommendations": copy.deepcopy(proposals)}
        fake = {
            "status": "success",
            "llm": {"provider": "test", "model": "stub"},
            "recommendations": proposals,
            "raw_response": raw,
        }
        with (
            patch.object(run_prototype.CaseAnalyzer, "analyze", side_effect=RuntimeError("stub")),
            patch.object(run_prototype.ReadinessExplainer, "explain", return_value={
                "requires_review": False, "status": "disabled", "validation_errors": [],
                "detector_evidence": [], "raw_response": None, "explanations": [], "llm": None,
            }),
            patch.object(run_prototype.RecommendationAgent, "generate", return_value=fake),
            patch.object(run_prototype, "AuditLogger"),
        ):
            result = run_prototype.run_pipeline(case_file, persist=False)
        info = result["recommendation_agent"]
        plan = result["final_output"]["recommendations"]
        self.assertEqual(plan, info["recommendations"])
        self.assertEqual(len(plan), len(proposals))
        self.assertNotIn("raw_response", info)
        displayed = next(item for item in plan if item["task_id"] == proposals[0]["task_id"])
        self.assertEqual(displayed["action"], proposals[0]["action"])
        self.assertEqual(displayed["source_fields"], proposals[0]["source_fields"])
        self.assertEqual(set(displayed), {
            "recommendation_id", "task_id", "action", "owner_role", "priority",
            "resolves_barriers", "source_fields",
        })
        self.assertEqual(result["safety_verification"]["accepted"][0]["rationale"], rationale)
        snapshot = result["integrity_artifacts"]
        self.assertEqual(snapshot["recommendation_result"]["raw_response"], raw)
        self.assertTrue(verify(result["provenance"], record, snapshot))


if __name__ == "__main__":
    unittest.main()
