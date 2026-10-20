
"""Speech input for Jarvis with longer, pause-tolerant recording."""
import queue
import time

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


class JarvisListener:
    def __init__(self):
        print("[Voice Input] Loading Whisper small.en...")
        self.model = WhisperModel(
            "small.en",
            device="cpu",
            compute_type="int8",
        )

        self.device = 1
        self.sample_rate = 16000
        self.frame_ms = 30
        self.frame_size = int(self.sample_rate * self.frame_ms / 1000)

        self.start_threshold = 0.003
        self.end_silence = 1.35
        self.min_speech_seconds = 0.24
        self.max_recording_seconds = 40

        print("[Voice Input] Ready for continuous listening.")

    def listen(self):
        started = time.perf_counter()
        audio_queue = queue.Queue(maxsize=300)

        def callback(indata, frames, time_info, status):
            chunk = indata[:, 0].copy()
            try:
                audio_queue.put_nowait(chunk)
            except queue.Full:
                # Keep the newest audio if the consumer falls behind.
                try:
                    audio_queue.get_nowait()
                    audio_queue.put_nowait(chunk)
                except (queue.Empty, queue.Full):
                    pass

        recording = []
        speaking = False
        silence_seconds = 0.0
        elapsed_recording = 0.0
        frame_seconds = self.frame_ms / 1000.0

        print("\n[Listening] Speak naturally. Finish your full instruction, then pause.")

        try:
            with sd.InputStream(
                device=self.device,
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.frame_size,
                callback=callback,
            ):
                while elapsed_recording < self.max_recording_seconds:
                    try:
                        audio = audio_queue.get(timeout=1.0)
                    except queue.Empty:
                        continue

                    elapsed_recording += frame_seconds
                    level = float(np.sqrt(np.mean(audio * audio) + 1e-12))

                    if not speaking:
                        if level >= self.start_threshold:
                            speaking = True
                            recording.append(audio)
                            print("[Voice Input] Speech detected...")
                        continue

                    recording.append(audio)

                    if level < self.start_threshold:
                        silence_seconds += frame_seconds
                    else:
                        silence_seconds = 0.0

                    if silence_seconds >= self.end_silence:
                        break

        except KeyboardInterrupt:
            return ""
        except Exception as error:
            print(
                f"[Voice Input] Microphone error: "
                f"{type(error).__name__}: {error}"
            )
            return ""

        print(
            f"[Timing] Recording: "
            f"{time.perf_counter() - started:.2f}s"
        )

        if not recording or elapsed_recording < self.min_speech_seconds:
            return ""

        audio_data = np.concatenate(recording).astype(
            np.float32, copy=False
        )

        print("[Voice Input] Transcribing...")
        transcription_started = time.perf_counter()

        try:
            segments, _ = self.model.transcribe(
                audio_data,
                language="en",
                beam_size=1,
                best_of=1,
                vad_filter=False,
                condition_on_previous_text=False,
                without_timestamps=True,
                initial_prompt=(
                    "Jarvis, Windows computer assistant. Common terms: "
                    "VS Code, Visual Studio Code, File Explorer, Chrome, "
                    "Work profile, Main profile, list windows, inspect window, "
                    "click control, click coordinates, type text, activate window."
                ),
            )

            text = " ".join(
                segment.text.strip()
                for segment in segments
            ).strip()

            print(
                f"[Timing] Transcription: "
                f"{time.perf_counter() - transcription_started:.2f}s"
            )

        except Exception as error:
            print(
                f"[Voice Input] Transcription failed: "
                f"{type(error).__name__}: {error}"
            )
            return ""

        if text:
            print(f"You said: {text}")
        else:
            print("[Voice Input] No clear speech recognised.")

        return text
