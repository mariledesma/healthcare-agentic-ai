class PolicyEngine:
    """
    Deterministic governance layer.

    The Policy Engine decides whether a proposed task is allowed
    to continue through the supervised discharge workflow.

    It uses stable task IDs instead of matching English sentences.
    """

    def __init__(self):

        # Tasks the AI may RECOMMEND.
        #
        # This does not mean the AI is allowed to execute them.
        self.allowed_tasks = {
            "schedule_followup",
            "arrange_transport",
            "confirm_caregiver",
            "arrange_therapy",
            "check_home_safety",
            "address_finances",
            "notify_pcp",

            "teach_meds",
            "teach_condition",
            "teach_diet",
            "teach_mobility_device",
            "teach_device",

            "assess_function",
            "review_results",

            "reconcile_meds",
            "fill_meds",
            "sign_summary"
        }

        # These represent actions the AI system must never
        # autonomously execute.
        self.forbidden_operations = {
            "place_discharge_order",
            "modify_medication_list",
            "send_prescription",
            "sign_discharge_summary",
            "authorize_home_oxygen_order",
            "communicate_med_change_to_patient_directly"
        }

    def evaluate(self, recommendation):

        task_id = recommendation.get(
            "task_id"
        )

        action = recommendation.get(
            "action"
        )

        requested_operation = (
            recommendation.get(
                "requested_operation"
            )
        )

        # -------------------------------------------------
        # Explicitly forbidden execution
        # -------------------------------------------------

        if (
            requested_operation
            in self.forbidden_operations
        ):
            return {
                "policy_status": "forbidden",
                "task_id": task_id,
                "action": action,
                "reason": (
                    "The requested operation is "
                    "prohibited by governance policy."
                )
            }

        # -------------------------------------------------
        # Recognized recommendation
        # -------------------------------------------------

        if task_id in self.allowed_tasks:
            return {
                "policy_status": "allowed",
                "task_id": task_id,
                "action": action,
                "reason": (
                    "The recommendation is permitted "
                    "to continue through the supervised "
                    "workflow."
                )
            }

        # -------------------------------------------------
        # Unknown task
        # -------------------------------------------------

        return {
            "policy_status": "review_required",
            "task_id": task_id,
            "action": action,
            "reason": (
                "This task is not explicitly defined "
                "in the governance policy."
            )
        }