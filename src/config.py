import yaml
from pathlib import Path

DEFAULTS = {
    "timezone": "UTC",
    "program_duration_sec": 7200,
    "segment_time_sec": 900,
    "copy_mode": True,
    "aac_bitrate": "128k",
    "mp3_bitrate": "160k",
    "final_format": "mp3",
    "whisper": {
        "enabled": True,
        "backend": "cli",
        "model": "small",
        "language": "es",
        "output_format": "vtt"
    },
    "paths": {
        "data_root": "data",
        "bronze": "data/bronze",
        "silver": "data/silver",
        "gold":   "data/gold",
        "logs":   "logs"
    },
    "ad_heuristics": {
        "min_hits_per_segment": 3,
        "ratio_threshold": 0.35,
        "patterns": {"url": True, "phone": True},
        "keywords": [
            "auspicia","patrocina","presenta","oferta","promoción","descuento",
            "llamá al","llamen al","ingresá a","visitanos en","en nuestra web",
            "envío gratis","válido hasta","términos y condiciones"
        ]
    }
}

def load_config(cfg_path: str = None) -> dict:
    cfg_file = Path(cfg_path) if cfg_path else Path(__file__).resolve().parents[1] / "config.yaml"
    user = {}
    print("Cargando config desde:", cfg_file)
    if cfg_file.exists():
        with open(cfg_file, "r", encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
    cfg = DEFAULTS.copy()
    for k, v in user.items():
        cfg[k] = v
    return cfg
