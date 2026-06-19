"""Foreground-window context detection (Windows UI Automation helper).

Detects which application currently has focus so the text pipeline can adapt
its formatting (Slack vs. Gmail vs. VS Code, etc.). Best-effort: returns None
when the platform is unsupported or detection fails, so callers can fall back
to a neutral style.
"""
import os
import sys
import logging

# Default mapping from executable name (lowercased, with extension) to the
# context label understood by the text pipeline. Extendable via config.
DEFAULT_PROCESS_MAP = {
    "slack.exe": "Slack",
    "discord.exe": "Slack",        # similar fast-chat style
    "whatsapp.exe": "WhatsApp",
    "telegram.exe": "WhatsApp",
    "code.exe": "VS Code",
    "code - insiders.exe": "VS Code",
    "cursor.exe": "Cursor",
    "notion.exe": "Notion",
    "obsidian.exe": "Notas",
    "notepad.exe": "Notas",
    "outlook.exe": "Correo",
    "olk.exe": "Correo",
    "thunderbird.exe": "Correo",
}

# Keyword (found in the window title, lowercased) -> context. Used mainly for
# web apps running inside a browser (Gmail, Notion, WhatsApp Web, etc.).
DEFAULT_TITLE_MAP = {
    "gmail": "Gmail",
    "outlook": "Correo",
    "proton mail": "Correo",
    "notion": "Notion",
    "slack": "Slack",
    "whatsapp": "WhatsApp",
    "discord": "Slack",
    "visual studio code": "VS Code",
    "cursor": "Cursor",
}

# Browsers whose window title we inspect to identify the active web app.
BROWSER_EXES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
    "opera.exe", "arc.exe", "vivaldi.exe",
}


def _get_foreground_info_windows():
    """Return (exe_name_lower, window_title) for the foreground window on Windows."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "", ""

    # Window title
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value or ""

    # Owning process id
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    exe_name = ""
    process_query_limited_information = 0x1000
    h_process = kernel32.OpenProcess(process_query_limited_information, False, pid.value)
    if h_process:
        try:
            size = wintypes.DWORD(32768)
            path_buf = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(h_process, 0, path_buf, ctypes.byref(size)):
                exe_name = os.path.basename(path_buf.value)
        finally:
            kernel32.CloseHandle(h_process)

    return exe_name.lower(), title


def detect_context(process_map=None, title_map=None):
    """Detect the focused application's context label, or None if unknown.

    process_map / title_map let callers override or extend the defaults
    (e.g. from the user's config).
    """
    if sys.platform != "win32":
        return None

    process_map = {**DEFAULT_PROCESS_MAP, **(process_map or {})}
    title_map = {**DEFAULT_TITLE_MAP, **(title_map or {})}

    try:
        exe_name, title = _get_foreground_info_windows()
    except Exception as e:
        logging.warning(f"Context detection failed: {e}")
        return None

    if not exe_name:
        return None

    title_lower = (title or "").lower()

    # Native desktop apps: match by executable first.
    if exe_name in process_map:
        return process_map[exe_name]

    # Web apps inside a browser: identify them from the window title.
    if exe_name in BROWSER_EXES:
        for keyword, context in title_map.items():
            if keyword in title_lower:
                return context

    # Last resort: any app whose title hints at a known context.
    for keyword, context in title_map.items():
        if keyword in title_lower:
            return context

    return None
