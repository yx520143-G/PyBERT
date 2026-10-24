"""Verify installed dependency provenance without importing the model or engine."""

import ast
import hashlib
from importlib import metadata, util
import json
from pathlib import Path
import re
import sys
import traceback
from urllib.parse import unquote, urlparse


def main():
    """Import only the inert package; inspect the model through its spec and AST."""
    route, output_name = sys.argv[1:]
    assert route in ("A", "B")
    root = Path(__file__).resolve().parents[4]
    output = Path(output_name).resolve()
    assert not output.exists()
    expected = json.loads(Path(__file__).with_name("source-inputs.json").read_text(encoding="utf-8"))
    environment = root / ".venv" if route == "A" else root.parent / "pybert-issue25-pip-venv"
    result = {
        "route": route, "executable": sys.executable, "python": sys.version,
        "prefix": sys.prefix, "base_prefix": sys.base_prefix, "sys_path": sys.path,
        "expected_F": expected["F"], "expected_tree": expected["F_tree"],
        "blocked_attempts": [], "production_python_methods": 0,
        "real_model_C_loader_engine_DSP_parser_calls": 0,
        "mode": "pyibisami package import; model ModuleSpec/AST only, no model module body",
        "guard_boundary": "before any product import; ctypes/engine/parser/helper imports and dlopen blocked",
    }

    def blocked(reason):
        result["blocked_attempts"].append(reason)
        raise RuntimeError("Source-only guard: " + reason)

    class ImportGuard:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {
                "ctypes", "pybert", "pychopmarg", "numpy", "scipy", "parsec",
                "matplotlib", "traits", "traitsui", "chaco", "enable", "PySide6",
            }:
                blocked("import " + fullname)
            if fullname.startswith("pyibisami.") and fullname not in {
                "pyibisami.ami", "pyibisami.ami.model",
            }:
                blocked("import " + fullname)
            return None

    def audit(event, args):
        if event in ("ctypes.dlopen", "ctypes.dlsym"):
            blocked(event)

    def profile(frame, event, arg):
        if event == "call":
            filename = frame.f_code.co_filename.replace("\\", "/")
            if "/pyibisami/" in filename:
                if frame.f_code.co_name != "<module>" or filename.endswith("/ami/model.py"):
                    blocked("product Python execution " + frame.f_code.co_qualname)

    guard = ImportGuard()
    sys.meta_path.insert(0, guard)
    sys.addaudithook(audit)
    sys.setprofile(profile)
    try:
        assert Path(sys.prefix).resolve() == environment.resolve()
        assert sys.prefix != sys.base_prefix
        config = (environment / "pyvenv.cfg").read_text(encoding="utf-8").lower()
        assert "include-system-site-packages = false" in config
        import pyibisami  # pylint: disable=import-outside-toplevel

        package = Path(pyibisami.__file__).resolve().parent
        model = Path(util.find_spec("pyibisami.ami.model").origin).resolve()
        assert model == package / "ami/model.py"
        assert "pyibisami.ami.model" not in sys.modules
        result["package_module_file"] = pyibisami.__file__
        result["model_spec_origin"] = str(model)
        result["package_version"] = pyibisami.__version__
        distributions = {}
        for name in ("pipbert", "pyibis-ami", "pychopmarg"):
            dist = metadata.distribution(name)
            direct = dist.read_text("direct_url.json")
            distributions[name] = {
                "name": dist.metadata["Name"], "version": dist.version,
                "requires_dist": dist.requires, "metadata_root": str(dist.locate_file("")),
                "direct_url": json.loads(direct) if direct else None,
            }
        result["distributions"] = distributions
        assert distributions["pipbert"]["version"] == "11.1.0"
        assert distributions["pyibis-ami"]["version"] == expected["PyAMI_project"]["version"]
        assert distributions["pychopmarg"]["version"] == expected["PyChOpMarg_version"]
        requirements = distributions["pipbert"]["requires_dist"]
        assert any("pyibis-ami[gui]@git+https://github.com/yx520143-G/PyAMI.git@" + expected["F"]
                   in requirement.replace(" ", "") for requirement in requirements)
        ami_url = distributions["pyibis-ami"]["direct_url"]
        bert_url = distributions["pipbert"]["direct_url"]
        if route == "A":
            assert package == root / "PyAMI/src/pyibisami"
            assert ami_url["dir_info"]["editable"] is True
            assert Path(unquote(urlparse(ami_url["url"]).path).lstrip("/")).resolve() == root / "PyAMI"
            assert bert_url["dir_info"]["editable"] is True
            bert_package = root / "src/pybert"
        else:
            assert package.is_relative_to(environment)
            assert ami_url["url"] == "https://github.com/yx520143-G/PyAMI.git"
            assert ami_url["vcs_info"]["commit_id"] == expected["F"]
            assert ami_url["vcs_info"]["requested_revision"] == expected["F"]
            assert not bert_url.get("dir_info", {}).get("editable", False)
            bert_package = Path(metadata.distribution("pipbert").locate_file("pybert"))
            assert bert_package.is_relative_to(environment)
        result["PyBERT_source_directory_not_imported"] = str(bert_package)
        result["installed_python_source_sha256"] = {}
        for entries, parent in ((expected["python_sources"], package.parent),
                                (expected["pybert_python_sources"], bert_package.parent)):
            for relative, info in entries.items():
                source = parent / relative
                raw = source.read_bytes()
                digest = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
                assert digest == info["normalized_sha256"], str(source)
                result["installed_python_source_sha256"][str(source)] = {
                    "raw": hashlib.sha256(raw).hexdigest(), "LF_normalized": digest,
                }
        classes = {node.name: node for node in ast.parse(model.read_text(encoding="utf-8")).body
                   if isinstance(node, ast.ClassDef)}
        required = {"initialize", "getWave", "close", "last_getwave_calls", "last_init_call", "last_close_call"}
        present = {node.name for node in classes["AMIModel"].body if isinstance(node, ast.FunctionDef)}
        assert required <= present and "AMIModelError" in classes
        result["model_APIs_present_by_AST"] = sorted(required)
        result["gui_extra_installed_distributions"] = {
            re.match(r"[A-Za-z0-9_.-]+", requirement).group(): metadata.version(
                re.match(r"[A-Za-z0-9_.-]+", requirement).group()
            ) for requirement in expected["PyAMI_project"]["optional-dependencies"]["gui"]
        }
        assert not result["blocked_attempts"]
        result["status"] = "passed"
    except Exception:
        result["status"] = "failed"
        result["traceback"] = traceback.format_exc()
        raise
    finally:
        sys.setprofile(None)
        sys.meta_path.remove(guard)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"route": route, "status": result["status"], "package": str(package),
                      "verified_source_files": len(result["installed_python_source_sha256"])}))


if __name__ == "__main__":
    main()
