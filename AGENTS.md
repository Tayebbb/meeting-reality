---
Rules:

- Every endpoint must have tests.
- Use type hints.
- Return JSON.
- Run pytest before completing.
- This project is stress-tested against OpenRouter, never the real OpenAI API.
  All model calls go through OpenRouter (https://openrouter.ai/api/v1) using
  the `openai` SDK pointed at that base_url. Do not call api.openai.com.
- Load OPENROUTER_API_KEY via python-dotenv, never hardcode it.
- Use model "openai/gpt-5-mini" (OpenRouter model slug) for all calls unless told otherwise.
- Speaker diarization for uploaded recordings (mp4/audio) goes through
  AssemblyAI, never a self-hosted Whisper/pyannote pipeline. Load
  ASSEMBLYAI_API_KEY via python-dotenv, never hardcode it.
---
