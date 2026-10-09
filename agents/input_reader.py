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

        if not path.exists():
            return {
                "agent": "InputReader",
                "status": "error",
                "finding": "Patient case file was not found.",
                "supporting_evidence": str(path),
                "confidence": 1.0,
                "source_field": "file_path"
            }

        try:
            with open(path, "r", encoding="utf-8") as file:
                patient_case = json.load(file)
        except json.JSONDecodeError as error:
            return {
                "agent": "InputReader",
                "status": "error",
                "finding": "Patient case contains invalid JSON.",
                "supporting_evidence": str(error),
                "confidence": 1.0,
                "source_field": "patient_json"
            }

        missing_fields = [
            field for field in self.required_fields
            if field not in patient_case
        ]

        if missing_fields:
            return {
                "agent": "InputReader",
                "status": "error",
                "finding": "Required patient fields are missing.",
                "supporting_evidence": missing_fields,
                "confidence": 1.0,
                "source_field": "patient_json"
            }

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
            "patient_record": patient_case
        }