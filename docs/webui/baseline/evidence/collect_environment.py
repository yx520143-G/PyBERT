"""Read-only metadata for the visible desktop baseline; never sends GUI input."""
import ctypes
import importlib.metadata as metadata
import json
import os
import platform
import sys
from ctypes import wintypes
from pathlib import Path

import pybert

handle = int(sys.argv[1])
user32 = ctypes.windll.user32
user32.GetDpiForWindow.argtypes = [wintypes.HWND]
user32.GetDpiForWindow.restype = wintypes.UINT
rect = wintypes.RECT()
client = wintypes.RECT()
assert user32.GetWindowRect(handle, ctypes.byref(rect))
assert user32.GetClientRect(handle, ctypes.byref(client))
packages = ['pipbert', 'numpy', 'scipy', 'traits', 'traitsui', 'pyface', 'chaco', 'enable',
            'pyside6', 'scikit-rf', 'pyibis-ami', 'pychopmarg']
data = {
    'source_sha': '1bc905d577d2f3bd9471421cfbf3d422d4e6080e',
    'os': platform.platform(), 'python': sys.version, 'python_executable': sys.executable,
    'pybert_file': pybert.__file__, 'versions': {p: metadata.version(p) for p in packages},
    'environment': {k: os.environ.get(k) for k in ['ETS_TOOLKIT', 'QT_API', 'QT_QPA_PLATFORM',
                    'QT_SCALE_FACTOR', 'QT_ENABLE_HIGHDPI_SCALING', 'PYTHONPATH']},
    'window_handle_observed': handle,
    'window_rect_px': [rect.left, rect.top, rect.right, rect.bottom],
    'window_size_px': [rect.right-rect.left, rect.bottom-rect.top],
    'client_size_px': [client.right-client.left, client.bottom-client.top],
    'window_dpi': user32.GetDpiForWindow(handle),
    'primary_screen_px': [user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)],
    'capture_method': 'screenshot skill take_screenshot.ps1 / Graphics.CopyFromScreen / actual HWND',
    'input_method': '@oai/sky documented Windows API; keyboard input and UIA state',
    'uv_executable': r'C:\Users\yx\AppData\Roaming\Python\Python312\Scripts\uv.exe',
    'uv_version': '0.11.23',
    'future_web_acceptance': {'browser': 'Google Chrome', 'version': '155.0.8059.85',
                              'viewport_css_px': [1280, 720], 'zoom_percent': 100},
}
Path(__file__).with_name('environment.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
print(json.dumps(data, indent=2))
