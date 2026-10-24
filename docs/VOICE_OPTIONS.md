# Verified Kokoro-82M English voices

Verified 24 October 2026 against the publisher's [voice inventory](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md).

Installed runtime: Kokoro 0.9.4, CPU PyTorch 2.8.0. Existing local model configuration and weights were inspected at `../03-AccessPath/.tools/kokoro-model/`. The PatchGardener cache now contains Heart, Liam and Emma after comparison previews were generated. **The user explicitly selected Heart (`af_heart`) for the completed narration.** Other listed voices are supported by the model and require their official voice tensor download. Another project's voice selection was not reused as authorization.

| Accent | Voices |
|---|---|
| American English, female | Heart (`af_heart`), Alloy (`af_alloy`), Aoede (`af_aoede`), Bella (`af_bella`), Jessica (`af_jessica`), Kore (`af_kore`), Nicole (`af_nicole`), Nova (`af_nova`), River (`af_river`), Sarah (`af_sarah`), Sky (`af_sky`) |
| American English, male | Adam (`am_adam`), Echo (`am_echo`), Eric (`am_eric`), Fenrir (`am_fenrir`), Liam (`am_liam`), Michael (`am_michael`), Onyx (`am_onyx`), Puck (`am_puck`), Santa (`am_santa`) |
| British English, female | Alice (`bf_alice`), Emma (`bf_emma`), Isabella (`bf_isabella`), Lily (`bf_lily`) |
| British English, male | Daniel (`bm_daniel`), Fable (`bm_fable`), George (`bm_george`), Lewis (`bm_lewis`) |

The installed model artifact is the genuine hexgrad/Kokoro-82M v1 model, approximately 327 MB of weights. The model and dependencies are separate from the application and are not bundled in publication files.
