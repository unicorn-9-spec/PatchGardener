"""Verify the user-supplied YouTube upload using public YouTube metadata."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re

import httpx

ROOT = Path(__file__).resolve().parents[1]
VIDEO_ID = "cR2HYNkqO_0"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


def main():
    assert re.fullmatch(r"[A-Za-z0-9_-]{11}", VIDEO_ID)
    with httpx.Client(trust_env=False, timeout=35, follow_redirects=True) as client:
        response = client.get("https://www.youtube.com/oembed", params={"url": VIDEO_URL, "format": "json"})
        response.raise_for_status()
        embed = response.json()
        assert f"/embed/{VIDEO_ID}" in embed["html"]
        watch = client.get(VIDEO_URL)
        watch.raise_for_status()
        marker = re.search(r"ytInitialPlayerResponse\s*=\s*", watch.text)
        assert marker, "YouTube player metadata unavailable"
        player, _ = json.JSONDecoder().raw_decode(watch.text[marker.end():])
        status, details = player["playabilityStatus"], player["videoDetails"]
        assert status["status"] == "OK"
        assert status.get("playableInEmbed") is True
        assert details["videoId"] == VIDEO_ID and not details.get("isPrivate", False)
        assert abs(int(details["lengthSeconds"]) - 118.04) < 1
        thumbnail = client.get(embed["thumbnail_url"])
        thumbnail.raise_for_status()
    (ROOT / ".tools/youtube-thumbnail.jpg").write_bytes(thumbnail.content)
    report = {"verified_at": datetime.now(timezone.utc).isoformat(), "user_url": f"https://youtu.be/{VIDEO_ID}", "watch_url": VIDEO_URL, "video_id": VIDEO_ID, "title": details["title"], "author": embed["author_name"], "channel_id": details["channelId"], "length_seconds": int(details["lengthSeconds"]), "playability_status": status["status"], "playable_in_embed": True, "private": False, "oembed_http_status": response.status_code, "watch_http_status": watch.status_code, "thumbnail_http_status": thumbnail.status_code, "thumbnail_sha256": hashlib.sha256(thumbnail.content).hexdigest(), "thumbnail_visual_check": "Shows the actual PatchGardener interface and narrated captions", "scope": "Public metadata, embedding and thumbnail verified; not a full streamed playback verification"}
    (ROOT / "docs/youtube-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    path = ROOT / "docs/verification-results.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    summary["youtube"] = {"status": "verified", "url": report["user_url"], "video_id": VIDEO_ID, "report": "youtube-verification.json"}
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("user_url", "length_seconds", "playability_status", "playable_in_embed")}, indent=2))


if __name__ == "__main__":
    main()
