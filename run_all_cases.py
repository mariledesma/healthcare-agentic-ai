from pathlib import Path

from run_prototype import run_pipeline


def main():
    synthetic_dir = Path("data/synthetic")

    case_files = sorted(synthetic_dir.glob("case_*.json"))

    total_cases = 0
    total_expected = 0
    total_detected = 0
    total_matched = 0

    print("\nHealthcare Agentic AI - Prototype Evaluation")
    print("-" * 72)

    for case_file in case_files:
        result = run_pipeline(case_file)

        evaluation = result["evaluation"]

        expected = evaluation["expected_barriers"]
        detected = evaluation["detected_barriers"]
        matched = evaluation["matched_barriers"]
        missed = evaluation["missed_barriers"]
        extra = evaluation["extra_barriers"]

        total_cases += 1
        total_expected += len(expected)
        total_detected += len(detected)
        total_matched += len(matched)

        print(f"\nCase: {result['case_id']} ({result['condition']})")
        print(f"Expected: {expected}")
        print(f"Detected: {detected}")
        print(f"Matched:  {matched}")
        print(f"Missed:   {missed}")
        print(f"Extra:    {extra}")

    recall = (
        total_matched / total_expected
        if total_expected > 0
        else 0
    )

    precision = (
        total_matched / total_detected
        if total_detected > 0
        else 0
    )

    print("\n" + "=" * 72)
    print("Overall Results")
    print("=" * 72)
    print(f"Cases evaluated: {total_cases}")
    print(f"Expected barriers: {total_expected}")
    print(f"Detected barriers: {total_detected}")
    print(f"Matched barriers: {total_matched}")
    print(f"Barrier recall: {recall:.2%}")
    print(f"Barrier precision: {precision:.2%}")


if __name__ == "__main__":
    main()