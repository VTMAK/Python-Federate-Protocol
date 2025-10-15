"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional

# Simple logging utility with colored console output and optional file logging.

class Colors:
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    ORANGE = "\033[33m"
    WHITE = "\033[37m"
    RESET = "\033[0m"

_default_log_file_path_holder: list[Optional[str]] = [None]

def set_log_file_path(path: Optional[str]) -> None:
    """
        Description:
            Configure default log file path used when individual log calls omit a path.
        Inputs:
            path (Optional[str]): Filesystem path to append log lines or None to disable file logging globally.
        Outputs:
            None
        Exceptions:
            None raised; simply stores path in holder.
    """
    _default_log_file_path_holder[0] = path

def _write_file(message: str, log_file_path: Optional[str]) -> None:
    """
        Description:
            Append a single formatted log line (with timestamp) to the designated log file.
        Inputs:
            message (str): Already formatted message (no trailing newline required).
            log_file_path (Optional[str]): Explicit path override; if None uses default holder; if still None does nothing.
        Outputs:
            None
        Exceptions:
            Silently swallows OSError (e.g., permission or IO issues) to avoid disrupting caller.
    """
    try:
        path = log_file_path or _default_log_file_path_holder[0]
        if not path:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except OSError:
        # Avoid raising from logging
        pass

def log_and_print(message: Any, kind: str = "info", log_to_file: bool = False, log_file_path: Optional[str] = None) -> None:
    """
        Description:
            Core logging function performing colored console print and optional file logging.
        Inputs:
            message (Any): Object to be stringified and logged.
            kind (str): Category controlling color (outgoing, incoming, error, warning, info).
            log_to_file (bool): If True, persist line to file (using provided or default path).
            log_file_path (Optional[str]): Per-call path override.
        Outputs:
            None
        Exceptions:
            Any print-related exceptions propagate; file write errors suppressed in _write_file.
    """
    color_map = {
        "outgoing": Colors.BLUE,
        "incoming": Colors.GREEN,
        "error": Colors.RED,
        "warning": Colors.ORANGE,
        "info": Colors.WHITE,
    }
    color = color_map.get(kind, Colors.WHITE)
    text = str(message)
    try:
        # Console output with ANSI colors
        print(f"{color}{text}{Colors.RESET}")
    finally:
        if log_to_file:
            _write_file(text, log_file_path)

def log_outgoing(message: Any, log_to_file: bool = False, log_file_path: Optional[str] = None) -> None:
    """
        Description:
            Log an outgoing (sent) message in blue.
        Inputs:
            message (Any): Content to log.
            log_to_file (bool): Whether to append to file.
            log_file_path (Optional[str]): Optional per-call path.
        Outputs:
            None
        Exceptions:
            Same as log_and_print.
    """
    log_and_print(message, kind="outgoing", log_to_file=log_to_file, log_file_path=log_file_path)

def log_incoming(message: Any, log_to_file: bool = False, log_file_path: Optional[str] = None) -> None:
    """
        Description:
            Log an incoming (received) message in green.
        Inputs:
            message (Any)
            log_to_file (bool)
            log_file_path (Optional[str])
        Outputs:
            None
        Exceptions:
            Same as log_and_print.
    """
    log_and_print(message, kind="incoming", log_to_file=log_to_file, log_file_path=log_file_path)

def log_error(message: Any, log_to_file: bool = False, log_file_path: Optional[str] = None) -> None:
    """
        Description:
            Log an error message in red.
        Inputs:
            message (Any)
            log_to_file (bool)
            log_file_path (Optional[str])
        Outputs:
            None
        Exceptions:
            Same as log_and_print.
    """
    log_and_print(message, kind="error", log_to_file=log_to_file, log_file_path=log_file_path)

def log_warning(message: Any, log_to_file: bool = False, log_file_path: Optional[str] = None) -> None:
    """
        Description:
            Log a warning message in orange.
        Inputs:
            message (Any)
            log_to_file (bool)
            log_file_path (Optional[str])
        Outputs:
            None
        Exceptions:
            Same as log_and_print.
    """
    log_and_print(message, kind="warning", log_to_file=log_to_file, log_file_path=log_file_path)

def log_info(message: Any, log_to_file: bool = False, log_file_path: Optional[str] = None) -> None:
    """
        Description:
            Log an informational message in white.
        Inputs:
            message (Any)
            log_to_file (bool)
            log_file_path (Optional[str])
        Outputs:
            None
        Exceptions:
            Same as log_and_print.
    """
    log_and_print(message, kind="info", log_to_file=log_to_file, log_file_path=log_file_path)
