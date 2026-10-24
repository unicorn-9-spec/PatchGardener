"""Review and bundle the source without reading ignored local data or credentials."""
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", ".tools", ".next", ".cache", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "data", "logs", "node_modules", "test-results", "playwright-report"}
PATTERNS = {
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "Credential in URL": re.compile(r"https?://[^\s/@:\"']+:[^\s/@\"']+@"),
}


def main():
    files, findings = [], []
    for directory, dirs, names in os.walk(ROOT, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name not in IGNORED_DIRS and not name.startswith(".test-tmp") and not (Path(directory) / name).is_symlink())
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(ROOT).as_posix()
            if path.is_symlink() or name.endswith((".pyc", ".tsbuildinfo", ".mp4", ".webm", ".wav")):
                continue
            if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
                raise RuntimeError(f"Environment file unexpectedly entered source selection: {relative}")
            content = path.read_bytes()
            try:
                text = content.decode("utf-8-sig")
            except UnicodeError:
                text = ""
            for label, pattern in PATTERNS.items():
                for match in pattern.finditer(text):
                    findings.append({"path": relative, "line": text[:match.start()].count("\n") + 1, "kind": label})
            files.append({"path": relative, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    report = {"files": files, "total_files": len(files), "total_bytes": sum(item["bytes"] for item in files), "high_confidence_secret_findings": findings, "excluded": sorted(IGNORED_DIRS) + [".test-tmp*", "*.pyc", "*.tsbuildinfo", "*.mp4", "*.webm", "*.wav"], "publication": "Source-only review; this script performs no external writes"}
    review = ROOT / ".tools/publication"
    review.mkdir(parents=True, exist_ok=True)
    (review / "review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if findings:
        print(json.dumps({"findings": findings}, indent=2))
        raise SystemExit("Publication source needs review; no archive written")
    archive = review / "PatchGardener-source.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for item in files:
            bundle.write(ROOT / item["path"], item["path"])
    print(json.dumps({"files_reviewed": len(files), "source_bytes": report["total_bytes"], "high_confidence_secret_findings": len(findings), "review": str(review / "review.json"), "source_archive": str(archive), "archive_bytes": archive.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
