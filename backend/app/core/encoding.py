"""
Cross-platform encoding utilities.

Provides safe output functions that work on Windows without emoji encoding errors.
"""

import sys

# ASCII alternatives for common emojis
EMOJI_MAP = {
    "✓": "[OK]",
    "✅": "[OK]",
    "❌": "[ERR]",
    "⏳": "[...]",
    "→": "->",
    "•": "*",
    "📁": "[DIR]",
    "📄": "[DOC]",
    "🔍": "[?]",
    "💾": "[SAVE]",
    "🚀": "[GO]",
    "⚠️": "[WARN]",
    "ℹ️": "[INFO]",
}


def safe_str(text: str) -> str:
    """
    Convert a string to be safe for Windows console output.

    On Windows with cp1252 encoding, replaces emojis with ASCII alternatives.
    On other platforms, returns the string unchanged.
    """
    if sys.platform != "win32":
        return text

    result = text
    for emoji, replacement in EMOJI_MAP.items():
        result = result.replace(emoji, replacement)
    return result


def safe_print(*args, **kwargs):
    """
    Print function that handles encoding issues on Windows.

    Automatically converts emojis to ASCII alternatives on Windows.
    """
    if sys.platform == "win32":
        safe_args = [safe_str(str(arg)) for arg in args]
        print(*safe_args, **kwargs)
    else:
        print(*args, **kwargs)
