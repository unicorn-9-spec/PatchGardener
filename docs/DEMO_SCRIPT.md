# Actual application demonstration plan

Status: actual recording and Heart narration completed and verified on 24 October 2026. `demo/assets/video/final_demo.mp4` is 118.04 seconds at 1920×1080, with audio, burned captions and a selectable subtitle track. Full decoding passed. Source and seven actual screenshots are published at [unicorn-9-spec/PatchGardener](https://github.com/unicorn-9-spec/PatchGardener). The user uploaded the narrated video to [YouTube](https://youtu.be/cR2HYNkqO_0); playability, embedding, duration and thumbnail are verified.

## Reproduce

1. Start FastAPI on port 8105 and the production Next.js frontend on 3105.
2. Verify `qwen3:8b` is available locally; run `python scripts/evaluate.py`.
3. In a normal local terminal, install the Playwright browser with `npx playwright install chromium` and run `npm run test:e2e`. Resolve any real UI/accessibility failures before recording.
4. Run `npm run demo:record`. No mocks/interception are present. The fixture is explicitly labeled synthetic in the UI.
5. Convert with `ffmpeg -y -i demo/assets/video/demo_silent.webm -c:v libx264 -pix_fmt yuv420p -an demo/assets/video/demo_silent.mp4`.
6. Verify with `ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of json demo/assets/video/demo_silent.mp4` and `ffmpeg -v error -i demo/assets/video/demo_silent.mp4 -f null -`.

The script targets 1920×1080 and approximately 110–130 seconds depending on model and validation time. Actual duration must be measured. Screenshots are captured from the running app under `demo/assets/screenshots/`; no image-generation tool is used.

## Narrative beats

| Approximate interval | On-screen evidence | Story |
|---|---|---|
| 0–10 s | Live model status, untouched repository garden | A maintainer has a small cleanup task they keep postponing. |
| 10–22 s | Scan actual nine-file synthetic repository | Static tools find precise maintenance issues. |
| 22–34 s | Protected `auth/session.py` issue | Some paths are intentionally held for specialist review. |
| 34–45 s | `meadow.py:1` and Ruff excerpt | Every proposal begins with file/line/tool evidence. |
| 45–65 s | Fresh real Qwen inference, actual side-by-side diff | Open-weight AI proposes a bounded edit locally. |
| 65–80 s | Risk explanations and initially disabled approval | Import removal can have side effects; the human reviews it. |
| 80–100 s | Approved separate copy, baseline and post-change results | Selected issue resolved, no regressions, source unchanged. |
| 100–115 s | Expand actual test output and export patch | Passing tests and a portable artifact, no automatic push. |
| 115–125 s | Local audit and return to garden | The small task becomes a reviewable unit of work. |

## Narration and publication handoff

The user chose Heart (`af_heart`). `demo/assets/audio/narration_script.md` and `narration_timeline.json` preserve the spoken text and actual scene timing; `kokoro_voiceover.wav`, SRT/ASS captions and `demo/assets/video/final_demo.mp4` are generated. Audio/video duration, word coverage, nonoverlapping subtitle cues, loudness, clipping, full decode and representative captioned frames have been checked. See [voiceover notes](VOICEOVER.md).

The user supplied https://youtu.be/cR2HYNkqO_0. The usable ID, official embed, playability, rounded 118-second duration and matching thumbnail were verified. The user manually published the [DEV article](https://dev.to/ali_hamza_4bd92ee9f67e78702/i-built-an-ai-gardener-for-the-boring-work-every-open-source-maintainer-avoids-4doc), including the working video iframe and four screenshots; publication verification is recorded in `docs/dev-publication-verification.json`.
