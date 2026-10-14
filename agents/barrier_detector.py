class BarrierDetector:
    def has_transport_timing_conflict(
        self,
        planned_discharge_window,
        transport_time
    ):
        if not planned_discharge_window or not transport_time:
            return False

        try:
            hour = int(
                transport_time.split(":")[0]
            )
        except (ValueError, AttributeError):
            return False

        window = planned_discharge_window.lower()

        # Simple prototype time windows
        if window == "morning":
            return hour >= 12

        if window == "afternoon":
            return hour < 12 or hour >= 17

        if window == "evening":
            return hour < 17

        return False


    def detect(
        self,
        patient_record,
        analysis_result=None
    ):
        barriers = []

        def add_barrier(
            barrier_id,
            finding,
            evidence,
            source_field,
            priority="high"
        ):
            barriers.append({
                "barrier_id": barrier_id,
                "finding": finding,
                "evidence": evidence,
                "confidence": 0.95,
                "priority": priority,
                "source_field": source_field
            })

        # -------------------------------------------------
        # Clinical / Medical Barriers
        # -------------------------------------------------

        pending_labs = patient_record.get(
            "pending_labs",
            []
        )

        if pending_labs:
            add_barrier(
                "B-C02",
                "Pending laboratory results require review.",
                pending_labs,
                "pending_labs"
            )

        physical_function_status = patient_record.get(
            "physical_function_status"
        )

        if (
            physical_function_status
            and physical_function_status
            not in [
                "independent",
                "none"
            ]
        ):
            add_barrier(
                "B-C05",
                "Patient has a physical function limitation.",
                physical_function_status,
                "physical_function_status"
            )

        # -------------------------------------------------
        # Medication / Education Barriers
        # -------------------------------------------------

        medication_reconciliation_status = (
            patient_record.get(
                "medication_reconciliation_status"
            )
        )

        if medication_reconciliation_status == "incomplete":
            add_barrier(
                "B-C01",
                "Medication reconciliation is incomplete.",
                medication_reconciliation_status,
                "medication_reconciliation_status"
            )

        medication_education_status = patient_record.get(
            "medication_education_status"
        )

        if medication_education_status == "incomplete":
            add_barrier(
                "B-E01",
                "Medication education is incomplete.",
                medication_education_status,
                "medication_education_status"
            )

        medication_availability = patient_record.get(
            "medication_availability"
        )

        if medication_availability == "not_available":
            add_barrier(
                "B-E02",
                "Discharge medication is not available.",
                medication_availability,
                "medication_availability"
            )

        patient_education_status = patient_record.get(
            "patient_education_status"
        )

        if patient_education_status == "incomplete":
            add_barrier(
                "B-E03",
                "Required patient education is incomplete.",
                patient_education_status,
                "patient_education_status"
            )

        diet_education_status = patient_record.get(
            "diet_education_status"
        )

        if diet_education_status == "incomplete":
            add_barrier(
                "B-E04",
                "Diet education is incomplete.",
                diet_education_status,
                "diet_education_status"
            )

        mobility_device_education_status = (
            patient_record.get(
                "mobility_device_education_status"
            )
        )

        if mobility_device_education_status == "incomplete":
            add_barrier(
                "B-E05",
                "Mobility device education is incomplete.",
                mobility_device_education_status,
                "mobility_device_education_status"
            )

        medical_device_education_status = (
            patient_record.get(
                "medical_device_education_status"
            )
        )

        if medical_device_education_status == "incomplete":
            add_barrier(
                "B-E06",
                "Medical device education is incomplete.",
                medical_device_education_status,
                "medical_device_education_status"
            )

        # -------------------------------------------------
        # Follow-Up / Care Coordination Barriers
        # -------------------------------------------------

        followup_status = patient_record.get(
            "followup_appointment_status"
        )

        if followup_status == "not_scheduled":
            add_barrier(
                "B-F01",
                "Follow-up appointment has not been scheduled.",
                followup_status,
                "followup_appointment_status"
            )

        caregiver_status = patient_record.get(
            "caregiver_status"
        )

        if caregiver_status == "unavailable":
            add_barrier(
                "B-F03",
                "Required caregiver support is unavailable.",
                caregiver_status,
                "caregiver_status"
            )

        outpatient_therapy_status = patient_record.get(
            "outpatient_therapy_status"
        )

        if outpatient_therapy_status == "not_arranged":
            add_barrier(
                "B-F04",
                "Required outpatient therapy has not been arranged.",
                outpatient_therapy_status,
                "outpatient_therapy_status",
                priority="medium"
            )

        pcp_notification_status = patient_record.get(
            "pcp_notification_status"
        )

        if pcp_notification_status in [
            "not_complete",
            "not_notified"
        ]:
            add_barrier(
                "B-F05",
                "Primary care provider notification is incomplete.",
                pcp_notification_status,
                "pcp_notification_status",
                priority="medium"
            )

        # -------------------------------------------------
        # Social / Logistical / Workflow Barriers
        # -------------------------------------------------

        financial_status = patient_record.get(
            "financial_status"
        )

        if financial_status in [
            "barrier",
            "financial_barrier",
            "unable_to_afford",
            "needs_assistance"
        ]:
            add_barrier(
                "B-S01",
                "Financial barrier may affect discharge.",
                financial_status,
                "financial_status"
            )

        # -------------------------------------------------
        # Transportation
        # -------------------------------------------------

        transport_status = patient_record.get(
            "transport_status"
        )

        transport_time = patient_record.get(
            "transport_time"
        )

        planned_discharge_window = patient_record.get(
            "planned_discharge_window"
        )

        # Transportation does not exist
        if transport_status == "not_arranged":
            add_barrier(
                "B-S02",
                "Transportation home has not been arranged.",
                transport_status,
                "transport_status"
            )

        # Transportation exists, but conflicts with discharge time
        elif (
            transport_status == "arranged"
            and self.has_transport_timing_conflict(
                planned_discharge_window,
                transport_time
            )
        ):
            add_barrier(
                "B-S07",
                (
                    "Transportation timing conflicts with "
                    "the planned discharge window."
                ),
                (
                    f"Discharge is planned for "
                    f"{planned_discharge_window}, but "
                    f"transportation is scheduled for "
                    f"{transport_time}."
                ),
                (
                    "planned_discharge_window + "
                    "transport_time"
                )
            )

        home_safety_status = patient_record.get(
            "home_safety_status"
        )

        if (
            home_safety_status
            and home_safety_status
            not in [
                "safe",
                "none"
            ]
        ):
            add_barrier(
                "B-S03",
                "A home safety concern may affect discharge.",
                home_safety_status,
                "home_safety_status"
            )

        case_manager_status = patient_record.get(
            "case_manager_status"
        )

        if case_manager_status == "unavailable":
            add_barrier(
                "B-S05",
                "Case manager is currently unavailable.",
                case_manager_status,
                "case_manager_status"
            )

        discharge_summary_status = patient_record.get(
            "discharge_summary_status"
        )

        if discharge_summary_status in [
            "draft",
            "unsigned",
            "pending"
        ]:
            add_barrier(
                "B-S06",
                "Discharge documentation is incomplete.",
                discharge_summary_status,
                "discharge_summary_status"
            )

        # -------------------------------------------------
        # Final structured response
        # -------------------------------------------------

        return {
            "agent": "BarrierDetector",
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