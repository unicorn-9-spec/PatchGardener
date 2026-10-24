"""Generate the user-selected local voice, timed captions, and final demonstration.

Run with a Kokoro-enabled Python environment and the explicitly selected --voice.
The explicit voice must match the recorded user choice in narration_timeline.json.
All model inference is CPU-only with a small thread limit, to leave other sessions alone.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import textwrap
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ['HF_HOME'] = str(ROOT / '.tools' / 'hf-cache')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OMP_NUM_THREADS'] = '2'
os.environ['MKL_NUM_THREADS'] = '2'
TEMP_ROOT = ROOT / '.tools/tmp'
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ['TEMP'] = str(TEMP_ROOT)
os.environ['TMP'] = str(TEMP_ROOT)


def command(args: list[str]):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    seconds, millis = divmod(millis, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'


def hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def ass_timestamp(seconds: float) -> str:
    centis = round(seconds * 100)
    hours, centis = divmod(centis, 360000)
    minutes, centis = divmod(centis, 6000)
    seconds, centis = divmod(centis, 100)
    return f'{hours}:{minutes:02}:{seconds:02}.{centis:02}'


def make_captions(spans, offset, factor, clip_end):
    # The tokenizer returns punctuation separately. Attach it before choosing
    # cue boundaries so a trailing period never becomes a flashing caption.
    joined = []
    for span in spans:
        if not re.search(r'\w', span['text']):
            if joined:
                joined[-1]['text'] = joined[-1]['text'].rstrip() + span['text']
                joined[-1]['end'] = max(joined[-1]['end'],span['end'])
        else:
            joined.append(dict(span))
    captions, words, start, end = [], [], None, None
    for span in joined:
        token = span['text']
        if not token.strip():
            continue
        a = offset + span['start'] / factor
        b = min(clip_end, offset + span['end'] / factor)
        if start is None:
            start = a
        words.append(token)
        end = max(b, a + 0.05)
        phrase = ''.join(words).strip()
        if len(phrase) >= 75 or (re.search(r'[.!?]["\u201d]?$', token.strip()) and end - start >= 1.4):
            captions.append({'start':start, 'end':min(clip_end,end + 0.16), 'text':phrase})
            words, start, end = [], None, None
    if words and start is not None:
        captions.append({'start':start, 'end':min(clip_end,end + 0.18), 'text':''.join(words).strip()})
    return captions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--voice', required=True)
    parser.add_argument('--audio-only', action='store_true')
    args = parser.parse_args()
    timeline_path = ROOT / 'demo/assets/audio/narration_timeline.json'
    timeline = json.loads(timeline_path.read_text(encoding='utf-8'))
    if args.voice != timeline['voice'] or timeline['voice_selected_by'] != 'user':
        raise SystemExit('The voice must match the explicit user selection saved in the timeline.')
    catalog = json.loads((ROOT / 'demo/assets/audio/voice_catalog.json').read_text(encoding='utf-8-sig'))
    if args.voice not in catalog['english_voices']:
        raise SystemExit('The selected voice is absent from the verified model inventory.')
    model_root = ROOT / '.tools/kokoro-model'
    model_root.mkdir(parents=True, exist_ok=True)
    for name in ('config.json', 'kokoro-v1_0.pth', f'{args.voice}.pt'):
        local = model_root / name
        if not local.exists():
            remote = f'voices/{name}' if name.endswith('.pt') else name
            url = f'https://huggingface.co/{catalog["repo"]}/resolve/{catalog["revision"]}/{remote}'
            urllib.request.urlretrieve(url, local)

    import numpy as np
    import soundfile as sf
    import torch
    from kokoro import KModel, KPipeline
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    started = time.perf_counter()
    model = KModel(repo_id=catalog['repo'], config=str(model_root/'config.json'),
                   model=str(model_root/'kokoro-v1_0.pth')).to('cpu').eval()
    pipeline = KPipeline(lang_code=args.voice[0], repo_id=catalog['repo'], model=model, device='cpu')
    sample_rate = int(timeline['sample_rate'])
    duration = float(timeline['video_duration'])
    combined = np.zeros(round(duration * sample_rate), dtype=np.float32)
    work = ROOT / '.tools/narration' / args.voice
    work.mkdir(parents=True, exist_ok=True)
    audio_root = ROOT / 'demo/assets/audio'
    scenes, captions = [], []
    for scene in timeline['scenes']:
        synthesis_text = scene.get('tts_text',scene['text'])
        digest = hashlib.sha256(f'{catalog["revision"]}:{args.voice}:{synthesis_text}'.encode()).hexdigest()[:16]
        raw = work / f'{scene["id"]}-{digest}.wav'
        tokens_path = raw.with_suffix('.tokens.json')
        if raw.exists() and tokens_path.exists():
            waveform, rate = sf.read(raw, dtype='float32')
            assert rate == sample_rate
            spans = json.loads(tokens_path.read_text(encoding='utf-8'))
        else:
            chunks, spans, elapsed = [], [], 0.0
            with torch.inference_mode():
                for result in pipeline(synthesis_text, voice=str(model_root/f'{args.voice}.pt'), speed=1.0):
                    if result.audio is None:
                        raise RuntimeError('The selected local model returned no audio.')
                    chunk = result.audio.cpu().numpy().astype(np.float32)
                    for token in result.tokens or []:
                        a, b = getattr(token,'start_ts',None), getattr(token,'end_ts',None)
                        text = token.text + (getattr(token,'whitespace','') or '')
                        if a is None or b is None:
                            if spans:
                                spans[-1]['text'] += text
                            continue
                        spans.append({'text':text,'start':elapsed+float(a),'end':elapsed+float(b)})
                    chunks.append(chunk)
                    elapsed += len(chunk)/sample_rate
            if not chunks or not spans:
                raise RuntimeError('Audio or model-derived word timing was missing.')
            waveform = np.concatenate(chunks)
            sf.write(raw, waveform, sample_rate, subtype='PCM_16')
            tokens_path.write_text(json.dumps(spans,indent=2),encoding='utf-8')
        natural = len(waveform)/sample_rate
        available = float(scene['end']) - float(scene['start']) - 0.12
        factor = max(1.0,natural/available)
        if factor > 1.22:
            raise RuntimeError(f'{scene["id"]} needs a shorter script: {natural:.2f}s for {available:.2f}s, factor={factor:.3f}.')
        if factor > 1.005:
            paced = work / f'{scene["id"]}-paced.wav'
            command(['ffmpeg','-v','error','-y','-i',str(raw),'-af',f'atempo={factor:.8f}',
                     '-ar',str(sample_rate),'-ac','1',str(paced)])
            waveform, rate = sf.read(paced, dtype='float32')
        placement = round(float(scene['start']) * sample_rate)
        if placement + len(waveform) > round(float(scene['end'])*sample_rate):
            raise RuntimeError(f'{scene["id"]} exceeded its scene window after pacing.')
        fade = min(240, len(waveform)//2)
        waveform[:fade] *= np.linspace(0,1,fade,dtype=np.float32)
        waveform[-fade:] *= np.linspace(1,0,fade,dtype=np.float32)
        combined[placement:placement+len(waveform)] += waveform
        captions.extend(make_captions(spans,float(scene['start']),factor,float(scene['start'])+len(waveform)/sample_rate))
        scenes.append({**scene,'natural_seconds':round(natural,3),'tempo_factor':round(factor,6),
                       'audio_end':round(float(scene['start'])+len(waveform)/sample_rate,3)})
        print(f'{scene["id"]}: {natural:.2f}s -> scene {scene["start"]:.2f}-{scene["end"]:.2f}, tempo {factor:.3f}',flush=True)

    raw_mix = work / 'aligned-raw.wav'
    sf.write(raw_mix,combined,sample_rate,subtype='PCM_24')
    final_audio = audio_root / 'kokoro_voiceover.wav'
    # Measure, then apply a two-pass normalization to avoid loudness changes between scenes.
    measured = subprocess.run(['ffmpeg','-v','info','-i',str(raw_mix),'-af',
                              'loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    loudness, _ = json.JSONDecoder().raw_decode(measured.stderr[measured.stderr.rfind('{'):])
    filt = ('loudnorm=I=-16:TP=-1.5:LRA=7:linear=true:'
            f'measured_I={loudness["input_i"]}:measured_TP={loudness["input_tp"]}:'
            f'measured_LRA={loudness["input_lra"]}:measured_thresh={loudness["input_thresh"]}:'
            f'offset={loudness["target_offset"]}')
    command(['ffmpeg','-v','error','-y','-i',str(raw_mix),'-af',filt,'-ar','48000','-ac','1','-c:a','pcm_s16le',str(final_audio)])
    captions.sort(key=lambda c:c['start'])
    for i, caption in enumerate(captions):
        if i+1<len(captions):
            caption['end'] = min(caption['end'],captions[i+1]['start']-.03)
        if caption['end'] <= caption['start']:
            raise RuntimeError('Invalid subtitle timing.')
    srt = []
    for i, caption in enumerate(captions,1):
        lines = textwrap.wrap(caption['text'],width=44,break_long_words=False,break_on_hyphens=False)
        if len(lines)>2:
            raise RuntimeError(f'A caption needs more than two lines: {caption["text"]}')
        srt.append(f'{i}\n{timestamp(caption["start"])} --> {timestamp(caption["end"])}\n'+ '\n'.join(lines)+'\n')
    subtitles = audio_root / 'subtitles.srt'
    subtitles.write_text('\n'.join(srt),encoding='utf-8')
    ass = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1920', 'PlayResY: 1080',
           'WrapStyle: 2', '', '[V4+ Styles]',
           'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
           'Style: Default,Arial,34,&H00FFFFFF,&H00FFFFFF,&H002D3B21,&H002D3B21,0,0,0,0,100,100,0,0,1,1,0,2,60,60,18,1',
           '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    for caption in captions:
        wrapped = r'\N'.join(textwrap.wrap(caption['text'],width=44,break_long_words=False,break_on_hyphens=False))
        ass.append(f'Dialogue: 0,{ass_timestamp(caption["start"])},{ass_timestamp(caption["end"])},Default,,0,0,0,,{wrapped}')
    (audio_root/'subtitles.ass').write_text('\n'.join(ass)+'\n',encoding='utf-8')
    # Burn subtitles into a dedicated bottom band; scale the original up to its boundary
    # so captions never obscure controls in the actual recorded application.
    if not args.audio_only:
        vf = ("scale=1920:976:force_original_aspect_ratio=decrease,"
              "pad=1920:1080:(ow-iw)/2:0:color=0x213b2d,"
              "subtitles=demo/assets/audio/subtitles.ass")
        final_video = ROOT / 'demo/assets/video/final_demo.mp4'
        command(['ffmpeg','-v','error','-y','-i','demo/assets/video/demo_silent.mp4',
                 '-i',str(final_audio),'-i',str(subtitles),'-map','0:v:0','-map','1:a:0','-map','2:s:0',
                 '-vf',vf,'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',
                 '-threads','2','-c:a','aac','-b:a','192k','-c:s','mov_text',
                 '-metadata:s:a:0','language=eng','-metadata:s:s:0','language=eng',
                 '-disposition:s:0','0','-t',str(duration),'-movflags','+faststart',str(final_video)])
        command(['ffmpeg','-v','error','-i',str(final_video),'-f','null','-'])
    manifest = {'voice':args.voice,'voice_display_name':args.voice.split('_',1)[1].title(),'voice_selected_by':'user',
                'repo':catalog['repo'],'revision':catalog['revision'],'engine':'kokoro',
                'engine_version':importlib.metadata.version('kokoro'),'torch':torch.__version__,
                'device':'cpu','threads':2,'model_sha256':hash_file(model_root/'kokoro-v1_0.pth'),
                'voice_sha256':hash_file(model_root/f'{args.voice}.pt'),
                'timeline_sha256':hash_file(timeline_path),'video_seconds':duration,
                'assembly_wall_seconds':round(time.perf_counter()-started,2),'scenes':scenes,
                'caption_count':len(captions),'subtitle_source':'Kokoro model-derived token durations, adjusted for scene pacing',
                'voice_engine_mentioned_in_narration':False,'final_video_decode_verified':not args.audio_only}
    (audio_root/'voiceover-evidence.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Generated narration, {len(captions)} timed captions, and final video: demo/assets/video/final_demo.mp4',flush=True)


if __name__=='__main__':
    main()
