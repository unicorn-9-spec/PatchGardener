# Narrated demonstration

The user explicitly selected **Heart (`af_heart`)**. The completed final video is `demo/assets/video/final_demo.mp4`: 118.04 seconds, 1920×1080, H.264 video, 48 kHz AAC speech, burned English captions in a dedicated bottom band and a selectable subtitle track.

Exact path: `G:\Hacktoberfest-2026-Week3\05-PatchGardener\demo\assets\video\final_demo.mp4`.

Narration uses nine scene windows, 219 spoken words and 34 model-timed caption cues. Audio/video durations match exactly. All caption words match the script, cues are ordered and nonoverlapping, and the PCM narration has zero clipped samples. Final loudness measured −16.10 LUFS and −1.45 dBTP true peak. Full MP4 decoding passed. Representative captioned diff and real-test-output frames were visually inspected; captions do not obscure application controls. Actual metadata and hashes are in `demo/assets/audio/final-verification.json` and model/voice provenance is in `voiceover-evidence.json`.

Three genuine Kokoro-82M comparison previews are available locally:

- [Liam, American English male](../demo/assets/audio/previews/am_liam.wav), 8.47 seconds.
- [Heart, American English female](../demo/assets/audio/previews/af_heart.wav), 9.70 seconds.
- [Emma, British English female](../demo/assets/audio/previews/bf_emma.wav), 8.53 seconds.

The comparison samples preceded the user's explicit Heart choice. Both the previews and final narration use genuine Kokoro 0.9.4 and hexgrad/Kokoro-82M v1 weights, with CPU-only Torch 2.8.0 and two threads. The official voice tensors were read locally or downloaded from model revision `f3ff3571791e39611d31c381e3a41a3af07b4987`. No shared Ollama service or other project was reconfigured.

To reproduce, use a Kokoro-enabled Python environment and run `demo/narrate_demo.py --voice af_heart`, then `demo/verify_voiceover.py`. The renderer requires the explicitly selected voice to match the timeline; it uses actual model-derived word durations, writes SRT/ASS, normalizes audio, and puts captions in a dedicated green bottom band. Two clips needed pacing adjustments of less than 7%; all others use natural speed. No background music or third-party video was added.

For an independent environment, create `.tools/kokoro`, install CPU Torch 2.8.0 from `https://download.pytorch.org/whl/cpu`, then install `demo/requirements-voice.lock.txt`. The script downloads the pinned official model and chosen voice when missing. Model files are approximately 327 MB plus the voice tensor.

The current machine's existing Kokoro interpreter is at `../03-AccessPath/.tools/kokoro/Scripts/python.exe`; model/config/voice files for this project are cached under `.tools/kokoro-model/`. `demo/requirements-voice.lock.txt` preserves the compatible voice environment. Runtime/model files and generated WAV/MP4/WebM files are excluded from version control.

Narration is complete. The user explicitly approved public [unicorn-9-spec/PatchGardener](https://github.com/unicorn-9-spec/PatchGardener), and source/screenshots have been published and verified. Credentials remain in ignored local configuration. The user uploads the final MP4 to their chosen YouTube account and supplies the actual URL; the agent does not select an account or upload automatically.
