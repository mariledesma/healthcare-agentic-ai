from llm.llm_client import LLMClient


class RecommendationAgent:
    def __init__(self):
        self.llm = LLMClient()

    def generate(self, barriers, tasks):
        system_prompt = """
You are the Recommendation Agent in a supervised hospital
discharge-coordination research prototype.

You receive barriers and tasks that were already identified by
deterministic components.

Your job is to produce prioritized recommendations.

Rules:
1. Do not invent new barriers.
2. Do not invent new tasks.
3. Every recommendation must correspond to one supplied task.
4. Preserve the exact task_name as the recommendation action.
5. Preserve the supplied owner_role.
6. Do not prescribe medications.
7. Do not change medication doses.
8. Do not authorize discharge.
9. Do not execute clinical actions.
10. Recommendations are proposals only and will be checked by
    a deterministic Policy Engine and Approval Gate.
"""

        input_data = {
            "barriers": barriers,
            "tasks": tasks
        }

        schema = {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string"
                            },
                            "action": {
                                "type": "string"
                            },
                            "rationale": {
                                "type": "string"
                            },
                            "owner_role": {
                                "type": "string"
                            },
                            "priority": {
                                "type": "string",
                                "enum": [
                                    "high",
                                    "medium",
                                    "low"
                                ]
                            },
                            "supporting_barrier_ids": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "source_fields": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": [
                            "task_id",
                            "action",
                            "rationale",
                            "owner_role",
                            "priority",
                            "supporting_barrier_ids",
                            "source_fields"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            "required": [
                "recommendations"
            ],
            "additionalProperties": False
        }

        result = self.llm.generate_json(
            system_prompt=system_prompt,
            user_data=input_data,
            schema_name="recommendation_output",
            schema=schema
        )

        task_lookup = {
            task["task_id"]: task
            for task in tasks
        }

        recommendations = []

        for item in result["recommendations"]:
            task_id = item["task_id"]

            if task_id not in task_lookup:
                continue

            canonical_task = task_lookup[task_id]

            recommendations.append({
                "recommendation_id": f"R-{task_id}",
                "action": canonical_task["task_name"],
                "rationale": item["rationale"],
                "owner_role": canonical_task["owner_role"],
                "priority": item["priority"],
                "resolves_barriers": canonical_task[
                    "resolves_barriers"
                ],
                "supporting_task_ids": [
                    task_id
                ],
                "source_fields": [
                    canonical_task["source_field"]
                ]
            })

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
            "llm": self.llm.get_metadata(),
            "finding": (
                f"{len(recommendations)} "
                "LLM-generated recommendation(s)."
            ),
            "supporting_evidence": {
                "barriers_reviewed": len(barriers),
                "tasks_reviewed": len(tasks)
            },
            "confidence": 0.90,
            "source_field": "detected_barriers_and_tasks",
            "recommendations": recommendations
        }