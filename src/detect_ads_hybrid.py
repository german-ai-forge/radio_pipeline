import os, glob, json
from pathlib import Path
from .config import load_config
from .paths import bronze_dir, silver_dir, gold_dir
from .detect_ads import vtt_blocks, is_ad_text   # reglas existentes
from .detect_ads_llm import _read_vtt_text, _load_audio_meta, _mistral_classify

def _heuristics_score(vtt_path: Path, cfg: dict):
    hits = total = 0
    for _, _, txt in vtt_blocks(vtt_path):
        total += 1
        if is_ad_text(txt, cfg):
            hits += 1
    ratio = (hits/total) if total else 0.0
    strong = (hits >= cfg["ad_heuristics"]["min_hits_per_segment"]) or (ratio >= cfg["ad_heuristics"]["ratio_threshold"])
    bl = cfg.get("llm", {}).get("heuristics_borderline", {})
    borderline = (not strong) and (hits >= bl.get("min_hits_per_segment", 2) or ratio >= bl.get("ratio_threshold_low", 0.20))
    return hits, total, ratio, strong, borderline

def write_keep_list_hybrid(cfg: dict = None):
    """Primero reglas. Si queda borderline → consulta al LLM."""
    cfg = cfg or load_config()
    bdir = bronze_dir(cfg); sdir = silver_dir(cfg); gdir = gold_dir(cfg)
    gdir.mkdir(parents=True, exist_ok=True)

    segments = sorted(glob.glob(str(bdir / "raw_segment_*.ts")))
    max_chars = cfg.get("llm", {}).get("max_chars_per_segment", 9000)

    keep, decisions = [], []
    for seg in segments:
        vtt = sdir / (Path(seg).stem + ".vtt")
        if not vtt.exists():
            keep.append(seg)
            decisions.append({"segment": Path(seg).name, "decision": "keep:no_vtt"})
            continue

        hits, total, ratio, strong, borderline = _heuristics_score(vtt, cfg)
        if strong:
            decisions.append({"segment": Path(seg).name, "decision": "drop:heuristics", "hits": hits, "ratio": ratio})
            continue
        if not borderline:
            keep.append(seg)
            decisions.append({"segment": Path(seg).name, "decision": "keep:heuristics", "hits": hits, "ratio": ratio})
            continue

        # borderline → LLM
        text = _read_vtt_text(vtt, max_chars)
        meta = _load_audio_meta(sdir, seg)
        try:
            cls = _mistral_classify(text, meta, cfg)
        except Exception as e:
            cls = "programa"  # fail-open ante error API
            decisions.append({"segment": Path(seg).name, "decision": f"keep:llm_error:{e}", "hits": hits, "ratio": ratio})

        if cls == "anuncio":
            decisions.append({"segment": Path(seg).name, "decision": "drop:llm", "hits": hits, "ratio": ratio})
        else:
            keep.append(seg)
            decisions.append({"segment": Path(seg).name, "decision": "keep:llm", "hits": hits, "ratio": ratio})

    keepfile = gdir / "keeplist.txt"
    with open(keepfile, "w", encoding="utf-8") as f:
        for k in keep: f.write(f"file '{k}'\n")

    (gdir / "decisions_hybrid.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[HYBRID] Keep list: {keepfile} (kept={len(keep)} of {len(segments)})")
    return 0
