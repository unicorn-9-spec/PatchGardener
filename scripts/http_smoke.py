"""Exercise the actual production Next.js proxy and real Qwen inference."""
import json
from pathlib import Path

import httpx


def main():
    checks = []
    with httpx.Client(base_url="http://127.0.0.1:3105", trust_env=False, timeout=210) as client:
        page = client.get("/")
        assert page.status_code == 200 and "Less tending." in page.text
        checks.append("Production HTML served")
        health = client.get("/api/health").json()
        assert health["model"]["available"]
        checks.append("Live local model status through same-origin proxy")
        scan_response = client.post("/api/scans", json={"repository_id": "demo"})
        scan_response.raise_for_status()
        scan = scan_response.json()
        assert len(scan["issues"]) == 5
        checks.append("Actual scanners through proxy: five findings")
        issue = next(item for item in scan["issues"] if item["evidence"]["path"] == "meadow.py" and item["evidence"]["line"] == 1)
        response = client.post("/api/proposals", json={"scan_id": scan["id"], "issue_id": issue["id"]})
        response.raise_for_status()
        proposal = response.json()
        assert proposal["model_digest"] == health["model"]["digest"]
        checks.append("Real Qwen structured proposal through proxy")
        denied = client.post("/api/approvals", json={"proposal_id": proposal["id"], "approved": False})
        assert denied.status_code == 422
        checks.append("Approval required")
        response = client.post("/api/approvals", json={"proposal_id": proposal["id"], "approved": True})
        response.raise_for_status()
        run = response.json()
        assert run["verdict"] == "passed" and run["source_unchanged"]
        assert run["checks"][-1]["status"] == "passed"
        checks.append("Isolated validation, unchanged original, real fixture tests passed")
        exported = client.get(f'/api/exports/{proposal["id"]}')
        assert exported.text == proposal["diff"] and "attachment;" in exported.headers["content-disposition"]
        checks.append("Exact downloadable patch")
        assert client.post("/api/scans", json={}, headers={"Origin": "https://evil.example"}).status_code == 403
        checks.append("Cross-origin mutation blocked")
    report = {"synthetic_fixture": True, "checks": checks, "model": health["model"], "inference_ms": proposal["inference_ms"], "validation": run}
    Path("docs/http-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": len(checks), "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
