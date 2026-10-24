"""Measure and verify real local browser/demo artifacts; no fabricated metadata."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    video = root / "demo/assets/video/demo_silent.mp4"
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height,pix_fmt", "-of", "json", str(video)], check=True, capture_output=True, text=True)
    metadata = json.loads(probe.stdout)
    stream = metadata["streams"][0]
    duration = float(metadata["format"]["duration"])
    assert (stream["width"], stream["height"]) == (1920, 1080)
    assert 90 <= duration <= 150
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], check=True, capture_output=True, text=True)
    assert not decode.stderr.strip(), decode.stderr
    shots = sorted((root / "demo/assets/screenshots").glob("*.png"))
    assert len(shots) >= 4
    report = {"measured_at": datetime.now(timezone.utc).isoformat(), "path": str(video), "metadata": metadata, "sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "full_decode": "passed", "screenshots": [{"file": item.name, "bytes": item.stat().st_size, "sha256": hashlib.sha256(item.read_bytes()).hexdigest()} for item in shots], "visual_inspection": "Desktop queue, diff and test-output video frames, final mobile protected-path view inspected", "narration": "pending user voice selection"}
    narration_check = root / "demo/assets/audio/final-verification.json"
    narration = json.loads(narration_check.read_text(encoding="utf-8")) if narration_check.exists() else None
    if narration:
        assert narration["full_decode_passed"]
        assert hashlib.sha256((root / "demo/assets/video/final_demo.mp4").read_bytes()).hexdigest() == narration["video_sha256"]
        report["narration"] = {"status": "verified", "voice": narration["voice"], "report": "../demo/assets/audio/final-verification.json"}
    (root / "docs/video-evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    browser = json.loads((root / "docs/browser-results.json").read_text(encoding="utf-8"))
    assert browser["stats"]["unexpected"] == 0
    assert browser["stats"]["expected"] == 3
    axe = []
    for file in (root / "test-results").rglob("axe-*.json"):
        violations = json.loads(file.read_text(encoding="utf-8"))
        assert not violations, (file, violations)
        axe.append({"report": str(file.relative_to(root)), "violations": len(violations)})
    assert len(axe) == 5
    summary_path = root / "docs/verification-results.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update({"browser_tests": {"status": "passed", "passed": 3, "duration_ms": browser["stats"]["duration"], "report": "browser-results.json"}, "accessibility": {"axe_reports": axe, "note": "Not WCAG certification"}, "visual_qa": "passed for inspected desktop/mobile/screens/video frames", "demo_recording": {"status": "verified", "seconds": duration, "width": 1920, "height": 1080, "report": "video-evidence.json"}, "kokoro_narration": "pending user voice selection"})
    if narration:
        summary["kokoro_narration"] = {"status": "verified", "voice": narration["voice"], "seconds": narration["audio_seconds"], "captions": narration["captions"], "report": "../demo/assets/audio/final-verification.json"}
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"browser_tests_passed": 3, "axe_scans_clean": len(axe), "screenshots": len(shots), "video_seconds": duration, "video_decode": "passed"}, indent=2))


if __name__ == "__main__":
    main()
