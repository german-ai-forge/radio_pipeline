import subprocess
import shlex
from dateutil import tz
from datetime import datetime
import os

def run(cmd, shell=False):
    """Run a subprocess command and stream output. Returns returncode."""
    if isinstance(cmd, str) and not shell:
        cmd = shlex.split(cmd)
    proc = subprocess.Popen(cmd, shell=shell)
    return proc.wait()

def now_local(tz_name: str = "UTC"):
    tzinfo = tz.gettz(tz_name)
    return datetime.now(tzinfo)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
    return path
