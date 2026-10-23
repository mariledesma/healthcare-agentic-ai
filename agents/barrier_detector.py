class BarrierDetector:
    """
    Detect discharge barriers using deterministic rules.

    The Case Analyzer may identify possible concerns using the LLM,
    but this detector makes the final structured barrier classification.

    Barrier IDs use short, readable names instead of codes such as B-S07.
    """

    def __init__(self):
        self.name = "BarrierDetector"

    # ---------------------------------------------------------
    # Transportation timing helper
    # ---------------------------------------------------------

    def has_transport_timing_conflict(
        self,
        planned_discharge_window,
        transport_time
    ):
        """
        Prototype discharge windows:

        morning   = before 12:00
        afternoon = 12:00 through 16:59
        evening   = 17:00 or later
        """

        if not planned_discharge_window or not transport_time:
            return False

        try:
            hour = int(
                str(transport_time).split(":")[0]
            )
        except (ValueError, IndexError, AttributeError):
            return False

        window = str(
            planned_discharge_window
        ).strip().lower()

        if window == "morning":
            return hour >= 12

        if window == "afternoon":
            return hour < 12 or hour >= 17

        if window == "evening":
            return hour < 17

        return False

    # ---------------------------------------------------------
    # Main barrier detector
    # ---------------------------------------------------------

    def detect(
        self,
        patient_record,
        analysis_result=None
    ):
        """
        patient_record:
            Original structured patient JSON.

        analysis_result:
            Optional Case Analyzer output.

        The argument is accepted so this detector stays compatible
        with run_prototype.py. Formal barrier classification remains
        deterministic.
        """

        barriers = []

        def add_barrier(
            barrier_id,
            finding,
            evidence,
            source_field,
            priority="high"
        ):
            barriers.append(
                {
                    "barrier_id": barrier_id,
                    "finding": finding,
                    "evidence": evidence,
                    "confidence": 0.95,
                    "priority": priority,
                    "source_field": source_field
                }
            )

        # =====================================================
        # CLINICAL READINESS
        # =====================================================

        pending_labs = patient_record.get(
            "pending_labs",
            []
        )

        if pending_labs:
            add_barrier(
                "pending_results",
                "Pending laboratory results require review.",
                pending_labs,
                "pending_labs"
            )

        physical_function = patient_record.get(
            "physical_function"
        )

        if physical_function in [
            "needs_assistance",
            "limited",
            "dependent",
            "unsafe",
            "impaired"
        ]:
            add_barrier(
                "physical_support_needed",
                "Patient has physical or mobility needs that may affect discharge.",
                physical_function,
                "physical_function"
            )

        # =====================================================
        # MEDICATION READINESS
        # =====================================================

        med_reconciliation = patient_record.get(
            "medication_reconciliation_status"
        )

        if med_reconciliation in [
            "incomplete",
            "pending",
            "not_complete",
            "not_completed"
        ]:
            add_barrier(
                "med_reconciliation_missing",
                "Medication reconciliation is incomplete.",
                med_reconciliation,
                "medication_reconciliation_status"
            )

        med_education = patient_record.get(
            "medication_education_status"
        )

        if med_education in [
            "incomplete",
            "pending",
            "not_complete",
            "not_completed",
            "needed"
        ]:
            add_barrier(
                "med_education_missing",
                "Medication education is incomplete.",
                med_education,
                "medication_education_status"
            )

        med_availability = patient_record.get(
            "medication_availability"
        )

        if med_availability in [
            "not_available",
            "unavailable",
            "missing"
        ]:
            add_barrier(
                "med_unavailable",
                "Required discharge medication is not available.",
                med_availability,
                "medication_availability"
            )

        # =====================================================
        # PATIENT EDUCATION
        # =====================================================

        patient_education = patient_record.get(
            "patient_education_status"
        )

        if patient_education in [
            "incomplete",
            "pending",
            "not_complete",
            "not_completed",
            "needed"
        ]:
            add_barrier(
                "patient_education_missing",
                "Required patient education is incomplete.",
                patient_education,
                "patient_education_status"
            )

        diet_education = patient_record.get(
            "diet_education_status"
        )

        if diet_education in [
            "incomplete",
            "pending",
            "not_complete",
            "not_completed",
            "needed"
        ]:
            add_barrier(
                "diet_education_missing",
                "Diet or fluid education is incomplete.",
                diet_education,
                "diet_education_status"
            )

        mobility_education = patient_record.get(
            "mobility_device_education_status"
        )

        if mobility_education in [
            "incomplete",
            "pending",
            "not_complete",
            "not_completed",
            "needed"
        ]:
            add_barrier(
                "mobility_education_missing",
                "Mobility device education is incomplete.",
                mobility_education,
                "mobility_device_education_status"
            )

        device_education = patient_record.get(
            "medical_device_education_status"
        )

        if device_education in [
            "incomplete",
            "pending",
            "not_complete",
            "not_completed",
            "needed"
        ]:
            add_barrier(
                "device_education_missing",
                "Medical device education is incomplete.",
                device_education,
                "medical_device_education_status"
            )

        # =====================================================
        # FOLLOW-UP AND CARE COORDINATION
        # =====================================================

        followup_status = patient_record.get(
            "followup_status"
        )

        if followup_status in [
            "not_scheduled",
            "unscheduled",
            "missing",
            "pending"
        ]:
            add_barrier(
                "followup_missing",
                "Required follow-up has not been scheduled.",
                followup_status,
                "followup_status"
            )

        caregiver_status = patient_record.get(
            "caregiver_status"
        )

        if caregiver_status in [
            "unavailable",
            "not_available",
            "missing",
            "needed"
        ]:
            add_barrier(
                "caregiver_missing",
                "Required caregiver support is unavailable.",
                caregiver_status,
                "caregiver_status"
            )

        therapy_status = patient_record.get(
            "outpatient_therapy_status"
        )

        if therapy_status in [
            "not_arranged",
            "unscheduled",
            "missing",
            "pending"
        ]:
            add_barrier(
                "therapy_missing",
                "Required outpatient therapy has not been arranged.",
                therapy_status,
                "outpatient_therapy_status",
                priority="medium"
            )

        pcp_status = patient_record.get(
            "pcp_notification_status"
        )

        if pcp_status in [
            "not_notified",
            "not_complete",
            "incomplete",
            "pending",
            "missing"
        ]:
            add_barrier(
                "pcp_notification_missing",
                "Primary care provider notification is incomplete.",
                pcp_status,
                "pcp_notification_status",
                priority="medium"
            )

        # =====================================================
        # SOCIAL AND LOGISTICAL BARRIERS
        # =====================================================

        financial_status = patient_record.get(
            "financial_status"
        )

        if financial_status in [
            "barrier",
            "financial_barrier",
            "unable_to_afford",
            "needs_assistance",
            "concern"
        ]:
            add_barrier(
                "financial_barrier",
                "Financial concerns may affect the discharge plan.",
                financial_status,
                "financial_status",
                priority="medium"
            )

        # -----------------------------------------------------
        # Transportation
        # -----------------------------------------------------

        transport_status = patient_record.get(
            "transport_status"
        )

        transport_time = patient_record.get(
            "transport_time"
        )

        planned_discharge_window = patient_record.get(
            "planned_discharge_window"
        )

        if transport_status in [
            "not_arranged",
            "unavailable",
            "missing"
        ]:
            add_barrier(
                "transport_missing",
                "Transportation has not been arranged.",
                transport_status,
                "transport_status"
            )

        elif (
            transport_status == "arranged"
            and self.has_transport_timing_conflict(
                planned_discharge_window,
                transport_time
            )
        ):
            add_barrier(
                "transport_timing",
                "Transportation timing conflicts with the planned discharge window.",
                (
                    f"Discharge is planned for "
                    f"{planned_discharge_window}, but transportation "
                    f"is scheduled for {transport_time}."
                ),
                "planned_discharge_window + transport_time"
            )

        # -----------------------------------------------------
        # Home safety
        # -----------------------------------------------------

        home_safety = patient_record.get(
            "home_safety_status"
        )

        if home_safety in [
            "unsafe",
            "concern",
            "needs_assessment"
        ]:
            add_barrier(
                "home_safety_issue",
                "A home safety concern may affect discharge.",
                home_safety,
                "home_safety_status"
            )

        # -----------------------------------------------------
        # Case manager
        # -----------------------------------------------------

        case_manager_status = patient_record.get(
            "case_manager_status"
        )

        if case_manager_status in [
            "unavailable",
            "not_available",
            "missing"
        ]:
            add_barrier(
                "case_manager_missing",
                "Case management support is currently unavailable.",
                case_manager_status,
                "case_manager_status"
            )

        # =====================================================
        # DISCHARGE DOCUMENTATION
        # =====================================================

        discharge_summary_status = patient_record.get(
            "discharge_summary_status"
        )

        if discharge_summary_status in [
            "draft",
            "unsigned",
            "pending",
            "incomplete",
            "not_signed",
            "missing"
        ]:
            add_barrier(
                "paperwork_pending",
                "Discharge documentation is incomplete.",
                discharge_summary_status,
                "discharge_summary_status"
            )

        # =====================================================
        # FINAL STRUCTURED RESULT
        # =====================================================

        return {
            "agent": self.name,
            "status": "success",
            "finding": (
                f"{len(barriers)} discharge barrier(s) detected."
            ),
            "supporting_evidence": {
                "barrier_count": len(barriers),
                "barrier_ids": [
                    barrier["barrier_id"]
                    for barrier in barriers
                ]
            },
            "confidence": 0.95,
            "source_field": "patient_record",
            "barriers": barriers
        }