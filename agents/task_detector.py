class TaskDetector:
    def detect(self, patient_record, detected_barriers):
        tasks = []

        barrier_ids = {
            barrier["barrier_id"]
            for barrier in detected_barriers
        }

        def add_task(
            task_id,
            task_name,
            owner_role,
            resolves,
            source_field,
            priority="high"
        ):
            tasks.append({
                "task_id": task_id,
                "task_name": task_name,
                "owner_role": owner_role,
                "resolves_barriers": resolves,
                "priority": priority,
                "source_field": source_field
            })

        if "B-C01" in barrier_ids:
            add_task(
                "T-PH01",
                "Complete medication reconciliation",
                "Pharmacist",
                ["B-C01"],
                "medication_reconciliation_status"
            )

        if "B-C02" in barrier_ids or "B-C03" in barrier_ids:
            add_task(
                "T-MD02",
                "Review pending labs and imaging",
                "Physician",
                ["B-C02", "B-C03"],
                "pending_labs, pending_imaging"
            )

        if "B-C04" in barrier_ids:
            add_task(
                "T-MD03",
                "Complete required specialist consult",
                "Physician",
                ["B-C04"],
                "pending_consult"
            )

        if "B-C05" in barrier_ids:
            add_task(
                "T-RN06",
                "Mobility and functional assessment",
                "Nurse / PT",
                ["B-C05"],
                "physical_function_status"
            )

        if "B-C07" in barrier_ids:
            add_task(
                "T-MD04",
                "Assess and clear medical stability",
                "Physician",
                ["B-C07"],
                "medical_stability_status"
            )

        if "B-E01" in barrier_ids:
            add_task(
                "T-RN01",
                "Conduct medication education",
                "Nurse",
                ["B-E01"],
                "medication_education_status"
            )

        if "B-E02" in barrier_ids:
            add_task(
                "T-PH02",
                "Fill discharge prescriptions",
                "Pharmacist",
                ["B-E02"],
                "medication_availability_status"
            )

        if "B-E03" in barrier_ids:
            add_task(
                "T-RN02",
                "Conduct disease-specific patient education",
                "Nurse",
                ["B-E03"],
                "patient_education_status"
            )

        if "B-E04" in barrier_ids:
            add_task(
                "T-RN03",
                "Teach diet and fluid restrictions",
                "Nurse",
                ["B-E04"],
                "diet_education_status"
            )

        if "B-E05" in barrier_ids:
            add_task(
                "T-RN07",
                "Mobility device education",
                "Nurse",
                ["B-E05"],
                "mobile_device_education_status"
            )

        if "B-E06" in barrier_ids:
            add_task(
                "T-RN08",
                "Medical device education",
                "Nurse",
                ["B-E06"],
                "medical_device_education_status"
            )

        if "B-F01" in barrier_ids or "B-F02" in barrier_ids:
            add_task(
                "T-CM01",
                "Schedule follow-up appointment",
                "Case Manager",
                ["B-F01", "B-F02"],
                "followup_appointment_status"
            )

        if "B-F03" in barrier_ids:
            add_task(
                "T-CM02",
                "Confirm caregiver availability and brief caregiver",
                "Case Manager / SW",
                ["B-F03"],
                "caregiver_status"
            )

        if "B-F04" in barrier_ids:
            add_task(
                "T-CM03",
                "Arrange outpatient therapy referrals",
                "Case Manager",
                ["B-F04"],
                "outpatient_therapy_status",
                priority="medium"
            )

        if "B-F05" in barrier_ids:
            add_task(
                "T-CM08",
                "Notify primary care provider",
                "Case Manager",
                ["B-F05"],
                "pcp_notification_status",
                priority="medium"
            )

        if "B-S01" in barrier_ids:
            add_task(
                "T-CM07",
                "Connect patient to financial assistance",
                "Social Worker",
                ["B-S01"],
                "financial_status",
                priority="medium"
            )

        if "B-S02" in barrier_ids or "B-S07" in barrier_ids:
            add_task(
                "T-CM04",
                "Arrange patient transport",
                "Case Manager",
                ["B-S02", "B-S07"],
                "transport_status"
            )

        if "B-S03" in barrier_ids:
            add_task(
                "T-CM05",
                "Conduct home safety assessment",
                "Case Manager / SW",
                ["B-S03"],
                "home_safety_status"
            )

        if "B-S06" in barrier_ids:
            add_task(
                "T-MD01",
                "Complete and sign discharge summary",
                "Physician",
                ["B-S06"],
                "discharge_summary_status"
            )

        return {
            "agent": "TaskDetector",
            "status": "success",
            "finding": f"{len(tasks)} pending task(s) detected.",
            "supporting_evidence": {
                "task_count": len(tasks)
            },
            "confidence": 0.95,
            "source_field": "detected_barriers",
            "tasks": tasks
        }