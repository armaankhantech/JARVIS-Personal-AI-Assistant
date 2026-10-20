import base64
import time

from dotenv import load_dotenv
from groq import Groq
import os
import pyautogui

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

print("Taking screenshot...")
screenshot = pyautogui.screenshot()

image_path = "data/test_vision.png"
os.makedirs("data", exist_ok=True)
screenshot.save(image_path)

with open(image_path, "rb") as image_file:
    image_data = base64.b64encode(image_file.read()).decode("utf-8")

image_url = f"data:image/png;base64,{image_data}"

prompt = """
Find the YouTube search box in this screenshot.

Return ONLY JSON:

{
    "found": true,
    "x": 123,
    "y": 456
}

If it is not visible:

{
    "found": false,
    "x": null,
    "y": null
}

x and y must be the approximate CENTER of the search box.
"""

print("Sending screenshot to Groq Vision...")
start = time.perf_counter()

response = client.chat.completions.create(
    model="qwen/qwen3.8-27b",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                    },
                },
            ],
        }
    ],
    reasoning_effort="none",
    response_format={
        "type": "json_object"
    },
    temperature=0,
    max_completion_tokens=100,
)

elapsed = time.perf_counter() - start

print("\n========== RESULT ==========")
print(response.choices[0].message.content)
print(f"\nTime: {elapsed:.2f} seconds")
print("============================")