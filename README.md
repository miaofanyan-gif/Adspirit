# Adspirit — Automated Short-Video Advertisement Generation

CS697 capstone project (Northern Arizona University), group **Adspirit**:
Fanyan Miao, Manikanta, Hariprasad. Supervisor: Dr. Ayotuyi Tosin Akinola.

Given a TikTok Shop product link, the system retrieves popular related TikTok
videos, analyses them with Claude, writes a storyboard, generates shot clips
with Kling 3.0 (image-to-video) and assembles a rough cut for final editing.

> Status: work in progress. All pipeline stages are still mock implementations.

## Run locally

Backend:

```
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY and VIDEO_GEN_API_KEY
uvicorn api:app --reload --port 8000
```

Frontend:

```
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Notes

- Never commit `.env`, the SQLite database, downloaded TikTok videos or
  generated clips (see `.gitignore`).
- Generated videos are for academic evaluation only and are labelled as
  AI-generated.
