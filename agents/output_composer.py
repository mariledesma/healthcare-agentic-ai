class OutputComposer:
    def compose(
        self,
        patient_record,
        barriers,
        tasks,
        recommendations,
        governance_results
    ):
        human_approval_required = []

        for item in governance_results:
            approval = item["approval"]

            if approval["requires_human_approval"]:
                human_approval_required.append({
                    "recommendation_id": item["recommendation_id"],
                    "action": item["action"],
                    "approval_status": approval["approval_status"]
                })

        return {
            "case_id": patient_record["case_id"],
            "condition": patient_record["condition"],
            "discharge_coordination_summary": {
                "barrier_count": len(barriers),
                "task_count": len(tasks),
                "recommendation_count": len(recommendations),
                "human_approval_required_count": len(
                    human_approval_required
                )
            },
            "barriers": barriers,
            "pending_tasks": tasks,
            "recommendations": recommendations,
            "governance": governance_results,
            "human_approval_required": human_approval_required,
            "final_status": self.determine_status(
                barriers,
                human_approval_required
            )
        }

    def determine_status(
        self,
        barriers,
        human_approval_required
    ):
        if human_approval_required:
            return "human_review_required"

        if barriers:
            return "discharge_barriers_present"

        return "no_detected_discharge_barriers"