from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import engine, seed
from backend.app import create_app
from backend.schemas import Edit, ModelReply


@pytest.fixture
def fixture_repo(tmp_path):
    root = tmp_path / "repo"
    engine.materialize(root, seed.FILES)
    return root


@pytest.fixture
def issue(fixture_repo):
    issues, _ = engine.scan_files(fixture_repo, seed.FILES)
    return next(item for item in issues if item.evidence.path == "meadow.py" and item.evidence.line == 1)


def test_exact_ground_truth(fixture_repo):
    issues, checks = engine.scan_files(fixture_repo, seed.FILES)
    actual = {(item.evidence.path, item.evidence.code, item.evidence.line) for item in issues}
    expected = {(item["path"], item["code"], item["line"]) for item in seed.GROUND_TRUTH}
    assert actual == expected
    assert len([item for item in issues if item.withheld]) == 1
    assert engine.fixture_tests(fixture_repo, True).status == "passed"


@pytest.mark.parametrize("path", ["../outside.py", "/etc/passwd", "C:/escape.py", "a\\b.py", "a/../../b.py", ".env", "a//b.py", "a/./b.py"])
def test_path_traversal(tmp_path, path):
    with pytest.raises(ValueError):
        engine.safe_path(tmp_path, path)


def test_symlink_excluded(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("private = 42\n")
    try:
        (root / "linked.py").symlink_to(outside)
    except OSError:
        pytest.skip("Windows account lacks symlink privilege")
    assert engine.index(root) == {}
    with pytest.raises(ValueError):
        engine.safe_path(root, "linked.py")


def test_secrets_not_stored(tmp_path):
    (tmp_path / "plain.py").write_text('api_key = "private-not-a-real-token"\n')
    (tmp_path / "credentials.json").write_text('{"x": "private"}')
    assert engine.index(tmp_path) == {}


def test_json_and_secret_directories_not_stored(tmp_path):
    (tmp_path / "settings.json").write_text('{"api_key": "not-a-real-key-1234"}')
    folder = tmp_path / "secrets"
    folder.mkdir()
    (folder / "plain.txt").write_text("otherwise unidentifiable private content")
    assert engine.index(tmp_path) == {}


def test_import_gate_accepts_exact_removal(issue):
    reply = ModelReply(summary="Remove unused os import", edits=[Edit(path="meadow.py", old="import os\n", new="")])
    after, diff, lines, _ = engine.patch_gate(seed.FILES, issue, reply)
    assert after["meadow.py"].startswith("import json\n")
    assert "-import os" in diff
    assert lines == 1


@pytest.mark.parametrize("old,new,path", [
    ("import os\n", "import subprocess\n", "meadow.py"),
    ("import os", "# coding: unicode_escape\n# \\x0aprint('injected')", "meadow.py"),
    ("import os\n", "", "../meadow.py"),
    ("import os\n", "", "auth/session.py"),
    ("import os\nimport json\n", "", "meadow.py"),
    ("not present", "", "meadow.py"),
])
def test_gate_rejects_scope_and_logic(issue, old, new, path):
    with pytest.raises(ValueError):
        engine.patch_gate(seed.FILES, issue, ModelReply(summary="Malicious edit", edits=[Edit(path=path, old=old, new=new)]))


def test_external_tests_never_execute(fixture_repo):
    check = engine.fixture_tests(fixture_repo, False)
    assert check.status == "skipped"


def test_modified_fixture_loses_execution_trust():
    modified = dict(seed.FILES)
    modified["tests/test_meadow.py"] += "\n# user modification\n"
    assert not engine.trusted_fixture(modified)


def test_runner_rejects_unknown_executable(tmp_path):
    with pytest.raises(ValueError, match="allowlist"):
        engine.command("Injected command", ["unknown-executable", "anything"], tmp_path)


def test_approval_and_source_immutability(tmp_path, monkeypatch):
    # Unit fixture reply only; real inference is verified separately in evaluate.py.
    from backend.model import LocalModel
    monkeypatch.setattr(LocalModel, "propose", lambda self, issue, snapshot: (ModelReply(summary="Unit fixture", edits=[Edit(path="meadow.py", old="import os\n", new="")]), 1, "unit-test-only"))
    app = create_app(tmp_path / "data")
    client = TestClient(app)
    scan = client.post("/api/scans", json={"repository_id": "demo"}).json()
    item = next(item for item in scan["issues"] if item["evidence"]["path"] == "meadow.py" and item["evidence"]["line"] == 1)
    proposal = client.post("/api/proposals", json={"scan_id": scan["id"], "issue_id": item["id"]}).json()
    assert client.post("/api/approvals", json={"proposal_id": proposal["id"], "approved": False}).status_code == 422
    result = client.post("/api/approvals", json={"proposal_id": proposal["id"], "approved": True})
    assert result.status_code == 200, result.text
    run = result.json()
    assert run["verdict"] == "passed"
    assert run["resolved"] == 1 and run["regressions"] == 0
    assert run["source_unchanged"] is True
    assert Path(scan["repository"]["path"], "meadow.py").read_text() == seed.FILES["meadow.py"]
    assert Path(run["copy_path"], "meadow.py").read_text().startswith("import json")
    assert client.post("/api/approvals", json={"proposal_id": proposal["id"], "approved": True}).status_code == 400
    assert client.get(f'/api/exports/{proposal["id"]}').text == proposal["diff"]


def test_stale_approval_and_cross_origin(tmp_path, monkeypatch):
    from backend.model import LocalModel
    monkeypatch.setattr(LocalModel, "propose", lambda self, issue, snapshot: (ModelReply(summary="Unit fixture", edits=[Edit(path="meadow.py", old="import os\n", new="")]), 1, "unit-test-only"))
    client = TestClient(create_app(tmp_path / "data"))
    scan = client.post("/api/scans", json={}).json()
    item = next(item for item in scan["issues"] if item["evidence"]["path"] == "meadow.py" and item["evidence"]["line"] == 1)
    proposal = client.post("/api/proposals", json={"scan_id": scan["id"], "issue_id": item["id"]}).json()
    Path(scan["repository"]["path"], "meadow.py").write_text("# changed\n")
    assert client.post("/api/approvals", json={"proposal_id": proposal["id"], "approved": True}).status_code == 400
    assert client.post("/api/scans", json={}, headers={"origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 400


def test_snapshot_limits(tmp_path):
    (tmp_path / "huge.md").write_text("a" * (engine.MAX_FILE_BYTES + 1))
    with pytest.raises(ValueError, match="64 KB"):
        engine.index(tmp_path)


def test_model_restriction():
    from backend.model import LocalModel
    with pytest.raises(ValueError):
        LocalModel("https://remote.example", "qwen3:8b")
    with pytest.raises(ValueError):
        LocalModel("http://127.0.0.1:11434", "gemma3:4b")
