# Radio Data Lake (Python)

Pipeline para **grabar una radio online**, **segmentar cada 10–15 min**, **transcribir** con Whisper,
**detectar y remover comerciales** (heurísticas) y **armar un programa final limpio** (sin cortes).

## Capas del Data Lake
- **Bronze**: audio crudo segmentado por fecha (`data/bronze/YYYY/MM/DD/*.ts`).
- **Silver**: transcripciones y metadatos (`data/silver/YYYY/MM/DD/*.vtt|.jsonl`).
- **Gold**: audio final sin comerciales (`data/gold/YYYY/MM/DD/program_clean.mp3`).

## Requisitos
- **FFmpeg** (obligatorio)  
- **streamlink** (recomendado si solo tenés URL del *player*, no la .m3u8)  
- **Python 3.10+**  
- (Opcional) **openai-whisper** o **faster-whisper** para transcripción

**Instalación rápida (Ubuntu/Debian):**
```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
pip install streamlink
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# para transcribir: elige una
pip install openai-whisper    # o: pip install faster-whisper
```

## Configuración
Editá `config.yaml` (URL del stream, duración, tamaño de segmento, modelo Whisper, etc.).  
- **`stream_url`**: URL directa (.m3u8/.mp3).  
- **`stream_page_url`**: URL del reproductor si necesitás `streamlink`.

## Estructura de salida
```
data/
  bronze/YYYY/MM/DD/
    raw_segment_000_20250904-1900.ts
    raw_segment_001_20250904-1915.ts
    manifest.jsonl
  silver/YYYY/MM/DD/
    raw_segment_000.vtt
    raw_segment_001.vtt
  gold/YYYY/MM/DD/
    keeplist.txt
    program_clean.ts
    program_clean.mp3
```

## Uso (CLI)
Desde la raíz del proyecto:

1) **Grabar y segmentar**
```bash
python -m src.pipeline record
```

2) **Manifest**
```bash
python -m src.pipeline manifest
```

3) **Transcribir**
```bash
python -m src.pipeline transcribe
```

4) **Detectar comerciales**
```bash
python -m src.pipeline detect-ads
```

5) **Ensamblar limpio**
```bash
python -m src.pipeline assemble
```

6) **Post-proceso completo (sin la grabación)**
```bash
python -m src.pipeline run-post
```

## Cron de ejemplo
Programa 19:00–21:00 (inicia 5 min antes y post-proceso a las 21:10). Editá rutas.
```cron
55 18 * * * /usr/bin/python3 /path/radio_datalake_python/src/pipeline.py record >> /path/radio_datalake_python/logs/record_$(date +\%Y\%m\%d).log 2>&1
10 21 * * * /usr/bin/python3 /path/radio_datalake_python/src/pipeline.py run-post >> /path/radio_datalake_python/logs/post_$(date +\%Y\%m\%d).log 2>&1
```

## Legal
Uso personal salvo permiso. Revisá términos de la radio.
