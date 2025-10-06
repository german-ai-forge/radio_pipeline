import os, json, glob
from pathlib import Path
from .config import load_config
from .paths import bronze_dir

def write_manifest(cfg: dict = None):
    cfg = cfg or load_config()
    bdir = bronze_dir(cfg)
    files = sorted(glob.glob(str(bdir / "raw_segment_*.ts")))
    man = bdir / "manifest.jsonl"
    with open(man, "w", encoding="utf-8") as f:
        for fp in files:
            st = os.stat(fp)
            item = {
                "file": os.path.basename(fp),
                "path": fp,
                "bytes": st.st_size,
                "duration_hint_sec": cfg["segment_time_sec"]
            }
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print("Manifest written:", man)
