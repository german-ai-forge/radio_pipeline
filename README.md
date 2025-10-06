📝 Project Bio

The Radio Data Pipeline is an experimental project that combines AI-powered transcription and classification with modern data pipeline practices.
It was designed to:

Capture live audio streams from radio stations.
Use Whisper for speech-to-text transcription.
Apply Mistral LLM and heuristic functions to classify content (ads, music, talk/news).
Organize and store the data in a Delta Lake architecture (Bronze → Silver → Gold).
Unlike pure AI-only approaches, this project leverages heuristics (rules-based functions) to improve accuracy. For example:
Detecting ad segments based on duration patterns or repeated keywords (e.g., “call now”, “discount”, “promo”).
Filtering music by identifying long non-speech sequences.
Classifying talk/news using both LLM reasoning and keyword heuristics.

🧩 Hybrid AI + Heuristics Approach

This project doesn’t rely only on LLMs for classification — it combines semantic reasoning from Mistral with rules-based heuristics for higher accuracy and explainability.

Why Hybrid?

LLMs are powerful but can be inconsistent with edge cases.
Heuristics provide deterministic, fast checks for common patterns.
Together, they create a reliable classification pipeline.
Example Heuristics

Advertisement detection:
Segment < 15 seconds and contains words like “discount”, “call now”, “limited offer” → classify as Ad.

Music detection:
Long continuous segments without speech → classify as Music.

Talk/News detection:
Contains named entities (politicians, locations, sports teams) → likely Talk/News.

Execution Flow

Whisper generates raw transcript.
Heuristic functions run first-pass classification.
Mistral LLM validates, overrides, or enriches the classification.
Final labeled data is stored in the Gold layer.

This project serves as a real-world case study for building scalable AI-driven pipelines that transform unstructured media (audio) into structured, analytics-ready datasets.
---

## 🗂️ Project Structure

radio_datalake_python/
│── README.md
│── requirements.txt
│── main.py # Orchestrates pipeline execution
│── extract.py # Handles raw audio ingestion
│── transcribe.py # Whisper transcription logic
│── classify.py # LLM (Mistral) classification & enrichment
│── delta_utils.py # Save & manage Delta Lake data
│── process_audio.py # Cleansing, segmentation, normalization
│── schema.py # Defines data schemas (Bronze/Silver/Gold)
│── notebooks/ # Jupyter notebooks for EDA & experiments
│── data/
├── bronze/ # Raw ingested audio & metadata
├── silver/ # Cleaned transcripts with labels
└── gold/ # Enriched analytics-ready datasets




## ⚙️ Installation

```bash
git clone https://github.com/german-ai-forge/radio_datalake_python.git
cd radio_datalake_python
pip install -r requirements.txt
🚀 Usage
1. Extract & Transcribe Radio Audio
bash
Copy code
python extract.py --source <radio_stream_url>
python transcribe.py --input data/bronze/audio_file.wav --output data/silver/
2. Classify Content with Mistral LLM
bash
Copy code
python classify.py --input data/silver/transcripts.json --output data/gold/
👉 Example task: Detect ads vs. music vs. talk segments.

3. Full Pipeline Orchestration
bash
Copy code
python main.py --source <radio_stream_url>
📊 Data Pipeline Layers
Bronze: Raw audio & basic metadata.

Silver: Transcribed & cleaned text (via Whisper).

Gold: Enriched, LLM-classified transcripts with analytics.

🧠 LLM Integration
Whisper (Speech-to-Text)
Converts raw radio audio into text transcripts.

Supports multilingual transcription.

Example usage in transcribe.py.

Mistral (Ad & Content Classification)
Classifies transcript segments:

🎵 Music

📰 News/Talk

📢 Advertisement

Example usage in classify.py.

🔮 Future Improvements
GPU acceleration for Whisper transcription.

Real-time stream ingestion.

Dashboard with ad frequency analysis.

Multi-radio comparison analytics.
