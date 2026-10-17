"""Tiện ích dùng chung cho các script CLI."""

from __future__ import annotations

import sys


def force_utf8_stdout() -> None:
    """Ép stdout/stderr dùng UTF-8.

    Console Windows mặc định là cp1252, in tiếng Việt sẽ lỗi
    UnicodeEncodeError. Gọi hàm này ở đầu mọi script CLI.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
