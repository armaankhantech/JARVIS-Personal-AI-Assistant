import os
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

project_dir = Path(__file__).resolve().parent.parent
load_dotenv(project_dir / ".env")

api_key = os.getenv("ELEVENLABS_API_KEY")
voice_id = "fhxKpNzeg3vGTIlNcCOB"

if not api_key:
    print("ERROR: ELEVENLABS_API_KEY was not found in .env")
    raise SystemExit(1)

try:
    print("Testing The Tech Professor voice...")
    client = ElevenLabs(api_key=api_key)

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text="Hello, this is Jarvis. Testing The Tech Professor voice.",
        model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128",
    )

    output_file = project_dir / "voice" / "tech_professor_test.mp3"
    output_file.write_bytes(b"".join(audio))
    print("SUCCESS: Audio generated at", output_file)

    import pygame
    pygame.mixer.init()
    pygame.mixer.music.load(str(output_file))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)
    pygame.mixer.quit()
    print("Playback finished.")

except Exception as e:
    print("TEST FAILED:", str(e)[:1200])
