class TaskDetector:
    """
    Convert detected discharge barriers into actionable tasks.

    Task IDs use short, plain-English names instead of codes
    such as T-CM04.
    """

    def __init__(self):
        self.name = "TaskDetector"

    def detect(
        self,
        patient_record,
        detected_barriers
    ):
        tasks = []

        barrier_ids = {
            barrier["barrier_id"]
            for barrier in detected_barriers
        }

        def add_task(
            task_id,
            task_name,
            owner_role,
            resolves_barriers,
            source_field,
            priority="high"
        ):
            tasks.append(
                {
                    "task_id": task_id,
                    "task_name": task_name,
                    "owner_role": owner_role,
                    "resolves_barriers": resolves_barriers,
                    "priority": priority,
                    "source_field": source_field
                }
            )

        # =====================================================
        # MEDICATION TASKS
        # =====================================================

        if "med_reconciliation_missing" in barrier_ids:
            add_task(
                "reconcile_meds",
                "Complete medication reconciliation",
                "Pharmacist",
                ["med_reconciliation_missing"],
                "medication_reconciliation_status"
            )

        if "med_education_missing" in barrier_ids:
            add_task(
                "teach_meds",
                "Conduct medication education",
                "Nurse",
                ["med_education_missing"],
                "medication_education_status"
            )

        if "med_unavailable" in barrier_ids:
            add_task(
                "fill_meds",
                "Fill discharge prescriptions",
                "Pharmacist",
                ["med_unavailable"],
                "medication_availability"
            )

        # =====================================================
        # CLINICAL TASKS
        # =====================================================

        if "pending_results" in barrier_ids:
            add_task(
                "review_results",
                "Review pending laboratory results",
                "Physician",
                ["pending_results"],
                "pending_labs"
            )

        if "physical_support_needed" in barrier_ids:
            add_task(
                "assess_function",
                "Complete mobility and functional assessment",
                "Nurse / PT",
                ["physical_support_needed"],
                "physical_function"
            )

        # =====================================================
        # EDUCATION TASKS
        # =====================================================

        if "patient_education_missing" in barrier_ids:
            add_task(
                "teach_condition",
                "Conduct disease-specific patient education",
                "Nurse",
                ["patient_education_missing"],
                "patient_education_status"
            )

        if "diet_education_missing" in barrier_ids:
            add_task(
                "teach_diet",
                "Teach diet and fluid restrictions",
                "Nurse",
                ["diet_education_missing"],
                "diet_education_status"
            )

        if "mobility_education_missing" in barrier_ids:
            add_task(
                "teach_mobility_device",
                "Complete mobility device education",
                "Nurse",
                ["mobility_education_missing"],
                "mobility_device_education_status"
            )

        if "device_education_missing" in barrier_ids:
            add_task(
                "teach_device",
                "Complete medical device education",
                "Nurse",
                ["device_education_missing"],
                "medical_device_education_status"
            )

        # =====================================================
        # FOLLOW-UP AND CARE COORDINATION
        # =====================================================

        if "followup_missing" in barrier_ids:
            add_task(
                "schedule_followup",
                "Schedule follow-up appointment",
                "Case Manager",
                ["followup_missing"],
                "followup_status"
            )

        if "caregiver_missing" in barrier_ids:
            add_task(
                "confirm_caregiver",
                "Confirm caregiver availability and support",
                "Case Manager / SW",
                ["caregiver_missing"],
                "caregiver_status"
            )

        if "therapy_missing" in barrier_ids:
            add_task(
                "arrange_therapy",
                "Arrange outpatient therapy referrals",
                "Case Manager",
                ["therapy_missing"],
                "outpatient_therapy_status",
                priority="medium"
            )

        if "pcp_notification_missing" in barrier_ids:
            add_task(
                "notify_pcp",
                "Notify primary care provider",
                "Case Manager",
                ["pcp_notification_missing"],
                "pcp_notification_status",
                priority="medium"
            )

        # =====================================================
        # SOCIAL AND LOGISTICAL TASKS
        # =====================================================

        if "financial_barrier" in barrier_ids:
            add_task(
                "address_finances",
                "Connect patient to financial assistance",
                "Social Worker",
                ["financial_barrier"],
                "financial_status",
                priority="medium"
            )

        # -----------------------------------------------------
        # Transportation
        # -----------------------------------------------------

        transport_barriers = [
            barrier_id
            for barrier_id in [
                "transport_missing",
                "transport_timing"
            ]
            if barrier_id in barrier_ids
        ]

        if transport_barriers:

            if "transport_timing" in transport_barriers:
                source_field = (
                    "planned_discharge_window + transport_time"
                )
            else:
                source_field = "transport_status"

            add_task(
                "arrange_transport",
                "Arrange patient transport",
                "Case Manager",
                transport_barriers,
                source_field
            )

        # -----------------------------------------------------
        # Home safety
        # -----------------------------------------------------

        if "home_safety_issue" in barrier_ids:
            add_task(
                "check_home_safety",
                "Conduct home safety assessment",
                "Case Manager / SW",
                ["home_safety_issue"],
                "home_safety_status"
            )

        # =====================================================
        # DOCUMENTATION TASKS
        # =====================================================

        if "paperwork_pending" in barrier_ids:
            add_task(
                "sign_summary",
                "Complete and sign discharge summary",
                "Physician",
                ["paperwork_pending"],
                "discharge_summary_status"
            )

        # =====================================================
        # FINAL STRUCTURED RESULT
        # =====================================================

        return {
            "agent": self.name,
            "status": "success",
            "finding": (
                f"{len(tasks)} pending task(s) detected."
            ),
            "supporting_evidence": {
                "task_count": len(tasks),
                "task_ids": [
                    task["task_id"]
                    for task in tasks
                ]
            },
            "confidence": 0.95,
            "source_field": "detected_barriers",
            "tasks": tasks
        }