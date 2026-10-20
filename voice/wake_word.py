"""Local wake-word detection using openWakeWord's pretrained Hey Jarvis model.

Detection runs locally after the model has been installed/downloaded once.
The pretrained model recognizes "Hey Jarvis", not the single word "Jarvis".
"""
from __future__ import annotations

import queue
import time

import numpy as np
import sounddevice as sd


class WakeWordDetector:
    def __init__(self, device=1, threshold=0.55, sample_rate=16000):
        self.device = device
        self.threshold = float(threshold)
        self.sample_rate = int(sample_rate)
        self.frame_size = 1280  # openWakeWord expects 80 ms frames at 16 kHz.
        self._model = None

    def load(self):
        try:
            from openwakeword.model import Model
        except ImportError as exc:
            raise RuntimeError(
                "Wake-word support needs openwakeword. Install it with: "
                "python -m pip install openwakeword"
            ) from exc
        print("[Wake Word] Loading local 'Hey Jarvis' detector...")
        # openWakeWord may download its public model on first setup. Detection
        # itself is local after the model files are available.
        self._model = Model(
            wakeword_models=["hey_jarvis"],
            inference_framework="onnx",
        )
        print("[Wake Word] Ready. Say 'Hey Jarvis', then speak your command.")

    def wait(self):
        """Block until a wake word is detected; returns False on Ctrl+C."""
        if self._model is None:
            self.load()

        frames = queue.Queue(maxsize=24)

        def callback(indata, frame_count, time_info, status):
            data = indata[:, 0].copy()
            try:
                frames.put_nowait(data)
            except queue.Full:
                try:
                    frames.get_nowait()
                    frames.put_nowait(data)
                except queue.Empty:
                    pass

        print("\n[Wake Word] Waiting for 'Hey Jarvis'...")
        try:
            with sd.InputStream(
                device=self.device,
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.frame_size,
                callback=callback,
            ):
                while True:
                    audio = frames.get()
                    scores = self._model.predict(audio)
                    if scores and max(float(v) for v in scores.values()) >= self.threshold:
                        print("[Wake Word] Detected. Listening for your command...")
                        try:
                            import winsound
                            winsound.Beep(880, 100)
                        except Exception:
                            pass
                        # Reset prediction state to reduce immediate repeat triggers.
                        try:
                            self._model.reset()
                        except Exception:
                            pass
                        time.sleep(0.12)
                        return True
        except KeyboardInterrupt:
            return False
