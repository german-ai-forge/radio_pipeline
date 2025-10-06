from pathlib import Path
from datetime import datetime
from dateutil import tz

def date_parts(tz_name: str):
    now = datetime.now(tz.gettz(tz_name))
    return now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"), now

def bronze_dir(cfg: dict):
    y,m,d,_ = date_parts(cfg["timezone"])
    return Path(cfg["paths"]["bronze"]) / y / m / d

def silver_dir(cfg: dict):
    y,m,d,_ = date_parts(cfg["timezone"])
    return Path(cfg["paths"]["silver"]) / y / m / d

def gold_dir(cfg: dict):
    y,m,d,_ = date_parts(cfg["timezone"])
    return Path(cfg["paths"]["gold"]) / y / m / d

def logs_dir(cfg: dict):
    return Path(cfg["paths"]["logs"])

def strftime_for_file(dt: datetime):
    return dt.strftime("%Y%m%d-%H%M%S")
