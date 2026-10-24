import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from ruff import find_ruff_bin

from . import seed
from .schemas import Check, Issue, IssueEvidence, ModelReply, RiskReason
from .storage import uid

EXTENSIONS = {".py", ".md", ".ts", ".tsx", ".json", ".toml", ".txt"}
EXCLUDED = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build", "data", ".aws", ".codex", ".agents"}
SENSITIVE = re.compile(r"(^|[/_.-])(auth|payments?|security|infra|secrets?|migrations?|credentials?|tokens?|passwords?)([/_.-]|$)", re.I)
SECRET = re.compile(r"-----BEGIN .*PRIVATE KEY-----|(?:api[_-]?key|password|secret|(?:access[_-]?)?token|database[_-]?url|private[_-]?key)['\"]?\s*[:=]\s*['\"][^'\"]{8,}", re.I)
MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES = 200, 64_000, 1_000_000
RUFF_EXECUTABLE = find_ruff_bin()
GIT_EXECUTABLE = shutil.which("git")


def linked(path: Path) -> bool:
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def safe_path(root: Path, relative: str) -> Path:
    if "\\" in relative or ":" in relative or any(ord(char) < 32 for char in relative):
        raise ValueError("Unsafe file path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"..", ".", ""} for part in relative.split("/")):
        raise ValueError("Unsafe file path")
    if any(part.startswith(".") for part in pure.parts):
        raise ValueError("Hidden paths are excluded")
    root = root.resolve()
    candidate = root.joinpath(*pure.parts)
    if not candidate.resolve().is_relative_to(root):
        raise ValueError("File escapes repository root")
    current = root
    for part in pure.parts:
        current = current / part
        if current.exists() and linked(current):
            raise ValueError("Symlink or junction paths are excluded")
    return candidate


def index(root: Path) -> dict[str, str]:
    if linked(root):
        raise ValueError("Repository root must not be a symlink or junction")
    root = root.resolve()
    snapshot: dict[str, str] = {}
    total = 0
    visited = 0
    for folder, dirs, files in os.walk(root, followlinks=False):
        visited += 1
        if visited > 1000:
            raise ValueError("Repository exceeds directory limit (1000)")
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.startswith(".") and not linked(Path(folder) / d))
        for name in sorted(files):
            path = Path(folder) / name
            if name.startswith(".") or path.suffix.lower() not in EXTENSIONS or linked(path):
                continue
            if re.search(r"secret|credential|password|(?:^|[._-])env(?:[._-]|$)|lock$", name, re.I):
                continue
            rel = path.relative_to(root).as_posix()
            if re.search(r"(^|/)(secrets?|credentials?|passwords?|tokens?)(/|$)", rel, re.I):
                continue
            path = safe_path(root, rel)
            if path.stat().st_size > MAX_FILE_BYTES:
                raise ValueError(f"File exceeds 64 KB scan limit: {rel}")
            try:
                raw = path.read_bytes()
                if len(raw) > MAX_FILE_BYTES:
                    raise ValueError("File grew beyond scan limit")
                content = raw.decode("utf-8")
            except UnicodeError:
                continue
            if "\x00" in content or SECRET.search(content):
                continue
            total += len(raw)
            if len(snapshot) >= MAX_FILES or total > MAX_TOTAL_BYTES:
                raise ValueError("Repository exceeds scan limits (200 files / 1 MB)")
            snapshot[rel] = content
    return snapshot


def fingerprint(snapshot: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def materialize(root: Path, snapshot: dict[str, str]):
    root.mkdir(parents=True, exist_ok=False)
    for relative, content in snapshot.items():
        path = safe_path(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))


def command(name: str, argv: list[str], cwd: Path, timeout: int = 25) -> Check:
    """Internal fixed argv only. Never accept commands from repository or model."""
    start = time.monotonic()
    if argv[0] not in {sys.executable, RUFF_EXECUTABLE, GIT_EXECUTABLE}:
        raise ValueError("Executable is outside the internal tool allowlist")
    env = {key: value for key, value in os.environ.items() if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "SYSTEMDRIVE"}}
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(cwd), "USERPROFILE": str(cwd), "TEMP": str(cwd), "TMP": str(cwd), "NO_PROXY": "*", "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    env["GIT_CEILING_DIRECTORIES"] = str(cwd.resolve().parent)
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, shell=False, capture_output=True, timeout=timeout)
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        return Check(name=name, status="passed" if result.returncode == 0 else "failed", output=output[:24000], duration_ms=int((time.monotonic() - start) * 1000))
    except subprocess.TimeoutExpired:
        return Check(name=name, status="failed", output=f"Timed out after {timeout}s", duration_ms=timeout * 1000)


def ruff(root: Path, snapshot: dict[str, str]) -> Check:
    paths = sorted(path for path in snapshot if path.endswith(".py"))
    if not paths:
        return Check(name="Ruff", status="passed", output="[]", duration_ms=0)
    if not RUFF_EXECUTABLE:
        raise ValueError("Ruff is unavailable. Install requirements.txt and put ruff on PATH.")
    # Resolve the trusted tool at application startup, never from repository cwd.
    return command("Ruff", [RUFF_EXECUTABLE, "check", "--isolated", "--no-cache", "--select", "F401,F841", "--output-format", "json", "--", *paths], root)


def relative_target(path: str, target: str) -> str | None:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith(("#", "/")):
        return None
    decoded = unquote(parsed.path)
    if not decoded:
        return None
    pieces = list(PurePosixPath(path).parent.parts)
    for part in decoded.split("/"):
        if part == "..":
            if not pieces:
                return "<outside-repository>"
            pieces.pop()
        elif part not in {"", "."}:
            pieces.append(part)
    return "/".join(pieces)


def evidence_issue(path: str, line: int, column: int, tool: str, code: str, message: str, snapshot: dict[str, str]) -> Issue:
    lines = snapshot[path].splitlines()
    withheld = bool(SENSITIVE.search(path))
    return Issue(id=uid(), title=message, severity="medium" if code == "MD001" else "low", evidence=IssueEvidence(tool=tool, code=code, path=path, line=line, column=column, excerpt=lines[line - 1] if 0 < line <= len(lines) else "", message=message), withheld=withheld, reason="Protected path: requires a specialist review; proposals disabled." if withheld else None)


def markdown_issues(snapshot: dict[str, str]) -> list[Issue]:
    issues = []
    for path, text in snapshot.items():
        if not path.endswith(".md"):
            continue
        fenced = False
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if not fenced:
                for match in re.finditer(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+['\"].*?['\"])?\)", line):
                    target = relative_target(path, match[1].strip("<>"))
                    if target and target not in snapshot and not any(file.startswith(target.rstrip("/") + "/") for file in snapshot):
                        issues.append(evidence_issue(path, number, match.start() + 1, "Markdown links", "MD001", f"Broken relative link: {match[1]}", snapshot))
            for match in re.finditer(r"\bpython(?:3)?\s+([\w./-]+\.py)\b", line):
                # Commands are interpreted from repository root, not document folder.
                target = relative_target("README.md", match[1])
                if target and target not in snapshot:
                    issues.append(evidence_issue(path, number, match.start() + 1, "Example paths", "CMD001", f"Missing Python example: {match[1]}", snapshot))
    return issues


def scan_files(root: Path, snapshot: dict[str, str]) -> tuple[list[Issue], list[Check]]:
    check = ruff(root, snapshot)
    try:
        findings = json.loads(check.output)
        if not isinstance(findings, list):
            raise ValueError("Ruff did not return a findings array")
    except (json.JSONDecodeError, ValueError):
        raise ValueError(f"Ruff scan failed: {check.output[:300]}")
    issues = []
    for finding in findings:
        path = Path(finding["filename"]).resolve().relative_to(root.resolve()).as_posix()
        if path in snapshot:
            issues.append(evidence_issue(path, finding["location"]["row"], finding["location"]["column"], "Ruff", finding["code"], finding["message"], snapshot))
    md = markdown_issues(snapshot)
    issues.extend(md)
    md_check = Check(name="Markdown & example paths", status="failed" if md else "passed", output="\n".join(f"{issue.evidence.path}:{issue.evidence.line} {issue.title}" for issue in md) or "All relative links and Python example paths resolve.", duration_ms=0)
    return issues, [check, md_check]


def patch_gate(snapshot: dict[str, str], issue: Issue, reply: ModelReply) -> tuple[dict[str, str], str, int, list[RiskReason]]:
    if issue.withheld or SENSITIVE.search(issue.evidence.path):
        raise ValueError("Protected path: proposals are withheld")
    after = dict(snapshot)
    for edit in reply.edits:
        safe_path(Path.cwd(), edit.path)
        if edit.path != issue.evidence.path or edit.path not in snapshot:
            raise ValueError("Edits must target only the selected evidence file")
        if after[edit.path].count(edit.old) != 1:
            raise ValueError("Edit old text must match exactly once")
        if edit.old == edit.new or SECRET.search(edit.new):
            raise ValueError("Empty or secret-bearing edit rejected")
        after[edit.path] = after[edit.path].replace(edit.old, edit.new, 1)
    path = issue.evidence.path
    if after[path] == snapshot[path]:
        raise ValueError("Proposal makes no change")
    reasons = [RiskReason(rule="scope", explanation="One evidence file; no file creation, deletion, or protected paths."), RiskReason(rule="execution", explanation="No model-supplied commands are executed.")]
    if path.endswith(".py"):
        if issue.evidence.code != "F401":
            raise ValueError("P0 only permits proven unused-import removal in Python")
        before_tree = ast.parse(snapshot[path])
        target = next((node for node in before_tree.body if isinstance(node, (ast.Import, ast.ImportFrom)) and node.lineno == issue.evidence.line and len(node.names) == 1), None)
        if target is None:
            raise ValueError("Only single-name top-level unused imports are supported")
        source_lines = snapshot[path].splitlines(keepends=True)
        first, last = target.lineno - 1, target.end_lineno - 1
        start = sum(len(line) for line in source_lines[:first])
        end = sum(len(line) for line in source_lines[:last]) + len(source_lines[last].encode("utf-8")[:target.end_col_offset].decode("utf-8"))
        exact_deletions = {
            snapshot[path][:start] + snapshot[path][end:],
            "".join(source_lines[:first] + source_lines[last + 1:]),
        }
        if after[path] not in exact_deletions:
            raise ValueError("Only exact import deletion is permitted; new comments, encoding declarations and formatting changes are prohibited")
        before_tree.body.remove(target)
        if ast.dump(before_tree, include_attributes=False) != ast.dump(ast.parse(after[path]), include_attributes=False):
            raise ValueError("Python logic changes are prohibited; remove only the reported import")
        reasons.append(RiskReason(rule="syntax", explanation="AST comparison permits only removal of the exact reported unused import; import side effects still need review."))
    elif not path.endswith(".md"):
        raise ValueError("P0 proposals support Python imports and Markdown only")
    else:
        reasons.append(RiskReason(rule="documentation", explanation="Documentation only; links are rechecked after approval."))
    diff = "".join(difflib.unified_diff(snapshot[path].splitlines(keepends=True), after[path].splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}"))
    if not snapshot[path].endswith("\n") or not after[path].endswith("\n"):
        raise ValueError("P0 patch export requires a trailing newline")
    lines = sum(1 for line in diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    if lines > 24 or len(diff) > 16000:
        raise ValueError("Patch exceeds 24 changed lines / 16 KB")
    if not diff.startswith(f"--- a/{path}\n+++ b/{path}\n@@"):
        raise ValueError("Invalid unified diff")
    reasons.append(RiskReason(rule="size", explanation=f"{lines} changed line(s); maximum 24. Risk is categorical, not a safety probability."))
    return after, diff, lines, reasons


def fixture_tests(root: Path, trusted: bool) -> Check:
    if not trusted:
        return Check(name="Fixture unit tests", status="skipped", output="User repository code is never executed. Static checks only; use an OS/container sandbox for untrusted tests.", duration_ms=0)
    code = "import sys, unittest; sys.path.insert(0, sys.argv[1]); suite=unittest.defaultTestLoader.discover(sys.argv[1]+'/tests'); result=unittest.TextTestRunner(verbosity=2).run(suite); sys.exit(not result.wasSuccessful())"
    return command("Fixture unit tests", [sys.executable, "-I", "-c", code, str(root.resolve())], root)


def trusted_fixture(snapshot: dict[str, str]) -> bool:
    return snapshot == seed.FILES


def diff_applicability(root: Path, patch: Path) -> Check:
    if not GIT_EXECUTABLE:
        raise ValueError("Git is required for unified diff validation")
    return command("Unified diff applicability", [GIT_EXECUTABLE, "apply", "--check", "--", str(patch.resolve())], root)


def signatures(issues: list[Issue]) -> set[tuple[str, str, str]]:
    return {(item.evidence.path, item.evidence.code, item.evidence.message) for item in issues}
