"""
hooks — extensible hook system plus built-in callbacks.

Events: UserPromptSubmit, PreToolUse, PostToolUse, Stop.
Hooks auto-register at import time.
"""
from config import WORKDIR

# ── Hook registry ─────────────────────────────────────────
HOOKS = {
    "UserPromptSubmit": [],
    "PreToolUse": [],
    "PostToolUse": [],
    "Stop": [],
}


def register_hook(event: str, callback):
    """Register a callback for a hook event."""
    HOOKS[event].append(callback)


def trigger_hooks(event: str, *args):
    """Fire all callbacks for *event*. First non-None return short-circuits."""
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:
            return result
    return None


# ── Built-in hook callbacks ───────────────────────────────
DENY_LIST = [
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "mkfs",
    "dd if=",
]


def permission_hook(block):
    """PreToolUse: block dangerous shell commands."""
    if block.name == "bash":
        for p in DENY_LIST:
            if p in block.input.get("command", ""):
                print(f"\n\033[31m⛔ Blocked: '{p}'\033[0m")
                return "Permission denied"
    return None


def log_hook(block):
    """PreToolUse: log every tool invocation."""
    print(f"\033[90m[HOOK] {block.name}\033[0m")
    return None


def context_inject_hook(query: str):
    """UserPromptSubmit: log the current working directory."""
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None


def summary_hook(messages: list):
    """Stop: print total tool-call count for the session."""
    tool_count = sum(
        1
        for m in messages
        for b in (
            m.get("content") if isinstance(m.get("content"), list) else []
        )
        if isinstance(b, dict) and b.get("type") == "tool_result"
    )
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None


# ── Auto-register built-in hooks ──────────────────────────
register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("Stop", summary_hook)
