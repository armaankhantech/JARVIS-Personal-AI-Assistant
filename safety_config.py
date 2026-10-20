# Jarvis central safety settings.
# Edit these lists as needed. Keep the guard enabled.

BLOCKED_TOOL_NAMES = {
    "delete_file", "delete_path", "remove_file", "remove_path",
    "run_command", "execute_command", "execute_shell",
    "run_powershell", "shutdown_computer", "format_drive",
}

# Any action targeting these names is blocked by default.
PROTECTED_TARGET_TERMS = {
    "password manager", "bitwarden", "1password", "keepass",
    "banking", "online banking", "credential vault",
}

# These shortcuts are blocked until a trusted approval workflow exists.
BLOCKED_SHORTCUTS = {
    "ctrl+a", "ctrl+x", "ctrl+v", "ctrl+s",
    "alt+f4", "win+r", "shift+delete",
}

# Only applied to command-execution tools, never ordinary text entry.
DANGEROUS_COMMAND_PATTERNS = [
    r"\bformat\s+[a-z]:",
    r"\bremove-item\b.*-recurse",
    r"\bdel\s+.*[/*]",
    r"\brmdir\s+.*[/s]",
    r"\bshutdown\b",
    r"\bformat-volume\b",
]
