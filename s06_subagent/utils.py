"""
utils — shared helpers used across modules.
"""
from pathlib import Path
from config import WORKDIR


def safe_path(p: str) -> Path:
    """Resolve a path relative to WORKDIR; reject paths that escape."""
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def extract_text(content) -> str:
    """Extract concatenated text from message content blocks."""
    if not isinstance(content, list):
        return str(content)
    return "\n".join(
        getattr(b, "text", "")
        for b in content
        if getattr(b, "type", None) == "text"
    )
