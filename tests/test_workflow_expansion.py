import unittest
from agents.barrier_detector import BarrierDetector
from agents.task_detector import TaskDetector
from agents.readiness_explainer import source_evidence
from policy.approval_gate import ApprovalGate


class WorkflowExpansionTests(unittest.TestCase):
    def test_unknown_and_forbidden_never_pass_gate(self):
        gate = ApprovalGate()
        for task in (None, "made_up", ""):
            self.assertTrue(gate.evaluate({"task_id": task})["requires_human_approval"])
        for operation in ("place_discharge_order", "send_prescription", "modify_medication_list"):
            self.assertEqual(gate.evaluate({"task_id": "arrange_transport", "requested_operation": operation})["approval_status"], "blocked")
        self.assertFalse(gate.evaluate({"task_id": "arrange_transport"})["requires_human_approval"])

    def test_combined_new_findings_preserve_evidence_and_review(self):
        record = {"pending_imaging": ["report A", "report B"], "pending_consult": ["consult C"],
                  "medical_stability_status": "unstable", "case_manager_status": "unavailable"}
        barriers = BarrierDetector().detect(record)["barriers"]
        tasks = TaskDetector().detect(record, barriers)["tasks"]
        self.assertEqual(len(barriers), 4)
        self.assertEqual(len(source_evidence(record, barriers)), 4)
        self.assertEqual({t["task_id"] for t in tasks}, {"review_imaging_result", "review_consult_recommendations", "request_clinical_reassessment", "assign_case_manager"})
        for task in tasks:
            result = ApprovalGate().evaluate(task)
            self.assertEqual(result["requires_human_approval"], task["task_id"] != "assign_case_manager")
            self.assertTrue(set(task["resolves_barriers"]) <= {b["barrier_id"] for b in barriers})

    def test_absence_does_not_establish_clinical_instability(self):
        for value in (None, "unknown", "stable"):
            record = {"pending_imaging": [], "pending_consult": [], "medical_stability_status": value}
            self.assertEqual(BarrierDetector().detect(record)["barriers"], [])

    def test_transport_full_time_validation_and_boundaries(self):
        detector = BarrierDetector()
        for invalid in ("14:75", "24:00", "-1:00", "12", "12:00:00", None):
            self.assertFalse(detector.has_transport_timing_conflict("morning", invalid))
        for window, time, expected in (("morning", "11:59", False), ("morning", "12:00", True),
                                       ("afternoon", "16:59", False), ("afternoon", "17:00", True),
                                       ("evening", "17:00", False)):
            self.assertEqual(detector.has_transport_timing_conflict(window, time), expected)

    def test_transport_dates_both_directions_and_combined_conflicts(self):
        for ride in ("2026-12-30", "2027-01-01"):
            record = {"transport_status": "arranged", "planned_discharge_date": "2026-12-31",
                      "transport_date": ride, "transport_time": "18:00", "planned_discharge_window": "morning"}
            barriers = BarrierDetector().detect(record)["barriers"]
            self.assertEqual({b["barrier_id"] for b in barriers}, {"transport_date_conflict", "transport_timing"})
            self.assertEqual(len(source_evidence(record, barriers)), 2)
            tasks = TaskDetector().detect(record, barriers)["tasks"]
            self.assertEqual(len(tasks), 1)
            self.assertEqual(set(tasks[0]["resolves_barriers"]), {"transport_date_conflict", "transport_timing"})
        for ride in (None, "2026-02-30", "20261231", "2026-12-31"):
            record = {"transport_status": "arranged", "planned_discharge_date": "2026-12-31", "transport_date": ride}
            self.assertEqual(BarrierDetector().detect(record)["barriers"], [])
