import re, glob
from pathlib import Path
from .config import load_config
from .paths import bronze_dir, silver_dir, gold_dir

URL_RE   = re.compile(r'https?://\S+', re.IGNORECASE)
PHONE_RE = re.compile(r'(?<!\d)(\+?\d[\d\s\-\(\)]{7,})(?!\d)')

def vtt_blocks(vtt_path: Path):
    # Yields (start, end, text)
    start = end = None
    buf = []
    with open(vtt_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "-->" in line:
                if buf and start and end:
                    yield (start, end, " ".join(buf).strip())
                    buf = []
                times = line.split("-->")
                start = times[0].strip()
                end = times[1].strip().split(" ")[0]
            elif line and not line.startswith("WEBVTT"):
                buf.append(line)
        if buf and start and end:
            yield (start, end, " ".join(buf).strip())

def is_ad_text(text: str, cfg: dict) -> bool:
    text_l = text.lower()
    score = 0
    if cfg["ad_heuristics"]["patterns"].get("url"):
        score += 2 * len(URL_RE.findall(text_l))
    if cfg["ad_heuristics"]["patterns"].get("phone"):
        score += 2 * len(PHONE_RE.findall(text_l))
    for kw in cfg["ad_heuristics"]["keywords"]:
        if kw in text_l:
            score += 1
    return score >= 2

def segment_is_ad(vtt_path: Path, cfg: dict) -> bool:
    hits = 0; total = 0
    for _, _, txt in vtt_blocks(vtt_path):
        total += 1
        if is_ad_text(txt, cfg):
            hits += 1
    if total == 0:
        return False
    return hits >= cfg["ad_heuristics"]["min_hits_per_segment"] or (hits/total) >= cfg["ad_heuristics"]["ratio_threshold"]

def write_keep_list(cfg: dict = None):
    cfg = cfg or load_config()
    bdir = bronze_dir(cfg)
    sdir = silver_dir(cfg)
    gdir = gold_dir(cfg)
    gdir.mkdir(parents=True, exist_ok=True)

    segments = sorted(glob.glob(str(bdir / "raw_segment_*.ts")))
    keep = []
    for seg in segments:
        vtt = sdir / (Path(seg).stem + ".vtt")
        if not vtt.exists():
            keep.append(seg)
            continue
        if not segment_is_ad(vtt, cfg):
            keep.append(seg)

    keepfile = gdir / "keeplist.txt"
    with open(keepfile, "w", encoding="utf-8") as f:
        for k in keep:
            f.write(f"file '{k}'\n")
    print(f"Keep list: {keepfile} (kept={len(keep)} of {len(segments)})")
    return 0
