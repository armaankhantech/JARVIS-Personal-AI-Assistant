
"""Jarvis voice assistant: natural wake phrases, continuous conversation and standby."""
import re
import time

from agent import JarvisAgent
from tools.chrome_bridge import bridge_status
from voice.stt import JarvisListener
from voice.voice_router import speak


def normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    return " ".join(text.split())



import re


def spoken_response(text):
    """Convert Markdown responses into clean, natural speech."""
    text = str(text or "")

    # Remove fenced code blocks instead of reading their symbols aloud.
    text = re.sub(r"```[\s\S]*?```", " Code block omitted. ", text)

    # Keep the readable text inside links and inline code.
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)

    # Remove Markdown headings, quotes, and list prefixes.
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)

    # Remove bold, italic, and strikethrough formatting.
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)

    # Remove leftover Markdown and HTML formatting characters.
    text = re.sub(r"</?[^>]+>", " ", text)
    text = re.sub(r"[*_`#~|]", " ", text)

    # Normalize whitespace so speech sounds more natural.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def matches_any(text: str, phrases: tuple[str, ...]) -> bool:
    """Match a complete phrase or a phrase within a longer sentence."""
    return any(
        re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text)
        for phrase in phrases
    )


PAUSE_PHRASES = (
    "wait", "wait a moment", "wait a minute", "wait for a moment",
    "hold on", "hang on", "pause", "pause jarvis",
    "wait jarvis", "jarvis wait", "stop listening",
    "go to sleep", "take a break", "be quiet for a moment",
)

EXIT_PHRASES = (
    "exit jarvis", "quit jarvis", "shut down jarvis",
    "shutdown jarvis", "close jarvis", "goodbye jarvis",
)

# Edit this list whenever you want to add your own wake-up phrases.
WAKE_PHRASES = (
    "hey jarvis", "hi jarvis", "wake up", "wake up jarvis",
    "wake up bro", "stand up", "stand up bro",
    "where are you", "where are you bro", "you there",
    "are you there", "jarvis are you there", "rise and shine",
    "get up", "wake bro", "start listening", "listen up",
    "come alive", "jarvis", "hello jarvis", "yo jarvis",
)


def is_pause_command(command: str) -> bool:
    return matches_any(command, PAUSE_PHRASES)


def is_exit_command(command: str) -> bool:
    return command in {"exit", "quit", "shutdown"} or matches_any(
        command, EXIT_PHRASES
    )


def is_wake_command(command: str) -> bool:
    return matches_any(command, WAKE_PHRASES)


def main():
    print("=" * 48)
    print("JARVIS — HANDS-FREE VOICE MODE")
    print("=" * 48)

    try:
        status = bridge_status()
        print(
            "[Browser Bridge] Online"
            if status.get("success")
            else "[Browser Bridge] Unavailable; continuing."
        )
    except Exception as error:
        print(f"[Browser Bridge] Warning: {type(error).__name__}: {error}")

    try:
        jarvis = JarvisAgent()
        listener = JarvisListener()
    except Exception as error:
        print(f"[Startup Error] {type(error).__name__}: {error}")
        return

    # Start in standby. This allows a natural wake phrase to activate Jarvis.
    awake = False

    print("\n[Jarvis] Ready, bro.")
    print("[Jarvis] Standby: say 'Wake up', 'Where are you, bro?' or 'Hey Jarvis'.")
    print("[Jarvis] While awake, keep talking naturally after each response.")
    print("[Jarvis] Say 'Wait a moment' or 'Stop listening' to pause.")
    print("[Jarvis] Say 'Exit Jarvis' to shut me down.")
    print("[Jarvis] Standby speech is transcribed locally to detect wake phrases.")

    try:
        while True:
            try:
                started = time.perf_counter()
                spoken = listener.listen()
                print(
                    f"[Timing] Voice input total: "
                    f"{time.perf_counter() - started:.2f}s"
                )
            except KeyboardInterrupt:
                break
            except Exception as error:
                print(f"[Voice Input Error] {type(error).__name__}: {error}")
                time.sleep(0.25)
                continue

            if not spoken:
                continue

            command = normalize(spoken)
            if not command:
                continue

            # Shutdown works in either mode.
            if is_exit_command(command):
                print("[Jarvis] Shutting down. Catch you later, bro!")
                speak("Alright, bro. Shutting down. Catch you later!")
                break

            # Standby: do not send ordinary background speech to the agent.
            if not awake:
                if is_wake_command(command):
                    awake = True
                    print(f"\n[Jarvis] Awake! I heard: {spoken}")
                    speak("I'm here, bro! What's the plan?")
                else:
                    print("[Standby] No wake phrase detected; ignoring speech.")
                continue

            # Active conversation: pause requests take priority over LLM calls.
            if is_pause_command(command):
                awake = False
                print("[Jarvis] Going into standby.")
                speak("No worries, bro. I'll wait right here. Call me when you're ready.")
                continue


            # All other active commands go through the existing agent and safety guard.
            try:
                started = time.perf_counter()
                response = jarvis.chat(spoken)
                print(
                    f"[Timing] Jarvis request total: "
                    f"{time.perf_counter() - started:.2f}s"
                )
                print(f"\nJarvis: {response}")
                speak(spoken_response(response))
            except Exception as error:
                print(f"[Jarvis Error] {type(error).__name__}: {error}")
                speak("Oops, bro. I hit a snag. Give me another try.")

            # Do not reset awake here: the next loop listens for the next command.

    except KeyboardInterrupt:
        print("\n[Jarvis] Stopping voice mode.")
    finally:
        print("[Jarvis] Shutdown complete.")


if __name__ == "__main__":
    main()
