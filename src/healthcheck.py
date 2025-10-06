import glob, os, sys
from .config import load_config
from .paths import bronze_dir

def main():
    cfg = load_config()
    bdir = bronze_dir(cfg)
    segs = sorted(glob.glob(str(bdir / "raw_segment_*.ts")))
    expected = max(1, cfg["program_duration_sec"] // cfg["segment_time_sec"])
    kept = 0
    for s in segs:
        if os.path.getsize(s) < 32_000:  # <32KB probable segmento vacío
            print("Removing tiny segment:", s)
            os.remove(s)
        else:
            kept += 1
    ok = kept >= expected - 1  # tolerancia
    print(f"Segments kept={kept}, expected~={expected}, OK={ok}")
    return 0 if ok else 2

if __name__ == "__main__":
    sys.exit(main())
