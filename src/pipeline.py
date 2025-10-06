import argparse
from .config import load_config
from .record import record_and_segment
from .manifest import write_manifest
from .transcribe import transcribe_segments
from .detect_ads import write_keep_list
from .assemble import assemble_clean
from .healthcheck import main as healthcheck_main

def main():
    ap = argparse.ArgumentParser(description="Radio Data Lake Pipeline")
    ap.add_argument("command", choices=[
        "record", "manifest", "transcribe", "detect-ads", "assemble", "run-post"
    ], help="Pipeline stage")
    ap.add_argument("--config", default=None, help="Path to config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)

    if args.command == "record":
        return record_and_segment(cfg)
    elif args.command == "manifest":
        return write_manifest(cfg)
    elif args.command == "transcribe":
        return transcribe_segments(cfg)
    elif args.command == "detect-ads":
        return write_keep_list(cfg)
    elif args.command == "assemble":
        return assemble_clean(cfg)
    elif args.command == "run-post":
        rc = write_manifest(cfg)
        if rc: return rc
        # validar segmentos antes de seguir
        rc = healthcheck_main()
        if rc: return rc
        rc = transcribe_segments(cfg)
        if rc: return rc
        rc = write_keep_list(cfg)
        if rc: return rc
        rc = assemble_clean(cfg)
        return rc

if __name__ == "__main__":
    raise SystemExit(main())
