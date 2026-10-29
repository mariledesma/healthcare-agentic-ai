from llm.llm_client import LLMClient


class CaseAnalyzer:
    def __init__(self):
        self.llm = LLMClient()

    def analyze(self, patient_record):
        system_prompt = """
You are the Case Analyzer in a supervised hospital discharge-coordination
research prototype.

Your role is to analyze the supplied synthetic patient record and produce a
structured summary of the patient's clinical, discharge, and social context.

You are an analytical component only. You do not make final clinical decisions,
assign formal discharge barrier IDs, or execute actions.

GENERAL RULES:
1. Use only information explicitly contained in the supplied patient record.
2. Do not invent diagnoses, medications, treatments, appointments, tasks,
   barriers, social circumstances, or clinical facts.
3. Do not prescribe medications or recommend medication changes.
4. Do not authorize or recommend final discharge.
5. Do not assign formal barrier IDs such as B-F01 or B-S07.
6. Do not assign formal task IDs.
7. Potential concerns may be identified, but formal barrier classification is
   performed later by the deterministic Barrier Detector.
8. Every potential concern must identify the source field or fields that
   directly support the concern.

SUMMARY RULES:
1. clinical_summary should summarize relevant diagnoses, medical stability,
   medications, laboratory information, and physical function when available.
2. discharge_summary should summarize discharge readiness information,
   education status, follow-up, transportation, documentation, and other
   discharge-related factors.
3. social_summary should summarize caregiver support, transportation,
   financial status, home safety, case management, and other social or
   logistical information when available.
4. Do not describe normal findings as problems.
5. Do not state that information is missing when an explicit status is given.

INFORMATION GAP RULES:
1. An information gap exists only when information is genuinely missing,
   unknown, null, undocumented, ambiguous, or unavailable.
2. Do not classify a known negative finding as an information gap.
3. An empty list represents no currently identified items unless the record
   explicitly states that the information is unknown.
4. Examples:
   - pending_labs = [] means no pending labs. This is not an information gap.
   - pending_imaging = [] means no pending imaging. This is not a gap.
   - pending_consults = [] means no pending consults. This is not a gap.
   - caregiver_status = "available" is known information.
   - followup_appointment_status = "scheduled" is known information.
   - transport_status = "arranged" is known information.
5. Explicit values such as complete, scheduled, available, safe, stable,
   independent, no_barrier, not_needed, and similar completed or normal
   statuses must not be listed as information gaps.
6. Do not restate normal findings inside information_gaps.
7. If there are no genuine information gaps, return an empty list.

POTENTIAL CONCERN RULES:
1. Identify only concerns that could reasonably interfere with discharge
   coordination.
2. Each concern must be grounded in specific evidence from the patient record.
3. Do not create a concern solely because a field exists.
4. Do not assign taxonomy IDs.
5. Assign a priority of high, medium, or low based on potential impact on the
   discharge workflow.

CROSS-FIELD REASONING:
1. Compare related fields when determining whether a potential discharge
   concern exists.
2. Two fields may individually appear acceptable but conflict when considered
   together.
3. Pay particular attention to relationships involving:
   - planned discharge timing and transportation timing
   - caregiver availability and discharge support needs
   - physical function and home safety
   - medication availability and medication requirements
   - follow-up status and discharge planning
4. Example:
   If transport_status is "arranged", but the transportation time conflicts
   with the planned discharge window, identify a transportation timing concern.
5. Describe the concern without assigning the formal barrier ID because the
   deterministic Barrier Detector performs that classification.
"""

        schema = {
            "type": "object",
            "properties": {
                "clinical_summary": {
                    "type": "string"
                },
                "discharge_summary": {
                    "type": "string"
                },
                "social_summary": {
                    "type": "string"
                },
                "potential_concerns": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "finding": {
                                "type": "string"
                            },
                            "supporting_evidence": {
                                "type": "string"
                            },
                            "source_field": {
                                "type": "string"
                            },
                            "priority": {
                                "type": "string",
                                "enum": [
                                    "high",
                                    "medium",
                                    "low"
                                ]
                            }
                        },
                        "required": [
                            "finding",
                            "supporting_evidence",
                            "source_field",
                            "priority"
                        ],
                        "additionalProperties": False
                    }
                },
                "information_gaps": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "clinical_summary",
                "discharge_summary",
                "social_summary",
                "potential_concerns",
                "information_gaps"
            ],
            "additionalProperties": False
        }

        result = self.llm.generate_json(
            system_prompt=system_prompt,
            user_data=patient_record,
            schema_name="case_analysis",
            schema=schema
        )

        return {
            "agent": "CaseAnalyzer",
            "status": "success",
            "llm": self.llm.get_metadata(),
            "finding": (
                "Clinical, discharge, and social context "
                "analyzed by LLM."
            ),
            "supporting_evidence": {
                "concern_count": len(
                    result["potential_concerns"]
                ),
                "information_gap_count": len(
                    result["information_gaps"]
                )
            },
            "confidence": 0.90,
            "source_field": "patient_record",
            "clinical_summary": result[
                "clinical_summary"
            ],
            "discharge_summary": result[
                "discharge_summary"
            ],
            "social_summary": result[
                "social_summary"
            ],
            "potential_concerns": result[
                "potential_concerns"
            ],
            "information_gaps": result[
                "information_gaps"
            ]
        }