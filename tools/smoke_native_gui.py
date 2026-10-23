"""Build the actual native TraitsUI window and close after its Qt event loop starts."""

import json
import contextlib
import importlib.util
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from pybert.gui.view import traits_view
from pybert.pybert import PyBERT


def main():
    reference = "--reference" in sys.argv
    if reference:
        path = Path("docs/webui/issue2/evidence/numeric-20261024-043542/F-NRZ-01/native_bert.py")
        spec = importlib.util.spec_from_file_location("pybert.models.gui_reference",path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        import pybert.pybert as native_class
        native_class.my_run_simulation = module.my_run_simulation
    app = QApplication.instance() or QApplication([])
    prefix = "native-gui-reference" if reference else "native-gui-smoke"
    log = Path(f"docs/webui/issue2/evidence/{prefix}.stderr.txt")
    with log.open("w",encoding="utf-8") as stderr, contextlib.redirect_stderr(stderr):
        engine = PyBERT(gui=True)
        ui = engine.edit_traits(view=traits_view, kind="nonmodal")
    report = {"native_status": engine.status, "window_title": ui.control.windowTitle(),
              "visible": ui.control.isVisible(), "qt_widget": type(ui.control).__name__}
    QTimer.singleShot(1500, app.quit)
    app.exec()
    ui.dispose()
    report.update(reference=reference,observer_attribute_error_count=log.read_text(encoding="utf-8").count("AttributeError:"))
    Path(f"docs/webui/issue2/evidence/{prefix}.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(report)
    assert report["native_status"]=="Ready." and report["visible"]


if __name__ == "__main__":
    main()
