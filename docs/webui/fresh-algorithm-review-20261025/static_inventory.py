"""Read Git objects with stdlib only; never import or execute product code."""

import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = "1bc905d577d2f3bd9471421cfbf3d422d4e6080e"
HEAD = "ab36b656a61cb6866da98105d72f6cacfb118031"


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", *args], cwd=cwd)


def symbols(content):
    result = {}

    def visit(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + child.name
                result[name] = {
                    "line": child.lineno,
                    "end": child.end_lineno,
                    "ast_sha256": hashlib.sha256(ast.dump(child, include_attributes=False).encode()).hexdigest(),
                }
                visit(child, name + ".")
            else:
                visit(child, prefix)

    visit(ast.parse(content))
    return result


def main():
    trees = {}
    for rev in (BASE, HEAD):
        entries = {}
        for row in git("ls-tree", "-r", rev).decode().splitlines():
            meta, path = row.split("\t")
            mode, kind, oid = meta.split()
            entries[path] = {"mode": mode, "kind": kind, "object": oid}
        trees[rev] = entries
    paths = sorted(set(trees[BASE]) | set(trees[HEAD]))
    products = [p for p in paths if p.startswith("src/") or p in (
        "PyAMI", "PyChOpMarg", "chaco", "pyproject.toml", "uv.lock", ".gitmodules",
        ".gitattributes", ".gitignore", ".pre-commit-config.yaml", "MANIFEST.in")]
    rows = []
    for path in products:
        old, new = trees[BASE].get(path), trees[HEAD].get(path)
        row = {"path": path, "base": old, "current": new, "status":
               "unchanged" if old == new else "added" if old is None else "removed" if new is None else "modified"}
        if row["status"] == "modified" and path.endswith(".py"):
            a, b = (symbols(git("show", f"{rev}:{path}")) for rev in (BASE, HEAD))
            row["symbols"] = [{"name": name, "base": a.get(name), "current": b.get(name), "ast_equal":
                               name in a and name in b and a[name]["ast_sha256"] == b[name]["ast_sha256"]}
                              for name in sorted(set(a) | set(b))]
        if row["status"] != "unchanged":
            row["commits"] = git("log", "--reverse", "--format=%h %s", f"{BASE}..{HEAD}", "--", path).decode().splitlines()
        rows.append(row)
    changes = git("diff", "--name-status", BASE, HEAD).decode().splitlines()
    dependencies = []
    for name, checkout in (
        ("PyAMI", Path("E:/serial-bus-simulator-dependencies/pyami-response-rng")),
        ("PyChOpMarg", Path("E:/serial-bus-simulator-dependencies/pybert-issue28-rng-pin/PyChOpMarg")),
    ):
        a, b = (trees[rev][name]["object"] for rev in (BASE, HEAD))
        current_tree = git("rev-parse", f"{b}^{{tree}}", cwd=checkout).decode().strip()
        checkout_tree = git("rev-parse", "HEAD^{tree}", cwd=checkout).decode().strip()
        dependency = {"name": name, "checkout": str(checkout), "base": a, "current": b,
                      "base_tree": git("rev-parse", f"{a}^{{tree}}", cwd=checkout).decode().strip(),
                      "current_tree": current_tree,
                      "checkout_head": git("rev-parse", "HEAD", cwd=checkout).decode().strip(),
                      "checkout_tree_matches_current": checkout_tree == current_tree,
                      "checkout_status": git("status", "--porcelain", cwd=checkout).decode(),
                      "commits": git("log", "--reverse", "--format=%h %s", f"{a}..{b}", cwd=checkout).decode().splitlines(),
                      "changed_sources": []}
        for path in git("diff", "--name-only", a, b, "--", "src/", cwd=checkout).decode().splitlines():
            before, after = (git("show", f"{rev}:{path}", cwd=checkout) for rev in (a, b))
            row = {"path": path, "base_sha256": hashlib.sha256(before).hexdigest(),
                   "current_sha256": hashlib.sha256(after).hexdigest()}
            if path.endswith(".py"):
                old_symbols, new_symbols = symbols(before), symbols(after)
                row["symbols"] = [{"name": symbol, "base": old_symbols.get(symbol),
                                   "current": new_symbols.get(symbol), "ast_equal":
                                   symbol in old_symbols and symbol in new_symbols
                                   and old_symbols[symbol]["ast_sha256"] == new_symbols[symbol]["ast_sha256"]}
                                  for symbol in sorted(set(old_symbols) | set(new_symbols))]
            dependency["changed_sources"].append(row)
        dependencies.append(dependency)
    result = {"base": BASE, "current": HEAD, "base_tree": git("rev-parse", f"{BASE}^{{tree}}").decode().strip(),
              "current_tree": git("rev-parse", f"{HEAD}^{{tree}}").decode().strip(), "scope":
              "Git blob identity plus unmodified whole-function AST (including docstrings). No observation stripping, no product imports, no numerical execution.",
              "change_counts": {prefix: sum(row.split("\t")[-1].startswith(prefix) for row in changes)
                                for prefix in ("src/", "docs/", "tests/", "tools/")},
              "products": rows, "dependencies": dependencies}
    Path(__file__).with_name("static-inventory.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"products": len(rows), "unchanged": sum(r["status"] == "unchanged" for r in rows),
                      "modified": sum(r["status"] == "modified" for r in rows),
                      "added": sum(r["status"] == "added" for r in rows), "change_counts": result["change_counts"]}))


if __name__ == "__main__":
    main()
