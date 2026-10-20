import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

DEVICE = 1
SAMPLE_RATE = 16000
DURATION = 8

print("Loading Whisper small.en...")
model = WhisperModel("small.en", device="cpu", compute_type="int8")

print("Speak clearly now for 8 seconds.")
print("Say: Jarvis, open Notepad.")

audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
    device=DEVICE,
)
sd.wait()

audio = np.squeeze(audio)
print("Recording peak level:", round(float(np.max(np.abs(audio))), 3))
print("Transcribing...")
segments, info = model.transcribe(
    audio,
    language="en",
    vad_filter=False,
    beam_size=5,
)
result = " ".join(s.text.strip() for s in segments).strip()
print("Recognized speech:", result or "[No speech detected]")
