import argparse
import json
from pathlib import Path

from agents.input_reader import InputReader
from agents.case_analyzer import CaseAnalyzer
from agents.barrier_detector import BarrierDetector


def run_pipeline(case_file):
    input_reader = InputReader()
    case_analyzer = CaseAnalyzer()
    barrier_detector = BarrierDetector()

    input_result = input_reader.read(case_file)

    if input_result["status"] != "success":
        return {
            "input_reader": input_result
        }

    patient_record = input_result["patient_record"]

    analysis_result = case_analyzer.analyze(patient_record)

    barrier_result = barrier_detector.detect(
        patient_record,
        analysis_result
    )

    expected_barriers = patient_record.get("expected_barriers", [])

    detected_barriers = [
        barrier["barrier_id"]
        for barrier in barrier_result["barriers"]
    ]

    matched_barriers = sorted(
        set(expected_barriers) & set(detected_barriers)
    )

    missed_barriers = sorted(
        set(expected_barriers) - set(detected_barriers)
    )

    extra_barriers = sorted(
        set(detected_barriers) - set(expected_barriers)
    )

    return {
        "case_id": patient_record["case_id"],
        "condition": patient_record["condition"],
        "pipeline": [
            "InputReader",
            "CaseAnalyzer",
            "BarrierDetector"
        ],
        "input_reader": input_result,
        "case_analyzer": analysis_result,
        "barrier_detector": barrier_result,
        "evaluation": {
            "expected_barriers": expected_barriers,
            "detected_barriers": detected_barriers,
            "matched_barriers": matched_barriers,
            "missed_barriers": missed_barriers,
            "extra_barriers": extra_barriers
        }
    }


def save_result(result):
    results_directory = Path("results")
    results_directory.mkdir(exist_ok=True)

    case_id = result.get("case_id", "unknown_case")

    output_path = results_directory / f"{case_id.lower()}_output.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "case_file",
        help="Path to synthetic patient JSON file"
    )

    args = parser.parse_args()

    result = run_pipeline(args.case_file)

    output_path = save_result(result)

    print(json.dumps(result, indent=2))
    print(f"\nResult saved to: {output_path}")