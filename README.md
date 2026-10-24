# PatchGardener

**Small repository fixes, grounded in evidence and reviewed by you.**

PatchGardener scans an allowlisted local repository with Ruff and relative Markdown checks, asks a real local Qwen model for a minimal edit, explains its risk, and waits for approval. It applies that edit to a separate copy, compares it with a baseline, and exports an ordinary unified patch. It never edits the original repository or pushes to a remote.

Built for [Hacktoberfest Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19). No Gemma models or Gemma category. The included Meadow Notes repository is **fictional, explicitly synthetic test data**; its findings and validation results are real.

Public source: [unicorn-9-spec/PatchGardener](https://github.com/unicorn-9-spec/PatchGardener). The seven screenshots in this repository are captures of the actual running application.

![Actual PatchGardener application](demo/assets/screenshots/01-garden.png)

## Current verification

- 26 backend tests passed, including traversal, symlinks, secret filtering, protected paths, executable allowlist, encoding-comment injection, AST scope, stale approval, replay, source immutability, and diff export.
- Real Qwen evaluation: 5/5 planted in-scope findings detected, zero false positives; 4/4 eligible proposals validated independently; 1 protected-path issue withheld. Each approved copy passed its three fixture unit tests. These small fixed-fixture results do not estimate performance on unseen repositories.
- TypeScript check and optimized Next.js build passed. Eight live HTTP checks through the production frontend proxy passed.
- All 3 Playwright browser tests passed, including the real local AI journey, mobile protected-path layout and API guards. Five axe scans reported zero violations. Desktop/mobile screenshots and representative video frames were visually inspected.
- Seven actual screenshots and a verified **118.04-second, 1920×1080 narrated demo** were produced. [Watch the narrated demo on YouTube](https://youtu.be/cR2HYNkqO_0). The local file `demo/assets/video/final_demo.mp4` uses the user's chosen Heart voice and 34 synchronized caption cues.

See [evaluation](docs/EVALUATION.md), [raw model measurements](docs/evaluation-results.json), and [browser results](docs/browser-results.json).

## Run locally

Requirements: Python 3.12+, Node 22+, Git, Ollama, and approximately 6 GB free RAM/VRAM for the default quantized model plus application overhead. GPU recommended; CPU inference is possible but was not benchmarked. Dependencies and model weights must be installed first; normal inference and scans then use local resources.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
ollama pull qwen3:8b
```

On Linux/macOS activate with `source .venv/bin/activate`. Run Ollama with `ollama serve` if it is not already running. Start two terminals from this directory:

```powershell
# Terminal 1 (activate the Python environment first)
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8105
```

```powershell
# Terminal 2
npm run dev
```

Open **http://127.0.0.1:3105**. For a production frontend, use `npm run build` then `npm run start`. Both services bind to loopback. Do not expose this personal local application to other machines; it has no multi-user authentication.

The app reads process environment variables. `.env.example` documents defaults; copying it to `.env` alone does not configure FastAPI. For example, set `$env:PG_MODEL='qwen3:8b'` in PowerShell or `export PG_MODEL=qwen3:8b` on Linux/macOS **before** starting the backend.

## Try the actual flow

1. Select the synthetic `meadow-notes` repository and click **Scan repository**.
2. Select the unused `os` import in `meadow.py`. Review its exact scanner evidence.
3. Click **Propose a local AI patch**. The model status must show the local model is available. There is no canned-response fallback.
4. Inspect both versions and risk reasons. Unused-import removal is rated medium because an import can have side effects.
5. Check the approval box and click **Approve & validate copy**.
6. Compare the before and after findings and expand the real unit-test output. A passing patch resolves its selected issue without introducing findings; other baseline issues can remain.
7. Export `.patch` and inspect the local activity log. Applying the patch to your original repository is your separate decision.

Selecting the issue under `auth/` demonstrates the protected-path gate: no model proposal or application is permitted.

## Add a known-safe local repository

Configure explicit roots before starting FastAPI. The browser cannot submit arbitrary paths.

```powershell
$env:PG_REPO_ROOTS='C:\Projects\my-trusted-repo;C:\Projects\another-repo'
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8105
```

On Linux/macOS use the OS path separator `:`. Roots must not overlap application data. Scans accept `.py`, `.md`, `.ts`, `.tsx`, `.json`, `.toml`, and `.txt`, bounded to 200 files, 64 KB per file, 1 MB total, and 1,000 visited directories. Hidden files, generated/dependency directories, symlinks, junctions, secret filenames/directories and detected secret-bearing text are excluded. The model receives only the selected file (maximum 12,000 characters), its scanner evidence, and the allowlisted path inventory.

**External repository code is never executed.** Only static checks run there. Only the exact built-in fixture may run its fixed unit-test command, after the AST gate proves the Python edit removes only the selected unused import. A copy or worktree is not an OS sandbox. Proxy environment values are defense in depth, not a network security boundary. There is no arbitrary test runner or model-supplied shell command.

## Check and evaluate

```powershell
python -m pytest tests/test_engine.py -q -p no:cacheprovider
python scripts/evaluate.py
npm run typecheck
npm run build
# Start production frontend and backend before the following:
python scripts/http_smoke.py
npx playwright install chromium
npm run test:e2e
npm run demo:record
ffmpeg -y -i demo/assets/video/demo_silent.webm -c:v libx264 -pix_fmt yuv420p -an demo/assets/video/demo_silent.mp4
```

The evaluation makes fresh real model calls and records outcomes in `docs/evaluation-results.json`. Each issue uses an independent copy of the original scan; this is not a cumulative all-issues repair benchmark. Unit tests stub the model only where testing validation behavior; they are separate from the real inference evaluation. The recording script uses the actual application, no intercepted requests, and writes screenshots and a roughly two-minute silent WebM on successful completion.

## Stack and layout

Next.js 16, React 19, TypeScript, Tailwind 4, shadcn-style Radix/CVA button primitive, Lucide icons; FastAPI, Pydantic, SQLite; Ollama/Qwen3-8B; Ruff and Git CLI. Source-code side-by-side review is implemented with accessible HTML; Monaco is not bundled in this P0. Model weights use [Apache-2.0](https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE); application code uses MIT. Dependencies retain their own licenses. No model weights are redistributed.

```text
app/                 UI and allowlisted same-origin API proxy
backend/             Schemas, scanners, patch gates, model client, SQLite audit
tests/               Backend and full browser journey tests
scripts/             Real inference evaluation and live HTTP smoke test
demo/record_demo.mjs  Actual application recording script
docs/                Architecture, evidence, demo and publication preparation
data/                Ignored local snapshots, fixture, isolated copies, SQLite
```

Docker Compose is not included: the local Docker engine was unavailable and container execution was not verified. Manual setup is the tested route.

## Privacy and limits

Source snapshots, patches and audit records stay in `data/`, unencrypted at rest. Use only repositories whose source you are authorized to inspect locally. Secret filters are heuristic and cannot guarantee detection of every secret. Backup or remove local data yourself when appropriate; no retention automation is implemented. No secrets, `.env`, local source snapshots, dependencies or model weights belong in a public repository.

P0 only checks F401/F841, inline relative Markdown links, and `python path.py` example commands. Anchors, external URLs, reference-style links, ESLint, formatting/config cleanup and missing-test detection are outside scope. Python proposals support only single-name top-level F401 import removal; F841 findings may be reported but cannot be patched. Small patches can still be semantically wrong. Review every change.

The user-approved public GitHub repository, screenshot hosting and user-uploaded YouTube video are verified. The complete article is in [docs/DEV_SUBMISSION.md](docs/DEV_SUBMISSION.md), ready for the user's review before manual DEV publication. The agent does not publish to DEV automatically.
