class RecommendationAgent:
    def generate(self, barriers, tasks):
        recommendations = []

        task_map = {
            task["task_id"]: task
            for task in tasks
        }

        for task_id, task in task_map.items():
            recommendation = {
                "recommendation_id": f"R-{task_id}",
                "action": task["task_name"],
                "owner_role": task["owner_role"],
                "priority": task["priority"],
                "resolves_barriers": task["resolves_barriers"],
                "source_field": task["source_field"],
                "rationale": (
                    f"This action is recommended because it addresses "
                    f"the discharge barrier(s): "
                    f"{', '.join(task['resolves_barriers'])}."
                )
            }

            recommendations.append(recommendation)

        priority_order = {
            "high": 1,
            "medium": 2,
            "low": 3
        }

        recommendations.sort(
            key=lambda item: priority_order.get(
                item["priority"],
                99
            )
        )

        return {
            "agent": "RecommendationAgent",
            "status": "success",
            "finding": (
                f"{len(recommendations)} recommendation(s) generated."
            ),
            "supporting_evidence": {
                "barriers_reviewed": len(barriers),
                "tasks_reviewed": len(tasks)
            },
            "confidence": 0.95,
            "source_field": "detected_tasks",
            "recommendations": recommendations
        }