"""Generate comparison samples only; this never selects the final narrator."""
import json
import os
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
os.environ["HF_HOME"] = str(ROOT / ".tools/hf-cache")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def main():
    import numpy as np
    import soundfile as sf
    import torch
    from kokoro import KModel, KPipeline

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    catalog = json.loads((ROOT / "demo/assets/audio/voice_catalog.json").read_text(encoding="utf-8-sig"))
    model_root = ROOT / ".tools/kokoro-model"
    output = ROOT / "demo/assets/audio/previews"
    output.mkdir(parents=True, exist_ok=True)
    model = KModel(repo_id=catalog["repo"], config=str(model_root / "config.json"), model=str(model_root / "kokoro-v1_0.pth")).to("cpu").eval()
    # Avoid inherited proxy configuration from the former restricted session.
    # Only official, pinned, public voice tensors are fetched.
    downloader = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    sample = "An unused import. A guide that moved. PatchGardener turns small maintenance chores into a reviewable patch. Your approval. Your repository."
    for voice in ("am_liam", "af_heart", "bf_emma"):
        voice_file = model_root / f"{voice}.pt"
        if not voice_file.exists():
            cached = ROOT.parent / "03-AccessPath/.tools/kokoro-model" / voice_file.name
            if cached.exists():
                shutil.copyfile(cached, voice_file)
            else:
                url = f'https://huggingface.co/{catalog["repo"]}/resolve/{catalog["revision"]}/voices/{voice}.pt'
                with downloader.open(url, timeout=60) as response:
                    voice_file.write_bytes(response.read())
        pipeline = KPipeline(lang_code=voice[0], repo_id=catalog["repo"], model=model, device="cpu")
        with torch.inference_mode():
            chunks = [result.audio.cpu().numpy() for result in pipeline(sample, voice=str(voice_file), speed=1.0) if result.audio is not None]
        waveform = np.concatenate(chunks)
        destination = output / f"{voice}.wav"
        sf.write(destination, waveform, 24000, subtype="PCM_16")
        print(f"Preview only: {destination} ({len(waveform)/24000:.2f}s)", flush=True)


if __name__ == "__main__":
    main()
