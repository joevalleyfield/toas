from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class CodeSurveyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.class_stack: list[str] = []
        self.functions: list[dict[str, Any]] = []
        self.classes: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        start = int(getattr(node, "lineno", 1))
        end = int(getattr(node, "end_lineno", start))
        self.classes.append(
            {
                "name": ".".join(self.class_stack + [node.name]),
                "start_line": start,
                "end_line": end,
                "lines": max(1, end - start + 1),
            }
        )
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node)
        self.generic_visit(node)

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        start = int(getattr(node, "lineno", 1))
        end = int(getattr(node, "end_lineno", start))
        self.functions.append(
            {
                "name": ".".join(self.class_stack + [node.name]),
                "start_line": start,
                "end_line": end,
                "lines": max(1, end - start + 1),
            }
        )


def collect_code_survey_entries(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    content = path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    visitor = CodeSurveyVisitor()
    visitor.visit(tree)
    return visitor.functions, visitor.classes


def format_code_survey_content(
    files_top: list[dict[str, Any]],
    functions_top: list[dict[str, Any]],
    classes_top: list[dict[str, Any]],
    skipped: list[dict[str, str]],
) -> str:
    lines: list[str] = []
    lines.append("top files by lines:")
    for item in files_top:
        lines.append(f"- {item['lines']:>5}  {item['path']}")
    lines.append("")
    lines.append("top functions by lines:")
    for item in functions_top:
        lines.append(
            f"- {item['lines']:>5}  {item['path']}:{item['name']} ({item['start_line']}-{item['end_line']})"
        )
    lines.append("")
    lines.append("top classes by lines:")
    for item in classes_top:
        lines.append(
            f"- {item['lines']:>5}  {item['path']}:{item['name']} ({item['start_line']}-{item['end_line']})"
        )
    if skipped:
        lines.append("")
        lines.append("skipped files:")
        for item in skipped:
            lines.append(f"- {item['path']}: {item['error']}")
    return "\n".join(lines)


def run_code_survey(args: dict, *, workspace_path_fn) -> dict:
    path_arg = args.get("path", "src")
    top_n = args.get("top_n", 20)
    if not isinstance(path_arg, str) or not path_arg.strip():
        raise RuntimeError("invalid arguments for tool code_survey: path must be a non-empty string")
    if not isinstance(top_n, int) or top_n < 1 or top_n > 200:
        raise RuntimeError("invalid arguments for tool code_survey: top_n must be an int between 1 and 200")

    path = workspace_path_fn(path_arg)
    if path.is_file():
        candidates = [path] if path.suffix == ".py" else []
    elif path.is_dir():
        candidates = sorted(p for p in path.rglob("*.py") if p.is_file())
    else:
        raise RuntimeError(f"tool code_survey requires a file or directory: {path_arg}")

    file_entries: list[dict[str, Any]] = []
    function_entries: list[dict[str, Any]] = []
    class_entries: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for candidate in candidates:
        rel = str(candidate.relative_to(Path.cwd()))
        line_count = len(candidate.read_text(encoding="utf-8").splitlines())
        file_entries.append({"path": rel, "lines": line_count})
        try:
            funcs, classes = collect_code_survey_entries(candidate)
        except (SyntaxError, UnicodeDecodeError) as exc:
            skipped.append({"path": rel, "error": str(exc)})
            continue
        for item in funcs:
            function_entries.append({**item, "path": rel})
        for item in classes:
            class_entries.append({**item, "path": rel})

    files_top = sorted(file_entries, key=lambda item: (-item["lines"], item["path"]))[:top_n]
    functions_top = sorted(
        function_entries, key=lambda item: (-item["lines"], item["path"], item["start_line"])
    )[:top_n]
    classes_top = sorted(class_entries, key=lambda item: (-item["lines"], item["path"], item["start_line"]))[:top_n]
    content = format_code_survey_content(files_top, functions_top, classes_top, skipped)
    return {
        "tool_name": "code_survey",
        "ok": True,
        "summary": (
            f"{len(candidates)} python file(s), "
            f"{len(function_entries)} function(s), "
            f"{len(class_entries)} class(es)"
        ),
        "path": path_arg,
        "top_n": top_n,
        "files_top": files_top,
        "functions_top": functions_top,
        "classes_top": classes_top,
        "skipped": skipped,
        "content": content,
    }
