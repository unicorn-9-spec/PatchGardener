"""Verify the approved public repository and commit-pinned screenshot bytes."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OWNER, REPOSITORY = "unicorn-9-spec", "PatchGardener"
SCREENSHOT_COMMIT = "ff8c76781bdaf9e96bab5371aa84c0fa939531dd"


def verify_image(path: Path):
    url = f"https://raw.githubusercontent.com/{OWNER}/{REPOSITORY}/{SCREENSHOT_COMMIT}/demo/assets/screenshots/{path.name}"
    with httpx.Client(trust_env=False, timeout=30, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    assert response.headers.get("content-type", "").startswith("image/png")
    digest = hashlib.sha256(response.content).hexdigest()
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest(), path.name
    return {"file": path.name, "url": url, "http_status": response.status_code, "bytes": len(response.content), "sha256": digest}


def main():
    url = f"https://github.com/{OWNER}/{REPOSITORY}"
    with httpx.Client(trust_env=False, timeout=30, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        metadata = client.get(f"https://api.github.com/repos/{OWNER}/{REPOSITORY}")
        metadata.raise_for_status()
        repository = metadata.json()
        assert repository["private"] is False
        assert repository["default_branch"] == "main"
        branch = client.get(f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/branches/main")
        branch.raise_for_status()
        head = branch.json()["commit"]["sha"]
    paths = sorted((ROOT / "demo/assets/screenshots").glob("*.png"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        images = list(pool.map(verify_image, paths))
    youtube_path = ROOT / "docs/youtube-verification.json"
    youtube = json.loads(youtube_path.read_text(encoding="utf-8"))["user_url"] if youtube_path.exists() else "pending user upload and actual URL"
    report = {"verified_at": datetime.now(timezone.utc).isoformat(), "repository": url, "public": True, "branch": "main", "observed_branch_head": head, "screenshot_commit": SCREENSHOT_COMMIT, "screenshots": images, "youtube": youtube}
    (ROOT / "docs/publication-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_path = ROOT / "docs/verification-results.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["github_publication"] = {"status": "verified", "repository": url, "public": True, "branch": "main", "screenshot_commit": SCREENSHOT_COMMIT, "report": "publication-results.json"}
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"repository": url, "public": True, "branch": "main", "head": head, "screenshots_verified": len(images)}, indent=2))


if __name__ == "__main__":
    main()
