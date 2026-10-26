Title: PatchGardener: Small Repository Fixes, Real Evidence, Human Approval

Tags: devchallenge, hf26challenge, opensource, ai

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19).*

## What I Built

An unused import is easy to remove. A broken README link is easy to repair. A stale example command is easy to overlook until someone tries it.

The effort comes from repeating the whole maintenance loop: find the problem, check the evidence, decide on the edit, review the change, run checks, and make sure nothing else moved.

I built **PatchGardener** to turn those small chores into concrete review decisions. It scans a repository, shows an exact finding from a deterministic tool, asks Qwen for a minimal patch, and waits for a human to approve it. Validation runs against separate baseline and patched copies. The original repository stays unchanged, and the result is an ordinary `.patch` file.

The interface follows that sequence: a maintenance queue, file-and-line evidence, a side-by-side diff, an approval checkbox, and before/after checks. It handles unused Python imports, broken relative Markdown links, and references to missing Python examples. Sensitive paths are withheld from proposals.

PatchGardener has a personal local workspace and a synthetic demo mode. The demo accepts only **Meadow Notes**, a fictional note-tagging repository included with the project. Visitors receive separate expiring workspaces for source copies, proposals, diffs and audit records. There is no server-path field or executable-command input.

It also has an optional **Backboard review notebook**. After a fix passes validation, the maintainer can save a small record of the decision and recall it in a fresh conversation. The notebook remembers the maintenance outcome while source files and diffs stay in the application.

![The actual maintenance queue, with scanner evidence and a withheld protected-path finding](https://raw.githubusercontent.com/unicorn-9-spec/PatchGardener/3ee6cb43710b9397b2da1b69750afb32d78cbd45/demo/assets/backboard/screenshots/02-scanner-findings.png)

## Demo

{% youtube X4P1CGkZocI %}

The narrated walkthrough runs for 3 minutes and 7.8 seconds at 1920×1080. It shows the real application, fresh Qwen inference, explicit approval and validation, patch export, protected-path rejection, and genuine Backboard memory save and recall. It includes spoken narration and 43 synchronized English caption cues. The local MP4 passed full decoding and audio/video synchronization checks, and the YouTube upload is playable and permits embedding.

The demo starts with a real Ruff finding at `meadow.py:1`:

```python
import os
import json
```

Selecting the unused `os` import shows its scanner evidence. Qwen reads the selected file and returns a structured edit. PatchGardener checks that edit against its deterministic rules before presenting it for review.

![A genuine local Qwen proposal, showing the original, proposed change and approval controls](https://raw.githubusercontent.com/unicorn-9-spec/PatchGardener/3ee6cb43710b9397b2da1b69750afb32d78cbd45/demo/assets/backboard/screenshots/04-real-qwen-diff.png)

Approval is an explicit decision. After I check the box and approve, the application creates baseline and patched copies, checks the exported diff for applicability, reruns the scanners, runs the permitted fixture tests, and checks the original fingerprint again.

The outcome is deliberately specific: **one finding resolved, zero regressions, original unchanged**. The fixture starts with five findings, so this fix leaves four. A passing change does not turn the whole repository green.

![Validation against the baseline, with actual fixture test output expanded](https://raw.githubusercontent.com/unicorn-9-spec/PatchGardener/3ee6cb43710b9397b2da1b69750afb32d78cbd45/demo/assets/backboard/screenshots/06-fixture-tests.png)

The video includes exporting the actual diff and selecting the planted finding under `auth/`, whose proposal is rejected. Separate browser acceptance checks also attempt to read a proposal and export from another visitor session; those requests are blocked.

The complete demo-mode browser journey has been verified over local HTTPS with real Qwen inference. It captures the scanner queue, proposed diff, validation result, protected-path rejection and live health dashboard. These are local application checks. A DigitalOcean-hosted URL and hosted screenshots are pending approved provisioning and successful deployment checks.

For Backboard, I verified an additional live sequence: save the approved review with automatic memory enabled, wait for indexing, then recall it in a different thread under the same private assistant. Backboard retrieved one memory and returned the correct review ID, file, F401 finding and successful validation outcome. This check used actual API calls and the local Qwen patch workflow.

![Actual Backboard review recall, including retrieved-memory count and conversation evidence](https://raw.githubusercontent.com/unicorn-9-spec/PatchGardener/3ee6cb43710b9397b2da1b69750afb32d78cbd45/demo/assets/backboard/screenshots/08-backboard-recalled.png)

## Code

Source repository: [PatchGardener on GitHub](https://github.com/unicorn-9-spec/PatchGardener).

The project includes the synthetic fixture and its known findings, strict patch gates, backend security tests, a real-inference browser acceptance journey, Dockerfiles, a Linux Compose configuration, and a DigitalOcean Terraform definition. The code is MIT licensed.

For a local workspace, install the Python and Node dependencies, pull `qwen3:8b` in Ollama, start FastAPI on loopback port 8105, and start the Next.js interface on loopback port 3105. The README contains the commands and execution boundaries.

## How I Built It

The frontend uses Next.js, React and TypeScript. FastAPI coordinates the workflow, Pydantic validates structured inputs and model replies, and SQLite stores scan, proposal, approval and validation records.

Ruff finds Python issues. A small relative-path scanner finds broken documentation links and missing example references without fetching external URLs. The model receives the selected file, its evidence and a bounded path inventory. It has no shell tools and cannot choose commands to execute.

**Qwen proposes. Application code decides what is admissible.**

An edit must target the selected evidence file, match existing text exactly, avoid protected paths, and stay within the diff budget. Python changes must be the exact removal of the reported unused import and pass an AST restriction. Approval rechecks the stored proposal and original-source fingerprint before creating any patched copy.

Arbitrary repository code never runs. The built-in fixture can run its fixed tests only when the original bytes match the trusted fixture. Local repositories supplied by the operator receive static checks. A missing model or malformed reply stops the flow; PatchGardener does not substitute a prerecorded response.

For the public demo design, the backend rejects local repository roots at startup. An HTTPS-only signed session cookie selects a private workspace with its own SQLite database. Session expiry, request limits, work quotas and resource bounds keep the demonstration small. The source, diffs and audit routes all use that same session boundary.

### Backboard memory across reviews

The notebook uses the official Backboard Python SDK. A save passes `memory="Auto"`; recall passes `memory="Readonly"` and starts a new thread with the same assistant. Each workspace owns its assistant mapping, so visitors do not share a notebook. Notebook replies use Qwen3-30B-A3B-Instruct through Backboard's OpenRouter integration.

The application sends a fixed record of the synthetic finding and approved validation outcome. It rejects private repositories, unapproved changes and failed validation runs. It sends no source files, generated diffs, arbitrary prompts or model tools. Remembering a review is an explicit action after validation; the notebook cannot approve or apply a patch.

The measured write and recall responses reported generation costs of $0.0000306 and $0.0000495. Their $0.0000801 sum describes those two reported calls, not a complete invoice or a promise about future usage. Backboard retains saved facts separately from local session expiry, which the interface explains before transfer.

The **Deployment health** page reports the running API, SQLite connectivity, installed model availability, digest, Ollama version and active limits. Model presence is a readiness check; the proposal journey proves actual inference.

## Why Does Open Innovation Matter?

An open-weight model lets this workflow run on the maintainer's machine or on a server they control. The model artifact can be identified by digest, and the prompt, reply schema and acceptance rules are inspectable code.

Open-source tools supply the checks around inference. Ruff provides reproducible evidence, Git checks the portable diff, and Python's AST helps constrain the permitted transformation. A fluent explanation alone cannot approve a patch.

This also keeps the model replaceable. Changing the inference engine should preserve the meaning of protected paths, human approval, baseline comparison and source immutability.

## The Lazy Payoff

PatchGardener packages a repetitive maintenance loop into something a developer can inspect and finish: evidence, proposed edit, approval, isolated validation and export.

The synthetic fixture makes the behavior easy to examine, including the boundaries. A protected finding remains withheld. Other existing issues remain visible after a successful fix. Another visitor cannot retrieve the generated diff. The original source remains the reference point throughout.

There is no measured claim of hours saved or accuracy on unseen repositories. The useful result is a complete, reviewable workflow for small maintenance tasks, with the final shipping decision left to the maintainer.

## Prize Categories

**Best Use of Backboard:** PatchGardener uses Backboard's real memory API to save approved synthetic review outcomes and retrieve them across fresh conversations, with a private assistant per workspace. The live check confirmed indexing, retrieval and correct recall while the open-weight Qwen proposal workflow remained central.
