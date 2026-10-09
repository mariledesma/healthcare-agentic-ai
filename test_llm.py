from llm.llm_client import LLMClient


client = LLMClient()

result = client.generate_json(
    system_prompt=(
        "You are testing an API connection. "
        "Return the requested structured result."
    ),
    user_data={
        "message": "Healthcare Agentic AI connection test"
    },
    schema_name="connection_test",
    schema={
        "type": "object",
        "properties": {
            "status": {
                "type": "string"
            }
        },
        "required": [
            "status"
        ],
        "additionalProperties": False
    }
)

print(result)