from llm.llm_client import LLMClient


class CaseAnalyzer:
    def __init__(self):
        self.llm = LLMClient()

    def analyze(self, patient_record):
        system_prompt = """
You are the Case Analyzer in a supervised hospital discharge-coordination
research prototype.

Your job is to analyze the supplied synthetic patient record and produce a
structured summary of the patient's clinical, discharge, and social context.

Rules:
1. Only use information explicitly present in the patient record.
2. Do not invent diagnoses, treatments, tasks, or barriers.
3. Do not recommend medication changes.
4. Do not authorize discharge.
5. Do not assign formal barrier IDs.
6. Identify potential discharge concerns, but leave final barrier classification
   to the deterministic Barrier Detector.
7. For each concern, include the exact source field from the patient record.
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
            "finding": "Clinical, discharge, and social context analyzed by LLM.",
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