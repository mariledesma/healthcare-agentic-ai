import json
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


class LLMClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY was not found. Add it to the .env file."
            )

        self.provider = os.getenv(
            "LLM_PROVIDER",
            "groq"
        )

        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b"
        )

        self.client = Groq(
            api_key=api_key
        )

    def generate_json(
        self,
        system_prompt,
        user_data,
        schema_name,
        schema
    ):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        user_data,
                        indent=2
                    )
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema
                }
            }
        )

        content = response.choices[0].message.content

        return json.loads(content)

    def get_metadata(self):
        return {
            "provider": self.provider,
            "model": self.model
        }