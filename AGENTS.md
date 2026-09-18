---
Rules:

- Use type hints.
- Return JSON.
- This project runs entirely on OpenAI's paid API (api.openai.com) via the
  `openai` SDK's default base_url. There is no OpenRouter or other provider
  fallback — do not repoint the client at a different base_url.
- Load OPENAI_API_KEY via python-dotenv, never hardcode it.
- Use model "gpt-3.5-turbo" for all LLM calls (synthesis, recap, speaker
  identification) unless told otherwise.
- Rate-limited calls (429) occasionally happen under load — that's routine,
  expected behavior, not a hard failure. Model calls go through
  `_call_with_retry` in main.py, which retries 429s with backoff; do not
  remove that or replace it with a bare try/except that swallows the error.
- Transcription for uploaded recordings (mp4/audio) goes through OpenAI's
  Whisper API (`whisper-1`), never a self-hosted Whisper/pyannote pipeline.
  Whisper does not return speaker diarization natively — speaker labels are
  identified via a separate LLM call in `_openai_transcribe` and returned
  as generic "User 1", "User 2", ... placeholders for the frontend to
  rename. Do not reintroduce AssemblyAI or any other third-party
  transcription provider.
---
