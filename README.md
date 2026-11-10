# CINEMORA AI

A starter full-stack AI movie creation app. The frontend is React/Vite; the backend is FastAPI.

## What works
- Create a project from a movie idea.
- Generate a structured screenplay with OpenAI.
- Request AI video clips through fal.ai (requires a compatible model and API key).
- View generated projects and clip URLs in the app.

## Important limitations
This is deployable source code, not a hosted service. Video generation requires provider credentials and may incur charges. The backend currently requests scene clips; it does not automatically stitch them into one finished 60-second movie. "Publish" is an in-app project status, not publishing to social media.

## Local development
Backend:
```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn main:app --reload
```
Frontend:
```bash
cd frontend
npm install
npm run dev
```

Set `OPENAI_API_KEY`, `FAL_KEY`, and `FAL_TEXT_TO_VIDEO_MODEL` in the backend environment. Never commit secrets or `.env` files.services:
  - type: web
    name: cinemora-ai-api
    runtime: docker
    rootDir: backend
    plan: free
    healthCheckPath: /health
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: FAL_KEY
        sync: false
      - key: FAL_TEXT_TO_VIDEO_MODEL
        sync: false
      - key: CORS_ORIGINS
        sync: false
