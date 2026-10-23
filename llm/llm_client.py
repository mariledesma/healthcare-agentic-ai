import json
import os

from dotenv import load_dotenv
from ollama import Client


load_dotenv()


class LLMClient:
    def __init__(self):
        self.provider = os.getenv(
            "LLM_PROVIDER",
            "ollama"
        )

        self.model = os.getenv(
            "OLLAMA_MODEL",
            "medgemma1.5:4b"
        )

        self.host = os.getenv(
            "OLLAMA_HOST",
            "http://localhost:11434"
        )

        self.client = Client(
            host=self.host
        )

    def generate_json(
        self,
        system_prompt,
        user_data,
        schema_name,
        schema
    ):
        user_prompt = (
            f"Schema name: {schema_name}\n\n"
            "Analyze the following input data.\n\n"
            "Use only information supported by the supplied data.\n\n"
            "INPUT DATA:\n"
            f"{json.dumps(user_data, indent=2)}"
        )

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            format=schema,
            options={
                "temperature": 0
            }
        )

        content = response.message.content

        if not content:
            raise ValueError(
                "MedGemma returned an empty response."
            )

        try:
            return json.loads(content)

        except json.JSONDecodeError as error:
            raise ValueError(
                "MedGemma did not return valid JSON."
            ) from error

    def get_metadata(self):
        return {
            "provider": self.provider,
            "model": self.model
        }