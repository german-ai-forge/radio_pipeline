import shlex, subprocess
from pathlib import Path
from .config import load_config
from .paths import gold_dir

def assemble_clean(cfg: dict = None):
    cfg = cfg or load_config()
    gdir = gold_dir(cfg)
    keepfile = gdir / "keeplist.txt"
    if not keepfile.exists():
        raise SystemExit(f"Not found: {keepfile}")

    clean_ts = gdir / "program_clean.ts"
    cmd1 = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
        "-f", "concat", "-safe", "0", "-i", str(keepfile),
        "-c", "copy", str(clean_ts)
    ]
    print("Running:", " ".join(shlex.quote(c) for c in cmd1))
    rc = subprocess.call(cmd1)
    if rc != 0: return rc

    final_format = cfg.get("final_format","mp3").lower()
    if final_format == "mp3":
        final_path = gdir / "program_clean.mp3"
        cmd2 = [
            "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
            "-i", str(clean_ts),
            "-vn", "-acodec", "libmp3lame", "-b:a", cfg.get("mp3_bitrate","160k"),
            str(final_path)
        ]
    else:
        final_path = gdir / "program_clean.aac"
        cmd2 = [
            "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
            "-i", str(clean_ts),
            "-vn", "-c:a", "aac", "-b:a", cfg.get("aac_bitrate","128k"),
            str(final_path)
        ]
    print("Running:", " ".join(shlex.quote(c) for c in cmd2))
    return subprocess.call(cmd2)
