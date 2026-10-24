"""Observe Chrome service child peak working sets; no engine/model invocation."""

import ctypes
import json
import re
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.verify_web_optimizer import rss


class Entry(ctypes.Structure):
    _fields_ = [(name, kind) for name, kind in (
        ("size", wintypes.DWORD), ("usage", wintypes.DWORD), ("pid", wintypes.DWORD),
        ("heap", ctypes.c_size_t), ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
        ("parent", wintypes.DWORD), ("priority", wintypes.LONG), ("flags", wintypes.DWORD),
        ("exe", wintypes.WCHAR * 260))]


if __name__ == "__main__":
    version = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    parent = int(re.search(r"server process \[(\d+)\]", (ROOT / f".pybert-web/chrome-v{version}-server.log").read_text()).group(1))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ("Process32FirstW", "Process32NextW"):
        getattr(kernel, name).argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    records = {}
    end = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 90)
    out = ROOT / f"docs/webui/issue10/evidence/chrome-v{version}/child-memory{sys.argv[2] if len(sys.argv)>2 else ''}.json"
    while time.time() < end:
        handle = kernel.CreateToolhelp32Snapshot(2, 0)
        entry = Entry(size=ctypes.sizeof(Entry))
        available = kernel.Process32FirstW(handle, ctypes.byref(entry))
        while available:
            if entry.parent == parent:
                row = records.setdefault(str(entry.pid), {"first_seen": time.time(), "peak_working_set_bytes": 0})
                row.update(last_seen=time.time(), peak_working_set_bytes=max(row["peak_working_set_bytes"], rss(entry.pid)))
            available = kernel.Process32NextW(handle, ctypes.byref(entry))
        kernel.CloseHandle(handle)
        out.write_text(json.dumps({"service_pid": parent, "children": records}, indent=2), encoding="utf-8")
        time.sleep(.03)
