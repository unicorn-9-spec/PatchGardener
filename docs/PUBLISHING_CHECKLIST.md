# Publishing checklist — completed

Source of approval checkpoints: [BUILD_PROMPT.md](../BUILD_PROMPT.md). No account, organization, voice or remote destination has been selected on the user's behalf.

## Local implementation and verification

- [x] Runnable local FastAPI and Next.js application.
- [x] Real local non-Gemma Qwen inference with verified Apache-2.0 model license.
- [x] Actual scanner evidence, patch gates, approval, isolated copy, baseline, regression comparison and patch export.
- [x] 26 backend tests, real model evaluation, TypeScript, production build and live HTTP smoke checks.
- [x] README, MIT LICENSE, environment example, architecture/evaluation/demo documentation.
- [x] All 3 end-to-end Playwright tests, mobile overflow/sidebar assertions, 5 clean axe scans and rendered visual review. Dedicated keyboard usability checks remain outside the current tests.
- [x] Seven actual screenshots and verified 118.04-second 1920×1080 silent video.

## GitHub destination and push

- [x] Asked exactly: **“Which GitHub username or organization should I publish this project under, and should the repository be public?”** User confirmed public `unicorn-9-spec/PatchGardener`.
- [x] Explicit user destination/visibility and publication approval received; not inferred from authentication.
- [x] Source package reviewed: credentials, `.env`, model weights, local data, generated audio/video, dependencies and caches excluded; no high-confidence token/private-key patterns found.
- [x] Concrete source package prepared and destination confirmed. GitHub API reported no existing repository at the approved destination before creation.
- [x] Approved source pushed to public [unicorn-9-spec/PatchGardener](https://github.com/unicorn-9-spec/PatchGardener), branch `main`. All seven screenshot URLs at commit `ff8c76781bdaf9e96bab5371aa84c0fa939531dd` returned PNG bytes matching their local SHA-256 hashes. See [publication verification](publication-results.json).

## Kokoro narration

- [x] Successful silent video exists and has been decoded/inspected.
- [x] Draft narration script prepared with approximate scene windows; precise audio alignment follows synthesis.
- [x] Inspected actual installed Kokoro-82M configuration (Kokoro 0.9.4, CPU Torch 2.8.0) and verified the publisher's 28 English voices. See [voice options](VOICE_OPTIONS.md).
- [x] User explicitly selected Heart (`af_heart`).
- [x] Genuine Kokoro audio synthesized and aligned; 34 caption cues and `demo/assets/video/final_demo.mp4` exported.
- [x] Audio/video durations, subtitle word coverage/order, scene alignment, loudness, clipping, full-file decoding and representative captioned frames checked. Exact final path: `G:\Hacktoberfest-2026-Week3\05-PatchGardener\demo\assets\video\final_demo.mp4`.

## YouTube and DEV

- [x] User uploaded the verified final MP4 and supplied https://youtu.be/cR2HYNkqO_0. The agent did not upload it or choose a YouTube account.
- [x] Verified ID `cR2HYNkqO_0`, official oEmbed, playability OK, embedding permitted, 118-second duration, and thumbnail matching the actual captioned application. Added `{% youtube cR2HYNkqO_0 %}`. See [YouTube verification](youtube-verification.json).
- [x] Completed the exact-template article with real GitHub link, actual YouTube embed and four verified commit-pinned screenshots.
- [x] Preserved measured claims and limitations; no invented time savings, session embeds, prize integrations or links.
- [x] Final article supplied as a Markdown file at the user's requested path for review.
- [x] User reviewed and manually published the article. The agent did not publish or modify it on DEV.
- [x] Verified the [published post](https://dev.to/ali_hamza_4bd92ee9f67e78702/i-built-an-ai-gardener-for-the-boring-work-every-open-source-maintainer-avoids-4doc): HTTP 200, required challenge tags and headings, correct YouTube iframe, repository link and all four rendered screenshot responses. Published body matches the local submission. See [DEV verification](dev-publication-verification.json).

The user published the completed article on 24 October 2026. Challenge page verified on 24 October 2026: https://dev.to/challenges/hacktoberfest-week3-2026-10-19. Its required tags `devchallenge` and `hf26challenge` are present. The application implements no partner-category integration; no partner prize category is claimed, including Gemma.
