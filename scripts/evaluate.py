"""Real model evaluation; no mock replies. Run from the project root."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from backend.app import app
from backend.seed import GROUND_TRUTH
from backend.storage import now


def main():
    client = TestClient(app)
    health = client.get("/api/health").json()
    scan_response = client.post("/api/scans", json={"repository_id": "demo"})
    scan_response.raise_for_status()
    scan = scan_response.json()
    actual = {(issue["evidence"]["path"], issue["evidence"]["code"], issue["evidence"]["line"]) for issue in scan["issues"]}
    expected = {(item["path"], item["code"], item["line"]) for item in GROUND_TRUTH}
    results = []
    for issue in scan["issues"]:
        response = client.post("/api/proposals", json={"scan_id": scan["id"], "issue_id": issue["id"]})
        item = {"path": issue["evidence"]["path"], "code": issue["evidence"]["code"], "line": issue["evidence"]["line"], "withheld": issue["withheld"], "proposal_status": response.status_code}
        if response.status_code == 200:
            proposal = response.json()
            validated = client.post("/api/approvals", json={"proposal_id": proposal["id"], "approved": True})
            item.update({"proposal_id": proposal["id"], "inference_ms": proposal["inference_ms"], "diff": proposal["diff"], "validation_status": validated.status_code, "validation": validated.json() if validated.status_code == 200 else validated.text})
        else:
            item["error"] = response.text
        results.append(item)
        print(json.dumps({key: value for key, value in item.items() if key not in {"validation", "diff"}}), flush=True)
    eligible = [item for item in results if not item["withheld"]]
    report = {"measured_at": now(), "synthetic_fixture": True, "model": health["model"], "files": scan["files"], "scan_ms": scan["duration_ms"], "true_positives": len(actual & expected), "false_positives": len(actual - expected), "false_negatives": len(expected - actual), "precision": len(actual & expected) / len(actual) if actual else 0, "recall_in_scope": len(actual & expected) / len(expected), "eligible_proposals": len(eligible), "validated_passes": sum(item.get("validation", {}).get("verdict") == "passed" for item in eligible), "results": results}
    destination = Path("docs/evaluation-results.json")
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved measured report to {destination}")
    return 0 if report["validated_passes"] == len(eligible) and report["false_negatives"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
