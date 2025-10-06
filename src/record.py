import shlex, subprocess
from pathlib import Path
from .config import load_config
from .paths import bronze_dir, strftime_for_file
from .utils import ensure_dir
from dateutil import tz
from datetime import datetime

def record_and_segment(cfg: dict = None):
    import shutil  # <-- añade esto arriba si no está importado
    cfg = cfg or load_config()
    outdir = bronze_dir(cfg)
    ensure_dir(str(outdir))

    seg_time = int(cfg["recording"]["segment_time_sec"])  # si lo moviste a recording, usa cfg["recording"]["segment_time_sec"]
    total = int(cfg["program_duration_sec"])
    copy_mode = bool(cfg.get("copy_mode", True))

    tzinfo = tz.gettz(cfg["timezone"])
    now = datetime.now(tzinfo)
    pattern = str(outdir / ("raw_segment_%03d_" + strftime_for_file(now) + ".ts"))

    stream_url = (cfg.get("stream_url") or "").strip()
    page_url   = (cfg.get("stream_page_url") or "").strip()

    # 🔹 RESOLVER RUTA DE FFMPEG (y de streamlink para el fallback)
    ffmpeg_bin = cfg.get("paths", {}).get("ffmpeg") or shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise SystemExit("ffmpeg no encontrado. Agrega paths.ffmpeg en config.yaml o ponlo en PATH.")
    streamlink_bin = cfg.get("paths", {}).get("streamlink") or shutil.which("streamlink")

    if stream_url:
        cmd = [
            ffmpeg_bin, "-hide_banner", "-loglevel", "warning", "-y",
            "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_on_network_error", "1",
            "-reconnect_delay_max", "5", "-rw_timeout", "15000000", "-timeout", "15000000",
            "-i", stream_url,
        ]
        if copy_mode:
            cmd += ["-map", "0:a:0", "-c", "copy"]
        else:
            cmd += ["-vn", "-c:a", "aac", "-b:a", cfg.get("aac_bitrate", "128k")]
        cmd += [
            "-f", "segment",
            "-segment_time", str(seg_time),
            "-segment_format", "adts",   # 👈 muxer correcto para AAC ADTS
            "-reset_timestamps", "1",
            "-t", str(total),
            pattern
        ]

        print("Running:", " ".join(shlex.quote(x) for x in cmd))
        rc = subprocess.call(cmd)
        if rc != 0 and page_url and streamlink_bin:
            # Fallback via streamlink (usa binario resuelto)
            codec_args = "-map 0:a:0 -c copy" if copy_mode else f"-vn -c:a aac -b:a {cfg.get('aac_bitrate','128k')}"
            cmd2 = (
                f"{shlex.quote(streamlink_bin)} --retry-streams 3 --retry-open 2 --stdout {shlex.quote(page_url)} best | "
                f"{shlex.quote(ffmpeg_bin)} -hide_banner -loglevel warning -y -i - "
                f"{codec_args} -f segment -segment_time {seg_time} -t {total} -strftime 1 {shlex.quote(pattern)}"
            )
            print("Fallback (streamlink):", cmd2)
            return subprocess.call(cmd2, shell=True)
        return rc

    elif page_url:
        if not streamlink_bin:
            raise SystemExit("streamlink no encontrado para usar stream_page_url; instala streamlink o usa stream_url directo.")
        codec_args = "-map 0:a:0 -c copy" if copy_mode else f"-vn -c:a aac -b:a {cfg.get('aac_bitrate','128k')}"
        cmd = (
            f"{shlex.quote(streamlink_bin)} --stdout {shlex.quote(page_url)} best | "
            f"{shlex.quote(ffmpeg_bin)} -hide_banner -loglevel warning -y -i - "
            f"{codec_args} -f segment -segment_time {seg_time} -t {total} -strftime 1 {shlex.quote(pattern)}"
        )
        print("Running (piped):", cmd)
        return subprocess.call(cmd, shell=True)

    else:
        raise SystemExit("Config: set either stream_url or stream_page_url")
