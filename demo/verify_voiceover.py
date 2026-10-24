"""Verify the actual final audio/video/caption artifacts without touching services."""
from array import array
import hashlib
import json
from pathlib import Path
import re
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT/'demo/assets/audio'
VIDEO = ROOT/'demo/assets/video/final_demo.mp4'


def time_value(text):
    h,m,s = text.replace(',','.').split(':')
    return int(h)*3600+int(m)*60+float(s)


def words(text):
    return re.findall(r'[a-z]+',text.lower())


def main():
    timeline=json.loads((AUDIO/'narration_timeline.json').read_text(encoding='utf-8'))
    manifest=json.loads((AUDIO/'voiceover-evidence.json').read_text(encoding='utf-8'))
    assert manifest['voice']==timeline['voice'] and manifest['voice_selected_by']=='user'
    script=' '.join(s['text'] for s in timeline['scenes'])
    assert 'kokoro' not in script.lower()
    subtitle_text=(AUDIO/'subtitles.srt').read_text(encoding='utf-8')
    assert 'kokoro' not in subtitle_text.lower()
    captions=[]
    for block in re.split(r'\n\s*\n',subtitle_text.strip()):
        lines=block.splitlines()
        start,end=lines[1].split(' --> ')
        caption={'start':time_value(start),'end':time_value(end),'text':' '.join(lines[2:])}
        assert caption['start']<caption['end']<=timeline['video_duration']
        assert re.search(r'[A-Za-z0-9]',caption['text']), 'Punctuation-only caption'
        assert len(lines[2:])<=2
        if captions:assert captions[-1]['end']<=caption['start']
        captions.append(caption)
    assert words(' '.join(c['text'] for c in captions))==words(script), 'Captions must cover the spoken script exactly'
    with wave.open(str(AUDIO/'kokoro_voiceover.wav'),'rb') as wav:
        assert wav.getnchannels()==1 and wav.getsampwidth()==2 and wav.getframerate()==48000
        audio_seconds=wav.getnframes()/wav.getframerate()
        assert abs(audio_seconds-timeline['video_duration'])<.01
        samples=array('h',wav.readframes(wav.getnframes()))
    peak=max(abs(s) for s in samples)
    assert peak<32767 and peak>1000
    for scene in manifest['scenes']:
        assert scene['start']<scene['audio_end']<=scene['end']
    probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,size',
                          '-show_entries','stream=codec_name,codec_type,width,height,sample_rate,channels,duration',
                          '-of','json',str(VIDEO)],check=True,capture_output=True,text=True)
    meta=json.loads(probe.stdout)
    v=next(s for s in meta['streams'] if s['codec_type']=='video')
    a=next(s for s in meta['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['codec_name'])==(1920,1080,'h264')
    assert a['codec_name']=='aac' and a['sample_rate']=='48000'
    assert abs(float(v['duration'])-float(a['duration']))<.05
    subprocess.run(['ffmpeg','-v','error','-i',str(VIDEO),'-f','null','-'],check=True,capture_output=True)
    measurement=subprocess.run(['ffmpeg','-v','info','-i',str(VIDEO),'-af',
                                 'loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json','-f','null','-'],
                                check=True,capture_output=True,text=True)
    loudness,_=json.JSONDecoder().raw_decode(measurement.stderr[measurement.stderr.rfind('{'):])
    assert float(loudness['input_tp'])<0
    result={'video':str(VIDEO),'voice':manifest['voice_display_name'],'audio_seconds':audio_seconds,
            'captions':len(captions),'caption_words_match_script':True,
            'caption_overlap':False,'punctuation_only_captions':False,
            'voice_tool_named_in_spoken_script_or_captions':False,
            'pcm_clipped_samples':sum(abs(s)>=32767 for s in samples),
            'integrated_lufs':float(loudness['input_i']),'true_peak_dbtp':float(loudness['input_tp']),
            'full_decode_passed':True,'streams':meta['streams'],'file_bytes':int(meta['format']['size']),
            'video_sha256':hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
            'audio_sha256':hashlib.sha256((AUDIO/'kokoro_voiceover.wav').read_bytes()).hexdigest()}
    (AUDIO/'final-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
