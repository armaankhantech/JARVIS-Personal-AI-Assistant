"""Fast Edge TTS with offline Piper fallback.

Edge-generated audio is played directly; FFmpeg loudness normalization was removed
because it added processing latency and Edge output is already normalized adequately.
"""
import asyncio
import os
import socket
import tempfile
import threading
import time
import wave
from pathlib import Path

import pygame
from dotenv import load_dotenv
from piper import PiperVoice

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
MODEL_PATH = BASE_DIR / "models" / "en_GB-alan-medium.onnx"
load_dotenv(PROJECT_DIR / ".env")
EDGE_VOICE = os.getenv("EDGE_TTS_VOICE", "en-GB-RyanNeural")
EDGE_TIMEOUT = 18
_piper_voice = None
_piper_lock = threading.Lock()
_speech_lock = threading.Lock()
_player_ready = False


def _internet_available():
    try:
        with socket.create_connection(("www.microsoft.com", 443), timeout=0.45):
            return True
    except OSError:
        return False


def _get_piper():
    global _piper_voice
    if _piper_voice is None:
        with _piper_lock:
            if _piper_voice is None:
                if not MODEL_PATH.is_file():
                    raise FileNotFoundError(f"Offline Piper model missing: {MODEL_PATH}")
                print("[Voice] Loading offline British Piper voice...")
                _piper_voice = PiperVoice.load(str(MODEL_PATH))
    return _piper_voice


def _play_file(path):
    global _player_ready
    if not _player_ready:
        pygame.mixer.init()
        _player_ready = True
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()
    try:
        while pygame.mixer.music.get_busy():
            pygame.time.wait(40)
    finally:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()


def _speak_piper(text):
    voice = _get_piper()
    output_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
            output_path = Path(temp.name)
        with wave.open(str(output_path), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        _play_file(output_path)
        print("[Voice] Offline Piper")
    finally:
        if output_path is not None:
            try:
                output_path.unlink(missing_ok=True)
            except PermissionError:
                print("[Voice] Piper temporary file is still in use.")


async def _speak_edge(text):
    import edge_tts
    started = time.perf_counter()
    output_path = None
    try:
        communicate = edge_tts.Communicate(
            text, EDGE_VOICE, volume="+50%", pitch="+0Hz", rate="+10%"
        )
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp:
            output_path = Path(temp.name)
        await asyncio.wait_for(communicate.save(str(output_path)), timeout=EDGE_TIMEOUT)
        generated = time.perf_counter()
        print(f"[Voice Timing] Edge synthesis: {generated - started:.2f}s")
        _play_file(output_path)
        finished = time.perf_counter()
        print(f"[Voice Timing] Edge playback: {finished - generated:.2f}s")
    finally:
        if output_path is not None:
            try:
                output_path.unlink(missing_ok=True)
            except PermissionError:
                print("[Voice] Edge temporary file is still in use.")


def _run_edge_speech(text):
    asyncio.run(_speak_edge(text))


def speak(text):
    """Speak using Edge when reachable; use Piper if Edge fails."""
    text = str(text).strip()
    if not text:
        return
    with _speech_lock:
        started = time.perf_counter()
        if _internet_available():
            try:
                _run_edge_speech(text)
                print(f"[Voice] Microsoft Edge TTS — {EDGE_VOICE}")
                print(f"[Voice Timing] Total speech time: {time.perf_counter() - started:.2f}s")
                return
            except Exception as error:
                print(f"[Voice] Edge TTS failed: {type(error).__name__}: {str(error)[:300]}")
        print("[Voice] Using offline Piper fallback.")
        _speak_piper(text)
        print(f"[Voice Timing] Total speech time: {time.perf_counter() - started:.2f}s")


if __name__ == "__main__":
    speak("Hello. I am Jarvis. My fast voice system is ready, with offline speech available when needed.")
