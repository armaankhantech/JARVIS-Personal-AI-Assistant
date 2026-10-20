import re
from safety_config import (
    BLOCKED_TOOL_NAMES,
    PROTECTED_TARGET_TERMS,
    BLOCKED_SHORTCUTS,
    DANGEROUS_COMMAND_PATTERNS,
)

KEY_TOOLS = {
    "press_key", "press_key_in_window", "browser_press", "chrome_press",
    "computer_hotkey", "hotkey",
}
COMMAND_TOOLS = {
    "run_command", "execute_command", "execute_shell", "run_powershell",
}

def check_action(tool_name, arguments):
    """Return (allowed, reason). Deny uncertain or configured risky actions."""
    try:
        name = str(tool_name).strip().casefold()
        args = arguments if isinstance(arguments, dict) else {}

        if name in {str(x).casefold() for x in BLOCKED_TOOL_NAMES}:
            return False, f"Tool '{name}' is blocked by safety_config.py."

        # Protect configured apps/windows/targets from all tool interactions.
        target_fields = (
            "window_title", "control_name", "application", "app_name",
            "target", "url", "profile",
        )
        target_text = " ".join(
            str(args.get(field, "")) for field in target_fields
        ).casefold()

        for term in PROTECTED_TARGET_TERMS:
            if str(term).casefold() in target_text:
                return False, f"Target matches protected term: '{term}'."

        if name in KEY_TOOLS:
            key = str(args.get("key", args.get("keys", "")))
            normalized = re.sub(r"[\s_-]+", "", key.casefold())
            blocked = {
                re.sub(r"[\s_-]+", "", str(k).casefold())
                for k in BLOCKED_SHORTCUTS
            }
            if normalized in blocked:
                return False, f"Shortcut '{key}' is blocked pending trusted approval."

        if name in COMMAND_TOOLS:
            command = str(args.get("command", args.get("cmd", "")))
            for pattern in DANGEROUS_COMMAND_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return False, "Command matches a blocked destructive pattern."

        return True, "Allowed by current safety policy."
    except Exception as exc:
        # Fail closed: a broken safety check must not allow the action.
        return False, f"Safety check failed closed: {type(exc).__name__}: {exc}"
