class BarrierDetector:
    def detect(self, patient_record, analysis):
        barriers = []

        def add_barrier(
            barrier_id,
            finding,
            evidence,
            source_field,
            priority="high",
            confidence=0.95
        ):
            barriers.append({
                "barrier_id": barrier_id,
                "finding": finding,
                "supporting_evidence": evidence,
                "confidence": confidence,
                "priority": priority,
                "source_field": source_field
            })

        if patient_record.get("pending_labs"):
            add_barrier(
                "B-C02",
                "Lab or test results are pending.",
                patient_record["pending_labs"],
                "pending_labs"
            )

        if patient_record.get("physical_function_status") not in [
            None,
            "independent"
        ]:
            add_barrier(
                "B-C05",
                "Patient has functional or physical limitations.",
                patient_record.get("physical_function_status"),
                "physical_function_status"
            )

        if patient_record.get("medication_reconciliation_status") == "incomplete":
            add_barrier(
                "B-C01",
                "Medication reconciliation is incomplete.",
                patient_record.get("medication_reconciliation_status"),
                "medication_reconciliation_status"
            )

        if patient_record.get("medication_education_status") == "incomplete":
            add_barrier(
                "B-E01",
                "Medication education is incomplete.",
                patient_record.get("medication_education_status"),
                "medication_education_status"
            )

        if patient_record.get("medication_availability_status") == "not_available":
            add_barrier(
                "B-E02",
                "Discharge medication is not available.",
                patient_record.get("medication_availability_status"),
                "medication_availability_status"
            )

        if patient_record.get("patient_education_status") == "incomplete":
            add_barrier(
                "B-E03",
                "Patient education is incomplete.",
                patient_record.get("patient_education_status"),
                "patient_education_status"
            )

        if patient_record.get("diet_education_status") == "incomplete":
            add_barrier(
                "B-E04",
                "Diet restrictions have not been fully taught.",
                patient_record.get("diet_education_status"),
                "diet_education_status"
            )

        if patient_record.get("mobile_device_education_status") == "incomplete":
            add_barrier(
                "B-E05",
                "Mobility device education is incomplete.",
                patient_record.get("mobile_device_education_status"),
                "mobile_device_education_status"
            )

        if patient_record.get("medical_device_education_status") == "incomplete":
            add_barrier(
                "B-E06",
                "Medical device education is incomplete.",
                patient_record.get("medical_device_education_status"),
                "medical_device_education_status"
            )

        if patient_record.get("followup_appointment_status") == "not_scheduled":
            add_barrier(
                "B-F01",
                "Follow-up appointment has not been scheduled.",
                patient_record.get("followup_appointment_status"),
                "followup_appointment_status"
            )

        if patient_record.get("caregiver_status") == "unavailable":
            add_barrier(
                "B-F03",
                "Reliable caregiver support is unavailable.",
                patient_record.get("caregiver_status"),
                "caregiver_status"
            )

        if patient_record.get("outpatient_therapy_status") == "not_arranged":
            add_barrier(
                "B-F04",
                "Required outpatient therapy has not been arranged.",
                patient_record.get("outpatient_therapy_status"),
                "outpatient_therapy_status",
                priority="medium"
            )

        if patient_record.get("pcp_notification_status") in [
            "not_complete",
            "not_notified"
        ]:
            add_barrier(
                "B-F05",
                "Primary care provider has not been notified.",
                patient_record.get("pcp_notification_status"),
                "pcp_notification_status",
                priority="medium"
            )

        if patient_record.get("financial_status") in [
            "financial_barrier",
            "unable_to_afford",
            "concern"
        ]:
            add_barrier(
                "B-S01",
                "Financial constraints may affect safe discharge.",
                patient_record.get("financial_status"),
                "financial_status"
            )

        if patient_record.get("transport_status") == "not_arranged":
            add_barrier(
                "B-S02",
                "Transportation home has not been arranged.",
                patient_record.get("transport_status"),
                "transport_status"
            )

        home_safety = patient_record.get("home_safety_status")

        if home_safety not in [None, "safe"]:
            add_barrier(
                "B-S03",
                "Home safety concerns may prevent safe discharge.",
                home_safety,
                "home_safety_status"
            )

        if patient_record.get("case_manager_status") == "unavailable":
            add_barrier(
                "B-S05",
                "Case manager is unavailable.",
                patient_record.get("case_manager_status"),
                "case_manager_status"
            )

        if patient_record.get("discharge_summary_status") in [
            "draft",
            "unsigned",
            "pending"
        ]:
            add_barrier(
                "B-S06",
                "Discharge paperwork is incomplete.",
                patient_record.get("discharge_summary_status"),
                "discharge_summary_status"
            )

        return {
            "agent": "BarrierDetector",
            "status": "success",
            "finding": f"{len(barriers)} discharge barrier(s) detected.",
            "supporting_evidence": {
                "barrier_count": len(barriers)
            },
            "confidence": 0.95,
            "source_field": "patient_record",
            "barriers": barriers
        }