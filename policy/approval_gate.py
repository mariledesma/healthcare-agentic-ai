from policy.policy_engine import PolicyEngine

class ApprovalGate:
    """
    Determines whether a permitted recommendation can remain
    an informational/coordination recommendation or must be
    reviewed by a human.

    Clinical and discharge-sensitive tasks require human approval.
    """

    def __init__(self):

        self.requires_approval = {
            "reconcile_meds",
            "fill_meds",
            "review_results",
            "sign_summary",
            "review_imaging_result",
            "review_consult_recommendations",
            "request_clinical_reassessment"
        }

    def evaluate(self, recommendation):
        if not isinstance(recommendation, dict):
            return {"approval_status": "requires_human_approval", "requires_human_approval": True,
                    "task_id": None, "action": None, "reason": "Malformed recommendation requires review."}

        task_id = recommendation.get(
            "task_id"
        )

        action = recommendation.get(
            "action"
        )

        policy = PolicyEngine().evaluate(recommendation)
        if policy['policy_status'] != 'allowed':
            return {
                'approval_status': 'blocked' if policy['policy_status'] == 'forbidden' else 'requires_human_approval',
                'requires_human_approval': True,
                'task_id': task_id, 'action': action, 'reason': policy['reason']
            }

        if task_id in self.requires_approval:
            return {
                "approval_status": (
                    "requires_human_approval"
                ),
                "requires_human_approval": True,
                "task_id": task_id,
                "action": action,
                "reason": (
                    "This recommendation involves "
                    "clinical or discharge-sensitive "
                    "work and requires human review."
                )
            }

        return {
            "approval_status": "auto_safe",
            "requires_human_approval": False,
            "task_id": task_id,
            "action": action,
            "reason": (
                "This is a coordination or educational "
                "recommendation and does not require "
                "clinical approval."
            )
        }