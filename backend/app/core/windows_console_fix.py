"""
Windows Console Encoding Fix

This module MUST be imported before any other modules to prevent
UnicodeEncodeError when CrewAI outputs emojis to the Windows console.

Import this at the very top of your main entry point:
    import app.core.windows_console_fix  # Must be first import!
"""

import sys
import io

if sys.platform == "win32":
    class SafeConsoleWriter:
        """
        A wrapper around stdout/stderr that handles encoding errors gracefully.
        Replaces characters that can't be encoded with '?' instead of crashing.
        """
        def __init__(self, stream, encoding='utf-8'):
            self._stream = stream
            self._encoding = encoding

        def write(self, s):
            if not s:
                return 0
            try:
                # Try to write normally
                return self._stream.write(s)
            except UnicodeEncodeError:
                # Fall back to replacing problematic characters
                safe_s = s.encode('ascii', 'replace').decode('ascii')
                return self._stream.write(safe_s)

        def flush(self):
            if hasattr(self._stream, 'flush'):
                return self._stream.flush()

        def fileno(self):
            if hasattr(self._stream, 'fileno'):
                return self._stream.fileno()
            raise io.UnsupportedOperation("fileno")

        def isatty(self):
            if hasattr(self._stream, 'isatty'):
                return self._stream.isatty()
            return False

        @property
        def encoding(self):
            return self._encoding

        @property
        def errors(self):
            return 'replace'

        def __getattr__(self, name):
            # Delegate any other attributes to the underlying stream
            return getattr(self._stream, name)

    # Wrap stdout and stderr with safe writers
    if not isinstance(sys.stdout, SafeConsoleWriter):
        sys.stdout = SafeConsoleWriter(sys.stdout)
    if not isinstance(sys.stderr, SafeConsoleWriter):
        sys.stderr = SafeConsoleWriter(sys.stderr)

    # Also wrap __stdout__ and __stderr__ which some libraries access directly
    if hasattr(sys, '__stdout__') and sys.__stdout__ is not None:
        if not isinstance(sys.__stdout__, SafeConsoleWriter):
            sys.__stdout__ = SafeConsoleWriter(sys.__stdout__)
    if hasattr(sys, '__stderr__') and sys.__stderr__ is not None:
        if not isinstance(sys.__stderr__, SafeConsoleWriter):
            sys.__stderr__ = SafeConsoleWriter(sys.__stderr__)
