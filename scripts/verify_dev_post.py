"""Read-only verification of the user's published DEV article."""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import httpx

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = "ali_hamza_4bd92ee9f67e78702"
SLUG = "i-built-an-ai-gardener-for-the-boring-work-every-open-source-maintainer-avoids-4doc"
URL = f"https://dev.to/{AUTHOR}/{SLUG}"


class ArticleHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images, self.frames = [], []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "img":
            self.images.append({"url": attrs.get("src"), "alt": attrs.get("alt", "")})
        if tag == "iframe":
            self.frames.append(attrs.get("src"))


def check_image(image):
    assert image["url"].startswith("https://media2.dev.to/")
    with httpx.Client(trust_env=False, timeout=30, follow_redirects=True) as client:
        response = client.get(image["url"])
        response.raise_for_status()
    assert response.headers.get("content-type", "").startswith("image/")
    return {**image, "http_status": response.status_code, "bytes": len(response.content), "content_type": response.headers.get("content-type"), "sha256": hashlib.sha256(response.content).hexdigest()}


def main():
    with httpx.Client(trust_env=False, timeout=30, follow_redirects=True) as client:
        page = client.get(URL)
        page.raise_for_status()
        response = client.get(f"https://dev.to/api/articles/{AUTHOR}/{SLUG}", headers={"accept": "application/vnd.forem.api-v1+json"})
        response.raise_for_status()
        article = response.json()
    assert article["published_at"] and article["url"] == URL
    assert {"devchallenge", "hf26challenge"}.issubset(set(article["tags"]))
    markdown = article["body_markdown"]
    headings = re.findall(r"^## (.+)$", markdown, re.M)
    expected = ["What I Built", "Demo", "Code", "How I Built It", "Why Does Open Innovation Matter?", "The Lazy Payoff", "Prize Categories"]
    assert headings == expected
    assert "{% youtube cR2HYNkqO_0 %}" in markdown
    assert "https://github.com/unicorn-9-spec/PatchGardener" in markdown
    source_images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    verified = json.loads((ROOT / "docs/submission-verification.json").read_text(encoding="utf-8"))
    assert source_images == verified["verified_screenshot_urls"]
    parser = ArticleHTML()
    parser.feed(article["body_html"])
    assert "https://www.youtube.com/embed/cR2HYNkqO_0" in parser.frames
    assert len(parser.images) >= 4
    with ThreadPoolExecutor(max_workers=4) as pool:
        images = list(pool.map(check_image, parser.images))
    local = (ROOT / "docs/DEV_SUBMISSION.md").read_text(encoding="utf-8")
    local_body = local[local.index("*This is a submission"):].strip()
    matches = markdown.strip() == local_body
    report = {"verified_at": datetime.now(timezone.utc).isoformat(), "url": URL, "article_id": article["id"], "title": article["title"], "author": AUTHOR, "published_at": article["published_at"], "published_by": "user", "page_http_status": page.status_code, "api_http_status": response.status_code, "tags": article["tags"], "required_challenge_tags_present": True, "headings": headings, "youtube_iframe": "https://www.youtube.com/embed/cR2HYNkqO_0", "repository": "https://github.com/unicorn-9-spec/PatchGardener", "source_images": source_images, "rendered_images": images, "body_matches_local_submission": matches, "published_body_sha256": hashlib.sha256(markdown.strip().encode()).hexdigest(), "verification_scope": "Published HTML and official public API; required tags/headings, video iframe, repository link and rendered screenshot HTTP responses"}
    (ROOT / "docs/dev-publication-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    verified.update(status="published_by_user", published_to_dev=True, published_url=URL, publication_report="dev-publication-verification.json")
    (ROOT / "docs/submission-verification.json").write_text(json.dumps(verified, indent=2), encoding="utf-8")
    path = ROOT / "docs/verification-results.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    summary["dev_article"] = {"status": "published_and_verified", "url": URL, "published_by": "user", "published_to_dev": True, "report": "dev-publication-verification.json"}
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"published_url": URL, "required_tags": True, "video_embed": True, "rendered_screenshots_verified": len(images), "body_matches_local_submission": matches}, indent=2))


if __name__ == "__main__":
    main()
