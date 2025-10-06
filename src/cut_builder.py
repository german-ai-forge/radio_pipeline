# src/cut_builder.py
import json, glob
from pathlib import Path
from typing import List, Tuple

from .config import load_config
from .paths  import bronze_dir, silver_dir, gold_dir
from .detect_ads import vtt_blocks, is_ad_text  # usamos lector VTT y heurística ya existente

# --- Utilidades de tiempo ---
def merge_intervals(intervals: List[Tuple[float, float]], join_gap: float = 8.0) -> List[Tuple[float, float]]:
    """Une intervalos [s,e] que estén muy cerca (gap < join_gap)."""
    if not intervals: return []
    ints = sorted(intervals)
    out = [ints[0]]
    for s,e in ints[1:]:
        ps,pe = out[-1]
        if s - pe <= join_gap:
            out[-1] = (ps, max(pe, e))
        else:
            out.append((s,e))
    return out

def subtract_intervals(full: Tuple[float,float], cuts: List[Tuple[float,float]]) -> List[Tuple[float,float]]:
    """Resta cuts del rango full y devuelve tramos válidos (keep)."""
    s0, e0 = full
    keeps = []
    cursor = s0
    for s,e in sorted(cuts):
        if e <= cursor:  # totalmente antes
            continue
        if s > e0:       # totalmente después
            break
        if s > cursor:
            keeps.append((cursor, min(s, e0)))
        cursor = max(cursor, e)
        if cursor >= e0:
            break
    if cursor < e0:
        keeps.append((cursor, e0))
    return [(max(s0, s), min(e0, e)) for s,e in keeps if e - s > 0]

# --- Candidatos por texto ---
def text_ad_windows(vtt_path: Path, min_block: float = 4.0) -> List[Tuple[float,float]]:
    """
    Devuelve ventanas [s,e] del VTT con bloques que caen como 'anuncio' por reglas simples.
    Agrupa bloques consecutivos sospechosos en intervalos.
    """
    def parse_ts(ts: str) -> float:
        # "HH:MM:SS.mmm" o "HH:MM:SS,mmm"
        ts = ts.replace(",", ".")
        h,m,s = ts.split(":")
        return int(h)*3600 + int(m)*60 + float(s)
    cand = []
    for s,e,txt in vtt_blocks(vtt_path):
        if is_ad_text(txt, load_config()):
            cand.append((parse_ts(s), parse_ts(e)))
    # Une bloques cercanos
    return merge_intervals(cand, join_gap=5.0)

# --- Candidatos por audio ---
def audio_music_windows(meta: dict, min_music: float = 25.0) -> List[Tuple[float,float]]:
    """
    A partir de metadatos de audio (silencios, first_speech_start, last_speech_end, voice_ratio),
    infiere ventanas típicas de música/jingle prolongada (sin voz) que merecen ser consideradas.
    """
    windows = []
    dur = float(meta.get("duration_sec", 600))
    silences = meta.get("silences", [])
    # normaliza a tuplas float
    silences = [(float(s), float(e)) for s,e in silences]
    # música/silencio largos
    for s,e in silences:
        if (e - s) >= min_music:
            windows.append((s,e))
    # si el inicio tiene música/voz muy tarde
    fs = float(meta.get("first_speech_start_sec", 0.0))
    if fs >= min_music:
        windows.append((0.0, fs))
    # si el final pierde voz mucho antes
    le = float(meta.get("last_speech_end_sec", dur))
    if dur - le >= min_music:
        windows.append((le, dur))
    return merge_intervals(windows, join_gap=5.0)

# --- Híbrido simple: intersección o expansión contextual ---
def decide_invalid_intervals(vtt_path: Path, audio_meta: dict, llm_cls: str = None,
                             min_cut_sec: float = 20.0) -> List[Tuple[float,float]]:
    """
    Construye intervalos NO VÁLIDOS combinando:
      - ventanas por texto (anuncio),
      - ventanas por audio (música/silencio prolongados),
      - etiqueta LLM (si está disponible) para reforzar decisión ambigua.

    Política:
      - Si hay texto de anuncio → marcar esa ventana.
      - Si hay música sin voz prolongada y LLM=anuncio → marcar ventana de audio.
      - Si hay música prolongada al borde de texto de anuncio → expandir al borde musical.
      - Ignorar todo corte < min_cut_sec (tu regla).
    """
    txt = text_ad_windows(vtt_path)
    mus = audio_music_windows(audio_meta) if audio_meta else []

    # Si el LLM dijo anuncio para el SEGMENTO completo, podemos expandir: pero
    # como queremos precisión, solo reforzamos donde haya música prolongada o texto cercano.
    invalid = []

    # 1) texto directo
    invalid.extend(txt)

    # 2) música prolongada + apoyo
    if mus:
        if txt:
            # expande: si están cerca (<= 10s), unir
            expanded = []
            for ms in mus:
                for tx in txt:
                    # si se tocan o están muy cerca, unir
                    gap = max(0.0, max(min(tx[1], ms[1]) - max(tx[0], ms[0]),  # overlap positivo
                                       min(abs(ms[0]-tx[1]), abs(tx[0]-ms[1]))))  # proximidad
                    if gap <= 10.0:
                        expanded.append((min(ms[0], tx[0]), max(ms[1], tx[1])))
            invalid.extend(expanded)
        # si LLM dijo anuncio y hay música larga → considerá la música como inválida
        if (llm_cls == "anuncio"):
            invalid.extend(mus)

    # Unifica y aplica umbral de 20s
    merged = merge_intervals(invalid, join_gap=5.0)
    return [(s,e) for s,e in merged if (e - s) >= min_cut_sec]

def build_keep_trims_for_segment(seg_path: Path, invalid: List[Tuple[float,float]], full_duration: float) -> List[Tuple[float,float]]:
    """Devuelve lista de (inpoint,outpoint) válidos a mantener, restando 'invalid' del [0, full_duration]."""
    full = (0.0, float(full_duration))
    keeps = subtract_intervals(full, merge_intervals(invalid, join_gap=5.0))
    # fusiona keeps muy cercanos para evitar chiqui-cortes
    nice = merge_intervals(keeps, join_gap=4.0)
    return nice

def write_keeplist_per_trims(keeps_by_file: dict, keeplist_path: Path):
    """
    Escribe keelist con múltiples inpoint/outpoint por archivo:
      file 'X'
      inpoint a
      outpoint b
      file 'X'
      inpoint c
      outpoint d
    """
    with open(keeplist_path, "w", encoding="utf-8") as f:
        for file_path, trims in keeps_by_file.items():
            for (a,b) in trims:
                f.write(f"file '{file_path}'\n")
                f.write(f"inpoint {a:.3f}\n")
                f.write(f"outpoint {b:.3f}\n")

def run_cut_builder():
    """
    Lee por fecha actual:
      - segmentos Bronze,
      - VTT en Silver,
      - metadatos de audio en Silver (si existen),
      - (opcional) decisiones del LLM por segmento (si existen) -> 'decisions_llm.json' o similar.
    Genera gold/.../keeplist.txt con recortes finos (respetando corte mínimo de 20s).
    """
    cfg = load_config()
    bdir = bronze_dir(cfg)
    sdir = silver_dir(cfg)
    gdir = gold_dir(cfg)
    gdir.mkdir(parents=True, exist_ok=True)

    min_cut_sec = 20.0  # tu regla
    segments = sorted(glob.glob(str(bdir / "raw_segment_*.ts")))
    keeps_by_file = {}

    # opcional: mapa rápido LLM por segmento
    llm_decisions = {}
    llm_json = gdir / "decisions_llm.json"
    if llm_json.exists():
        try:
            for row in json.loads(llm_json.read_text(encoding="utf-8")):
                seg = row.get("segment"); dec = row.get("decision","")
                # decision puede ser "drop:llm" o "keep:llm" -> nos interesa etiqueta
                if "drop:llm" in dec:
                    llm_decisions[seg] = "anuncio"
                elif "keep:llm" in dec:
                    llm_decisions[seg] = "programa"
        except Exception:
            pass

    for seg in segments:
        segp = Path(seg)
        vtt = sdir / (segp.stem + ".vtt")
        meta_path = sdir / (segp.stem + "_audio_meta.json")
        audio_meta = {}
        if meta_path.exists():
            try:
                audio_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                audio_meta = {}
        if not vtt.exists() and not audio_meta:
            # sin info -> conservar todo el segmento
            keeps_by_file[seg] = [(0.0, 600.0)]
            continue

        llm_label = llm_decisions.get(segp.name)  # 'anuncio'/'programa'/None
        invalid = decide_invalid_intervals(vtt, audio_meta, llm_cls=llm_label, min_cut_sec=min_cut_sec)
        dur = float(audio_meta.get("duration_sec", 600.0))
        keeps = build_keep_trims_for_segment(segp, invalid, dur)
        # si por alguna razón quedamos sin keeps (todo anúncio), puedes optar por dejar 1 bloque grande mínimo
        keeps_by_file[seg] = keeps if keeps else []

    keeplist = gdir / "keeplist.txt"
    write_keeplist_per_trims(keeps_by_file, keeplist)
    print(f"[CUT] keeplist con recortes finos: {keeplist}")
    return 0
