# Author: Maurizio Verde — LastReload
"""Portability helpers (Linux / macOS / native Windows), standard library only.

- `lock_fd` / `unlock_fd`: exclusive, blocking lock on an open file descriptor. POSIX: `fcntl.flock` (unchanged
  behaviour); Windows: `msvcrt.locking` on the first byte, retried until it is granted.
- `console_safe`: a Windows console (cp1252, cp850...) cannot encode characters like ⟪ 📌 🗑; printing them raised
  UnicodeEncodeError. Non-UTF-8 stdout/stderr switch to `errors="backslashreplace"`; UTF-8 streams are untouched.
- `sqlite_ro_uri`: `file:` URI for a read-only sqlite connection that also works with `C:\\...` paths.
- `bad_name`: characters that cannot appear in a single file name on this OS.
"""
from __future__ import annotations

import os
import sys
import time

WINDOWS = os.name == "nt"

if WINDOWS:  # pragma: no cover - exercised on the windows-latest CI runner
    import msvcrt

    def lock_fd(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)   # LK_LOCK itself retries for ~10 s, then OSError
                return
            except OSError:
                time.sleep(0.05)

    def unlock_fd(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def lock_fd(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_EX)

    def unlock_fd(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


def console_safe(*streams) -> None:
    """Never crash on a character the console code page cannot encode (UTF-8 streams are left as they are)."""
    for s in streams or (sys.stdout, sys.stderr):
        enc = (getattr(s, "encoding", None) or "").lower().replace("-", "").replace("_", "")
        if enc in ("utf8", "utf8sig") or not hasattr(s, "reconfigure"):
            continue
        try:
            s.reconfigure(errors="backslashreplace")
        except (ValueError, OSError):
            pass


def sqlite_ro_uri(path: str) -> str:
    """Read-only sqlite URI. POSIX: `file:/abs/path?mode=ro` (as before). Windows: `file:///C:/abs/path?mode=ro`."""
    p = os.path.abspath(path)
    if WINDOWS:
        p = "/" + p.replace("\\", "/")
    if WINDOWS:
        return "file://%s?mode=ro" % p.replace("%", "%25").replace("?", "%3f").replace("#", "%23")
    return "file:%s?mode=ro" % p.replace("?", "%3f").replace("#", "%23")


def replace(src: str, dst: str, tries: int = 50) -> None:
    """os.replace. On Windows a destination briefly open in another process (a reader of last_request.json, an
    antivirus scan) makes it fail with PermissionError: retry for up to ~2.5 s. POSIX: a single os.replace."""
    if not WINDOWS:
        os.replace(src, dst)
        return
    for i in range(tries):  # pragma: no cover - Windows only
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.05)


O_BINARY = getattr(os, "O_BINARY", 0)   # Windows: os.open is text mode (LF -> CRLF on write) without it


def bad_name(name: str) -> bool:
    """True if `name` is not a plain file name here (path separators; on Windows also `:` and reserved chars)."""
    if "/" in name or name.startswith("."):
        return True
    if WINDOWS:
        return any(c in name for c in '\\:*?"<>|') or name.rstrip(" .") != name
    return False
