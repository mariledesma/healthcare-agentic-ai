
from pathlib import Path

from run_prototype import run_pipeline


# ---------------------------------------------------------
# Calculate precision, recall, and F1 score
# ---------------------------------------------------------

def calculate_metrics(tp, fp, fn):
    precision = (
        tp / (tp + fp)
        if tp + fp > 0
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn > 0
        else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }


# ---------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------

def main():
    synthetic_dir = Path("data/synthetic")
    case_files = sorted(synthetic_dir.glob("case_*.json"))

    if not case_files:
        print("No synthetic patient cases were found.")
        return

    barrier_totals = {
        "tp": 0,
        "fp": 0,
        "fn": 0
    }

    task_totals = {
        "tp": 0,
        "fp": 0,
        "fn": 0
    }

    completed_cases = 0
    failed_cases = 0

    print("\nHealthcare Agentic AI - Research Evaluation")
    print("=" * 65)

    for case_file in case_files:
        print(f"\nRunning: {case_file.name}")

        try:
            result = run_pipeline(case_file)

            if "evaluation" not in result:
                failed_cases += 1
                print("SKIPPED: Pipeline did not complete.")
                continue

            evaluation = result["evaluation"]

            # Read the nested evaluation dictionaries.
            barriers = evaluation["barriers"]
            tasks = evaluation["tasks"]

            # Barrier true positives, false positives,
            # and false negatives.
            barrier_totals["tp"] += len(barriers["matched"])
            barrier_totals["fp"] += len(barriers["extra"])
            barrier_totals["fn"] += len(barriers["missed"])

            # Task true positives, false positives,
            # and false negatives.
            task_totals["tp"] += len(tasks["matched"])
            task_totals["fp"] += len(tasks["extra"])
            task_totals["fn"] += len(tasks["missed"])

            completed_cases += 1

            print(f"Case: {result['case_id']}")
            print(f"Condition: {result['condition']}")

            print("\nBarriers:")
            print("  Expected:", barriers["expected"])
            print("  Detected:", barriers["detected"])
            print("  Matched: ", barriers["matched"])
            print("  Missed:  ", barriers["missed"])
            print("  Extra:   ", barriers["extra"])

            print("\nTasks:")
            print("  Expected:", tasks["expected"])
            print("  Detected:", tasks["detected"])
            print("  Matched: ", tasks["matched"])
            print("  Missed:  ", tasks["missed"])
            print("  Extra:   ", tasks["extra"])

        except Exception as error:
            failed_cases += 1
            print(f"ERROR: {type(error).__name__}: {error}")

    # -----------------------------------------------------
    # Calculate aggregate micro-averaged metrics
    # -----------------------------------------------------

    barrier_metrics = calculate_metrics(
        barrier_totals["tp"],
        barrier_totals["fp"],
        barrier_totals["fn"]
    )

    task_metrics = calculate_metrics(
        task_totals["tp"],
        task_totals["fp"],
        task_totals["fn"]
    )

    print("\n" + "=" * 65)
    print("OVERALL RESEARCH EVALUATION")
    print("=" * 65)

    print(f"Cases completed: {completed_cases}")
    print(f"Cases failed:    {failed_cases}")

    print("\nBarrier Detection:")
    print(f"True positives:  {barrier_totals['tp']}")
    print(f"False positives: {barrier_totals['fp']}")
    print(f"False negatives: {barrier_totals['fn']}")
    print(f"Precision: {barrier_metrics['precision']:.2%}")
    print(f"Recall:    {barrier_metrics['recall']:.2%}")
    print(f"F1 Score:  {barrier_metrics['f1']:.2%}")

    print("\nTask Detection:")
    print(f"True positives:  {task_totals['tp']}")
    print(f"False positives: {task_totals['fp']}")
    print(f"False negatives: {task_totals['fn']}")
    print(f"Precision: {task_metrics['precision']:.2%}")
    print(f"Recall:    {task_metrics['recall']:.2%}")
    print(f"F1 Score:  {task_metrics['f1']:.2%}")

    print("\nNote: These metrics are based on synthetic cases.")
    print("They do not establish clinical performance.")


if __name__ == "__main__":
    main()
