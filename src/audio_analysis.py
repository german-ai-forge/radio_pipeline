import os, glob, json
from pathlib import Path
from pydub import AudioSegment, silence
import webrtcvad
import numpy as np
import wave

from .config import load_config
from .paths import bronze_dir, silver_dir

def analyze_segments(cfg: dict = None):
    """
    Analiza segmentos de audio en Bronze para detectar silencios y actividad de voz.
    Guarda metadatos en JSON por cada segmento.
    """
    cfg = cfg or load_config()
    bdir = bronze_dir(cfg)
    sdir = silver_dir(cfg)
    sdir.mkdir(parents=True, exist_ok=True)

    segments = sorted(glob.glob(str(bdir / "raw_segment_*.ts")))
    if not segments:
        print("No hay segmentos en Bronze:", bdir)
        return 1

    for seg in segments:
        # Convertimos con pydub
        audio = AudioSegment.from_file(seg, format="ts")
        
        # Detectar silencios largos
        silences = silence.detect_silence(audio, min_silence_len=1000, silence_thresh=-35)
        silences = [(start/1000, stop/1000) for start, stop in silences]  # segs

        # Exportar a WAV mono 16k para VAD
        wav_path = str(Path(seg).with_suffix(".wav"))
        audio.set_channels(1).set_frame_rate(16000).export(wav_path, format="wav")

        vad = webrtcvad.Vad(2)  # 0=agresivo bajo, 3=alto
        frames = read_frames(wav_path, frame_duration_ms=30)
        speech_flags = [vad.is_speech(f.bytes, 16000) for f in frames]

        voice_ratio = sum(speech_flags) / len(speech_flags) if speech_flags else 0.0

        meta = {
            "segment": os.path.basename(seg),
            "duration_sec": audio.duration_seconds,
            "silences": silences,
            "voice_activity_ratio": voice_ratio,
            "notes": f"Voz en {voice_ratio*100:.1f}% del segmento"
        }

        # Guardar en Silver
        out_json = sdir / (Path(seg).stem + "_audio_meta.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print("Guardado:", out_json)

    return 0

# Helpers para VAD
class Frame(object):
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration

def read_frames(wav_path, frame_duration_ms=30):
    with wave.open(wav_path, "rb") as wf:
        sample_rate = wf.getframerate()
        bytes_per_frame = int(sample_rate * 2 * frame_duration_ms / 1000)
        timestamp = 0.0
        duration = (float(bytes_per_frame) / (2 * sample_rate))
        frames = []
        while True:
            data = wf.readframes(int(bytes_per_frame / 2))
            if len(data) < bytes_per_frame:
                break
            frames.append(Frame(data, timestamp, duration))
            timestamp += duration
        return frames
