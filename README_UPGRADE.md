# Jarvis — Clean Integrated Upgrade

This package is based on the source files supplied for review. It excludes Chrome profile data, browser histories/login databases, `.env`, caches, backups, and runtime screenshots.

## Important reality check
This is a source-code upgrade, not a guarantee that every Windows app/site can be controlled perfectly. Windows accessibility support varies by app. Screenshot-based clicking uses a vision model and can fail when the target is hidden, ambiguous, or the model/provider is unavailable. Jarvis must report uncertain actions instead of claiming success.

## Preserve your current working setup
1. Stop Jarvis.
2. Back up the current project folder.
3. Extract this ZIP into a NEW folder first, e.g. `D:\AI DEVELOPMENT\Python\PROJECTS\Jarvis_Upgrade`.
4. Copy your existing `.env` into the new folder only if you want to use the same providers. Never share that file.
5. Review `.env` and keep API keys private. The package intentionally does not contain your keys or browser sessions.

## Install / run in your existing environment
Open PowerShell in the extracted folder and activate your existing compatible virtual environment, or create a new one.

```powershell
python -m venv .jarvisvenv
.\.jarvisvenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-jarvis.txt
```

If you already have a working Jarvis virtual environment, do not recreate it; activate it and install the new wake-word dependency if needed:

```powershell
python -m pip install openwakeword
```

Then run the syntax check:

```powershell
Get-ChildItem -Recurse -Filter *.py | Where-Object { $_.FullName -notmatch '\\.jarvisvenv\\|\\__pycache__\\' } | ForEach-Object { python -m py_compile $_.FullName }
```

Start Jarvis:

```powershell
python .\main.py
```

## Wake word
The new optional detector uses the pretrained **“Hey Jarvis”** model from openWakeWord. It is not a custom single-word “Jarvis” detector. Model files may be downloaded on first setup; detection is local once the model is available. Say **“Hey Jarvis”**, wait for the beep, then speak the command. This two-stage flow prevents the wake phrase from being sent as the command. If the detector cannot load, Jarvis falls back to the existing continuous Whisper listener instead of crashing.

Environment options:
- `JARVIS_WAKE_WORD=1` enables wake-word mode (default).
- `JARVIS_WAKE_WORD=0` disables it and uses the existing continuous listener.
- `JARVIS_WAKE_THRESHOLD=0.55` sets the detector threshold. Raise it to reduce false triggers; lower it if it misses your voice.

## Voice
Ryan's Edge TTS voice is set to `en-GB-RyanNeural` at `+10%` rate. Change `rate="+10%"` in `voice/voice_router.py` to adjust speaking speed. Edge TTS requires internet; Piper is the offline fallback and its model is included.

## Chrome extension bridge
The extension source is in `browser_extension`. In Chrome, open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select this folder. Keep the bridge token in `browser_extension/config.js` synchronized with `tools/chrome_bridge.py`; do not post it publicly. Select the intended Work/Main/Automation profile in the extension popup before asking Jarvis to control that profile.

This ZIP excludes live browser profiles. Your existing Chrome profiles remain on your computer and should not be copied into this project.

## Safety and real-world actions
- Keep `safety_guard.py` enabled. Do not remove the check before tool execution.
- For installs, account changes, sending messages, submitting forms, deleting files, purchases, or other consequential actions, Jarvis should seek explicit confirmation when needed and must not bypass OS or website security prompts.
- Windows UAC, Microsoft Store sign-in, licensing, region restrictions, anti-bot checks, and app-specific dialogs may still require you to act manually.
- A tool result that says a click was sent is not proof that the intended action completed. Verify the visible outcome.

## First acceptance tests
1. `python -c "from agent import JarvisAgent; from tools.chrome_bridge import bridge_status; a=JarvisAgent(); print(len(a.registry.list_tools()), sorted(a.registry.list_tools())); print(bridge_status())"`
2. Start Jarvis and confirm the wake detector loads. If it does not, use the continuous-listening fallback and share the exact error.
3. Test a harmless request: “Hey Jarvis” → beep → “tell me a short joke.”
4. Test “list my open windows.”
5. Test “open VS Code” and verify the new window via `list_windows`.
6. Test browser search with a harmless query and the explicit profile.
7. Test screenshot targeting on a harmless, clearly visible control. Do not start with installation or deletion.
8. Check that the action result and actual screen agree before treating it as verified.

## Known limitation
No desktop agent can safely guarantee “click anything” on every application. Use accessibility controls first, browser DOM tools for browser pages, and screenshot/vision fallback for custom-rendered controls. If a target is ambiguous or an action cannot be verified, Jarvis should stop and explain.
