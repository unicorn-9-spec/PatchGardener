# Evidence assets

Seven screenshots and the actual silent demo have been captured. `video/demo_silent.mp4` is H.264/yuv420p, 1920×1080, 118.04 seconds, and decoded fully without errors. The original WebM is also retained locally. See `docs/video-evidence.json`.

All 3 Playwright tests and five zero-violation axe scans passed. The initial restricted-session browser blocker is resolved. The user chose Heart: `video/final_demo.mp4`, `audio/kokoro_voiceover.wav`, 34 timed SRT/ASS caption cues and verification reports are complete. Full decoding, exact audio/video durations, caption word coverage/order, loudness and clipping checks passed; representative captioned frames were inspected. Publication follows the explicit checkpoints in `BUILD_PROMPT.md`.
