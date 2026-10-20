
import base64
import os
import time

from groq import Groq
from google import genai
from openai import OpenAI
from ollama import chat

from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    OPENROUTER_API_KEY,
    GROQ_MODEL,
    GEMINI_MODEL,
    OPENROUTER_MODEL,
    OLLAMA_MODEL,
)


class ModelRouter:
    def __init__(self):
        gateway_key = os.getenv("FREELLMAPI_API_KEY", "").strip()
        gateway_url = os.getenv(
            "FREELLMAPI_BASE_URL",
            "http://127.0.0.1:31415/v1",
        ).strip()

        self.freellmapi = None
        if gateway_key:
            self.freellmapi = OpenAI(
                api_key=gateway_key,
                base_url=gateway_url,
                timeout=12.0,
                max_retries=0,
            )

        self.groq = Groq(
            api_key=GROQ_API_KEY,
            timeout=20.0,
            max_retries=0,
        )

        self.gemini = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"timeout": 20000},
        )

        self.openrouter = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            timeout=10.0,
            max_retries=0,
        )

    @staticmethod
    def _require_text(response, provider):
        if not isinstance(response, str) or not response.strip():
            raise RuntimeError(f"{provider} returned an empty response.")
        return response.strip()

    def ask_freellmapi(self, prompt):
        if self.freellmapi is None:
            raise RuntimeError("FreeLLMAPI key is not configured.")

        response = self.freellmapi.chat.completions.create(
            model="auto:default",
            messages=[{"role": "user", "content": prompt}],
        )
        return self._require_text(
            response.choices[0].message.content,
            "FreeLLMAPI",
        )

    def ask_groq(self, prompt):
        response = self.groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._require_text(
            response.choices[0].message.content,
            "Groq",
        )

    def ask_gemini(self, prompt):
        chat_session = self.gemini.chats.create(model=GEMINI_MODEL)
        response = chat_session.send_message(message=prompt)
        return self._require_text(response.text, "Gemini")

    def ask_openrouter(self, prompt):
        response = self.openrouter.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._require_text(
            response.choices[0].message.content,
            "OpenRouter",
        )

    def ask_ollama(self, prompt):
        response = chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._require_text(
            response["message"]["content"],
            "Local Ollama",
        )

    def analyze_image(self, image_path, prompt):
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(
                image_file.read()
            ).decode("utf-8")

        image_url = f"data:image/png;base64,{image_data}"

        response = self.groq.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            reasoning_effort="none",
            temperature=0,
            max_completion_tokens=100,
        )

        return self._require_text(
            response.choices[0].message.content,
            "Groq vision",
        )

    def ask(self, prompt):
        providers = [
            ("FreeLLMAPI", self.ask_freellmapi),
            ("Groq", self.ask_groq),
            ("OpenRouter", self.ask_openrouter),
            ("Gemini", self.ask_gemini),
            ("Local Ollama", self.ask_ollama),
        ]

        failures = []

        for provider_name, provider_function in providers:
            started = time.perf_counter()
            print(f"\n[AI] Trying {provider_name}...")

            try:
                response = provider_function(prompt)
                elapsed = time.perf_counter() - started

                print(
                    f"[AI] {provider_name} succeeded "
                    f"in {elapsed:.2f}s."
                )
                return response

            except Exception as error:
                elapsed = time.perf_counter() - started
                message = f"{type(error).__name__}: {error}"
                failures.append(provider_name)

                print(
                    f"[AI] {provider_name} failed after "
                    f"{elapsed:.2f}s: {message}"
                )

        print("[AI] All providers failed: " + ", ".join(failures))
        return (
            "Sorry Armaan, all AI providers are currently unavailable. "
            "Check the provider error messages in the terminal."
        )
