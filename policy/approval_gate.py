class ApprovalGate:
    def __init__(self):
        self.requires_approval = {
            "Complete and sign discharge summary",
            "Assess and clear medical stability",
            "Complete medication reconciliation",
            "Fill discharge prescriptions",
            "Review pending labs and imaging",
            "Complete required specialist consult"
        }

    def evaluate(self, recommendation):
        action = recommendation.get("action")

        if action in self.requires_approval:
            return {
                "approval_status": "requires_human_approval",
                "requires_human_approval": True,
                "action": action,
                "reason": "Clinical or discharge-sensitive action requires human review."
            }

        return {
            "approval_status": "auto_safe",
            "requires_human_approval": False,
            "action": action,
            "reason": "Coordination action may be proposed without clinical execution."
        }