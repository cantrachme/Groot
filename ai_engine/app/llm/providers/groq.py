import os

from groq import Groq

from ..provider import LLMProvider


class GroqProvider(LLMProvider):
    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        self.client = Groq(api_key=api_key)

    def generate(self, system_prompt: str, user_message: str) -> str:
        response = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        return response.choices[0].message.content or ""
