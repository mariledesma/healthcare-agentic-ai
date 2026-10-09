class PolicyEngine:
    def __init__(self):
        self.allowed_actions = {
            "Schedule follow-up appointment",
            "Arrange patient transport",
            "Confirm caregiver availability and brief caregiver",
            "Arrange outpatient therapy referrals",
            "Conduct home safety assessment",
            "Connect patient to financial assistance",
            "Notify primary care provider",
            "Conduct medication education",
            "Conduct disease-specific patient education",
            "Teach diet and fluid restrictions",
            "Mobility and functional assessment",
            "Mobility device education",
            "Medical device education",
            "Review pending labs and imaging",
            "Complete required specialist consult",
            "Assess and clear medical stability",
            "Complete medication reconciliation",
            "Fill discharge prescriptions"
        }

        self.forbidden_actions = {
            "place_discharge_order",
            "modify_medication_list",
            "send_prescription",
            "sign_discharge_summary",
            "authorize_home_oxygen_order",
            "communicate_med_change_to_patient_directly"
        }

    def evaluate(self, recommendation):
        action = recommendation.get("action")

        if action in self.forbidden_actions:
            return {
                "policy_status": "forbidden",
                "action": action,
                "reason": "Action is prohibited by the governance policy."
            }

        if action in self.allowed_actions:
            return {
                "policy_status": "allowed",
                "action": action,
                "reason": "Action is permitted by the governance policy."
            }

        return {
            "policy_status": "review_required",
            "action": action,
            "reason": "Action is not explicitly listed and requires review."
        }