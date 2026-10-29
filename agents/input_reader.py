
import json
from pathlib import Path


class InputReader:
    def __init__(self):
        self.required_fields = [
            "case_id",
            "condition",
            "diagnoses",
            "medications",
            "discharge_summary"
        ]

    def read(self, file_path):
        path = Path(file_path)

        # Check whether the patient file exists.
        if not path.is_file():
            return self.error_result(
                "Patient case file was not found.",
                str(path)
            )

        # Load the JSON patient record.
        try:
            with open(path, "r", encoding="utf-8") as file:
                patient_case = json.load(file)

        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            return self.error_result(
                "Patient case contains invalid JSON.",
                str(error)
            )

        except OSError as error:
            return self.error_result(
                "Patient case could not be opened.",
                str(error)
            )

        # The root of the JSON must be an object.
        if not isinstance(patient_case, dict):
            return self.error_result(
                "Patient case must be a JSON object.",
                "patient_json"
            )

        # Check for required clinical fields.
        missing_fields = [
            field
            for field in self.required_fields
            if field not in patient_case
        ]

        if missing_fields:
            return self.error_result(
                "Required patient fields are missing.",
                missing_fields
            )

        # -------------------------------------------------
        # RESEARCH EVALUATION SEPARATION
        # -------------------------------------------------
        # Expected answers are used for evaluation only.
        # They must not be available to any AI agent.

        answer_key = {
            "expected_barriers": patient_case.pop(
                "expected_barriers", []
            ),
            "expected_tasks": patient_case.pop(
                "expected_tasks", []
            )
        }

        # Top-level distractor labels are evaluation
        # metadata. Distractor text inside actual
        # clinical notes remains in the patient record.
        patient_case.pop("distractors", None)

        # -------------------------------------------------
        # RETURN VALIDATED INPUT
        # -------------------------------------------------

        return {
            "agent": "InputReader",
            "status": "success",
            "finding": "Patient case successfully loaded and validated.",
            "supporting_evidence": {
                "case_id": patient_case["case_id"],
                "condition": patient_case["condition"]
            },
            "confidence": 1.0,
            "source_field": "patient_json",
            "patient_record": patient_case,
            "answer_key": answer_key
        }

    def error_result(self, message, evidence):
        return {
            "agent": "InputReader",
            "status": "error",
            "finding": message,
            "supporting_evidence": evidence,
            "confidence": 1.0,
            "source_field": "patient_json"
        }
