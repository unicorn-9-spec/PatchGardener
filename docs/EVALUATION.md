# Measured evaluation and limitations

Measurements were collected locally on **24 October 2026**, using the explicitly synthetic Meadow Notes fixture. The source fixture and ground truth are in `backend/seed.py`. These are reproducible developer checks, not a user study or a benchmark on unseen repositories.

## Model and environment

- Qwen3-8B via Ollama, `qwen3:8b`, Q4_K_M, approximately 5.2 GB downloaded weights; model metadata reports 8.2B parameters and native 40,960 context. The application bounds context to 8,192 tokens and output to 1,200 tokens.
- Apache-2.0 model license verified at https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE. Model digest: `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
- Ollama 0.40.8; Python 3.12.7; Node 22.14.0; Next.js 16.4.3; Ruff 0.16.5 in the final evaluation. An initial PATH-selected Ruff was 0.15.20; the app now resolves Ruff from its active Python installation for reproducibility.
- NVIDIA RTX 4090, 24 GB VRAM, approximately 17 GB initially free. The GPU is shared; no dedicated performance claim is made. Docker CLI is installed, but its engine was unavailable.

## Detection and real proposals

The 9-file fixture contains five deliberately planted **P0 in-scope** findings:

| File and line | Ground truth | Detected | Proposal/validation |
|---|---|---|---|
| `meadow.py:1` | F401 unused `os` | Yes | Real Qwen; passed; 781 ms inference |
| `meadow.py:2` | F401 unused `json` | Yes | Real Qwen; passed; 875 ms inference |
| `README.md:5` | Broken relative guide link | Yes | Real Qwen; passed; 1,030 ms inference |
| `README.md:10` | Missing Python example path | Yes | Real Qwen; passed; 1,233 ms inference |
| `auth/session.py:1` | F401 unused `hashlib` | Yes | Withheld by protected-path gate; no inference |

Measured on this fixed fixture: **5 true positives, 0 false positives, 0 false negatives; precision 1.0, in-scope recall 1.0; 4/4 eligible proposals applied and validated; 1/1 protected issue withheld.** These fractions describe five known cases, not general safety or accuracy probabilities.

Each eligible issue was evaluated independently from the same original snapshot. Every approved copy resolved its selected issue, introduced zero new issue signatures, passed `git apply --check`, passed all three fixture unit tests, and left the original fingerprint unchanged. Remaining unrelated lint/docs findings were retained. There is no cumulative claim that all five findings were cleared. A short clean three-test suite is not proof of behavioral equivalence for arbitrary projects.

The fixture also contains TypeScript formatting and a minimal configuration, and lacks more extensive edge-case coverage. These are **not** counted as detected or fixed. ESLint/Prettier, configuration analysis and test-gap detection are outside P0. Recall uses the declared five-case P0 ground truth only.

The quoted inference times include the local HTTP request and structured response validation; the model was already available and this is not a cold-start benchmark. An earlier first request took 3,796 ms. No retries, canned patches, or mock model responses were used in the real evaluation. All exact diffs, timings, statuses and test output are preserved in [evaluation-results.json](evaluation-results.json). Reproduce with `python scripts/evaluate.py`.

## Application and security checks

**26 backend tests passed.** Tests cover exact scanner ground truth, path traversal/absolute/drive/backslash/hidden paths, symlink exclusion, secret-bearing Python and JSON, secret directories, file-size limits, protected scope, AST logic-change rejection, encoding-comment injection, unrelated import removal, invalid old text, executable allowlist, fixture trust invalidation, nonexecution of external tests, required approval, stale source, approval replay, cross-origin and Host rejection, exact export and original immutability. Unit-test-only model stubs exercise validation mechanics; they are not counted as real inference.

**TypeScript checking and optimized production build passed.** The default TypeScript CLI build worker hit `spawn EPERM` in this restricted host; using Next's supported worker API and one worker completed type validation and the production build without skipping errors.

**Eight live HTTP smoke checks passed through the actual Next.js production server**: server-rendered HTML, live model status, actual scans, fresh Qwen proposal, rejected missing approval, isolated validation and fixture tests, exact downloadable diff, and rejected cross-origin mutation. The final report is [http-results.json](http-results.json). Reproduce against running services with `python scripts/http_smoke.py`.

## Browser, accessibility and demo evidence

After the execution restrictions were lifted, **all three Playwright tests passed** on the actual production application in 7.5 seconds. The main journey uses fresh real Qwen inference, scanner evidence, disabled-until-approved application, isolated-copy validation, original immutability, export and the actual approval audit. Other checks cover protected paths, 390×844 mobile overflow/sidebar behavior, local setup and same-origin/cross-origin request validation. The raw report is [browser-results.json](browser-results.json).

Five default-rule axe scans—desktop queue, patch review, validation result, mobile protected-path view and mobile settings—reported **zero violations**. Their raw JSON reports are retained in `test-results/`, and the reproducible checks are in `tests/browser/journey.spec.ts`. Automated scans do not establish WCAG conformance; no dedicated keyboard usability study was conducted. Desktop and mobile screenshots and representative decoded video frames were visually inspected.

The first unrestricted browser run exposed a real proxy bug: Next's internal origin could be `localhost` while the browser loaded `127.0.0.1`. Comparing Origin against that canonical URL rejected legitimate mutations. The guard now compares against the validated incoming loopback Host; browser and API tests cover both the legitimate origin and rejected cross-origin requests. Subsequent runs found five low-contrast labels and a mobile sidebar note that overflowed its compact column; both were corrected and retested.

The genuine silent Playwright recording is **118.04 seconds**, **1920×1080**, H.264/yuv420p, **2,680,327 bytes**. FFmpeg decoded the entire MP4 without errors. Seven actual screenshots show the garden, queue, exact evidence, AI diff, completed validation, passing unit tests and audit. [Video evidence](video-evidence.json) preserves metadata and hashes. Files are local; no fabricated UI or public video link is substituted.

The user selected **Heart (`af_heart`)**. Genuine Kokoro-82M narration is complete with **34 synchronized caption cues**, both burned into a dedicated bottom band and included as a selectable subtitle track. Final audio/video tracks both last **118.04 seconds**; the final MP4 is **4,375,821 bytes**. Full decoding passed, caption words match the spoken script, cues do not overlap, and PCM audio has zero clipped samples. Measured loudness is **−16.10 LUFS**, true peak **−1.45 dBTP**. Representative captioned diff and test-output frames were visually inspected. [Voiceover verification](../demo/assets/audio/final-verification.json) records actual checks and hashes; [voiceover notes](VOICEOVER.md) explain reproduction. A user-uploaded YouTube URL remains pending.

## What payoff is evidenced

The real system turns a detected finding into a bounded model edit, explicit approval, an independently checked copy and an exportable patch. In the measured fixture, four such proposals worked and one sensitive finding was withheld. It reduces steps the maintainer must carry out manually, but **minutes saved, adoption, human review time, real-world false-positive rates and productivity gains have not been measured**.

The user-approved [public source repository](https://github.com/unicorn-9-spec/PatchGardener) is published on `main`. All seven commit-pinned screenshot URLs returned PNG bytes with SHA-256 hashes matching the actual local captures; [publication-results.json](publication-results.json) preserves this verification. The user-uploaded YouTube URL and final DEV article review remain pending under the explicit checkpoints in `BUILD_PROMPT.md`.
