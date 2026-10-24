# PatchGardener implementation plan

1. Validate local runtime and model: Python 3.12.7, Node 22.14.0, Ollama 0.40.8, installed Qwen3 8B Q4_K_M (8.2B parameters, 40,960 native context). Restrict application context to 8,192 tokens. Qwen3-8B is Apache-2.0: https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE. No Gemma use. GPU: RTX 4090, 24 GB, approximately 17 GB initially free.
2. P0: immutable bounded repository snapshots, real Ruff + relative Markdown checks, exact evidence, SQLite audit, structured local Ollama proposals, deterministic patch gates, approval, isolated copies, baseline and post-change checks, export.
3. Test P0 with a real local model before completing the UI. Cover traversal, symlink escape, protected paths, oversized edits, stale approval and source immutability.
4. Build responsive Next.js/TypeScript/Tailwind interface with shadcn-style accessible primitives and side-by-side diff. Include honest model availability and actionable errors.
5. Verify production build, browser journey and seeded evaluation; record actual screenshots and a 90–150 second silent video. Document actual measured results and limitations.
6. Prepare publishing materials. GitHub destination, Kokoro voice, YouTube upload and external publication require the explicit checkpoints in BUILD_PROMPT.md. Continue independent local work while awaiting required choices.

Execution policy: only the built-in, hash-verified synthetic fixture may run its fixed unit tests. User-configured repositories receive static validation only. Copy isolation is not an OS sandbox; never execute arbitrary repository code. Docker engine is unavailable on this machine. Network access is unavailable for package downloads; reuse already installed dependency artifacts where possible and document any unavailable optional tooling.
