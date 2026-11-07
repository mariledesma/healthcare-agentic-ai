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
4. Preserve the exact task_id.
5. Preserve the exact task_name as the recommendation action.
6. Preserve the supplied owner_role.
7. Do not prescribe medications.
8. Do not change medication doses.
9. Do not authorize discharge.
10. Do not execute clinical actions.
11. Recommendations are proposals only.
12. Return exactly one recommendation per supplied task. Copy priority, source_fields
    (a one-element list containing the task source_field), and resolves_barriers
    (as supporting_barrier_ids) exactly.
13. Every recommendation will be checked by deterministic governance.
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

        # Preserve raw proposals before verification; never silently repair or drop them.
        raw_items = result.get("recommendations") if isinstance(result, dict) else None
        recommendations = []
        if isinstance(raw_items, list):
            for index, item in enumerate(raw_items):
                if not isinstance(item, dict):
                    recommendations.append(item)
                    continue
                task_id = item.get("task_id")
                recommendations.append({
                    "recommendation_id": f"recommendation_{task_id}_{index}",
                    "task_id": task_id,
                    "action": item.get("action"),
                    "rationale": item.get("rationale"),
                    "owner_role": item.get("owner_role"),
                    "priority": item.get("priority"),
                    "resolves_barriers": item.get("supporting_barrier_ids"),
                    "supporting_task_ids": [task_id],
                    "source_fields": item.get("source_fields"),
                    **({"requested_operation": item["requested_operation"]} if "requested_operation" in item else {})
                })
        else:
            recommendations = [raw_items]

        return {
            "agent": "RecommendationAgent",
            "status": "success",
            "llm": self.llm.get_metadata(),

            "finding": (
                f"{len(recommendations)} "
                "LLM-generated recommendation(s)."
            ),

            "supporting_evidence": {
                "barriers_reviewed": len(
                    barriers
                ),
                "tasks_reviewed": len(
                    tasks
                )
            },

            "confidence": 0.90,
            "source_field": (
                "detected_barriers_and_tasks"
            ),

            "raw_response": result,
            "recommendations": recommendations
        }