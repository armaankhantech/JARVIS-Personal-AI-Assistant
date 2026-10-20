import os

from dotenv import load_dotenv
from groq import Groq
from google import genai
from openai import OpenAI
from ollama import chat


# Load .env
load_dotenv()


def test_groq():
    print("\n" + "=" * 50)
    print("TEST 1: GROQ - GPT-OSS 120B")
    print("=" * 50)

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: GROQ WORKS"
            }
        ],
    )

    print(response.choices[0].message.content)


def test_gemini():
    print("\n" + "=" * 50)
    print("TEST 2: GEMINI - 3.6 FLASH")
    print("=" * 50)

    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY")
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Reply with exactly: GEMINI WORKS",
    )

    print(response.text)


def test_openrouter():
    print("\n" + "=" * 50)
    print("TEST 3: OPENROUTER - FREE ROUTER")
    print("=" * 50)

    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )

    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: OPENROUTER WORKS"
            }
        ],
    )

    print(response.choices[0].message.content)


def test_ollama():
    print("\n" + "=" * 50)
    print("TEST 4: OLLAMA - LLAMA 3.2 3B")
    print("=" * 50)

    response = chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: OLLAMA WORKS"
            }
        ],
    )

    print(response["message"]["content"])


if __name__ == "__main__":

    test_groq()
    test_gemini()
    test_openrouter()
    test_ollama()

    print("\n" + "=" * 50)
    print("ALL MODEL TESTS FINISHED")
    print("=" * 50)