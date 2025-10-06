import os, glob, shlex, subprocess
from pathlib import Path
from .config import load_config
from .paths import bronze_dir, silver_dir
from faster_whisper import WhisperModel

def _call(cmd):
    print("Running:", cmd if isinstance(cmd,str) else " ".join(shlex.quote(c) for c in cmd))
    return subprocess.call(cmd, shell=isinstance(cmd, str))

def transcribe_segments(cfg: dict = None):
    cfg = cfg or load_config()
    bdir = bronze_dir(cfg)
    sdir = silver_dir(cfg)
    sdir.mkdir(parents=True, exist_ok=True)

    backend = cfg["whisper"].get("backend","cli")
    model = cfg["whisper"].get("model","small")
    lang = cfg["whisper"].get("language","es")
    outfmt = cfg["whisper"].get("output_format","vtt")

    segments = sorted(glob.glob(str(bdir / "raw_segment_*.ts")))
    if not segments:
        print("No segments found in", bdir)
        return 1

    if backend == "cli":
        for seg in segments:
            cmd = [
                "whisper", seg,
                "--model", model,
                "--language", lang,
                "--task", "transcribe",
                "--output_format", outfmt,
                "--output_dir", str(sdir)
            ]
            rc = _call(cmd)
            if rc != 0: return rc
        return 0
    elif backend == "python":
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print("Install openai-whisper or switch to 'cli' backend in config.yaml")
            return 2
        m = WhisperModel(model, device="cpu", compute_type="float16")
        for seg in segments:
            result = m.transcribe(seg, language=lang, task="transcribe")
            vtt_path = sdir / (Path(seg).stem + ".vtt")
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n\n")
                for chunk in result["segments"]:
                    def fmt(t):
                        h = int(t//3600); m=int((t%3600)//60); s=(t%60)
                        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".",",")
                    f.write(f"{fmt(chunk['start'])} --> {fmt(chunk['end'])}\n{chunk['text'].strip()}\n\n")
        return 0
    elif backend == "faster":
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print("Install faster-whisper or switch backend in config.yaml")
            return 2
        model_size = model
        model = WhisperModel(model_size, device="cpu")
        for seg in segments:
            segs, info = model.transcribe(seg, language=lang)
            vtt_path = sdir / (Path(seg).stem + ".vtt")
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n\n")
                for segm in segs:
                    def fmt(t):
                        h = int(t//3600); m=int((t%3600)//60); s=(t%60)
                        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".",",")
                    f.write(f"{fmt(segm.start)} --> {fmt(segm.end)}\n{segm.text.strip()}\n\n")
        return 0
    else:
        print("Unknown whisper backend:", backend)
        return 3
