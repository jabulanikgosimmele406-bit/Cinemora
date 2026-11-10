import os, json, uuid, asyncio
from pathlib import Path
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI(title="CINEMORA AI API")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
DB = Path("projects.json")

def load_projects():
    return json.loads(DB.read_text()) if DB.exists() else []

def save_projects(items):
    DB.write_text(json.dumps(items, indent=2))

class CreateRequest(BaseModel):
    idea: str
    style: str = "Ultra realistic"
    duration_seconds: int = 60
    generate_video: bool = False

@app.get("/health")
def health():
    return {"status": "ok", "app": "CINEMORA AI"}

@app.get("/api/projects")
def projects():
    return load_projects()

@app.post("/api/create")
async def create(req: CreateRequest, background: BackgroundTasks):
    if not req.idea.strip():
        raise HTTPException(400, "Please enter a movie idea.")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(503, "OPENAI_API_KEY is not configured on the server.")
    client = OpenAI(api_key=key)
    prompt = f"""Create an original {req.duration_seconds}-second {req.style} movie screenplay from this idea: {req.idea}
Return valid JSON only with keys title, logline, scenes. scenes must be an array of 5 objects, each with time, visual, camera, dialogue, sound, transition."""
    try:
        result = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type":"json_object"},
            messages=[{"role":"system","content":"You are CINEMORA AI, a concise film screenplay generator."},{"role":"user","content":prompt}],
            temperature=0.8
        )
        script = json.loads(result.choices[0].message.content)
    except Exception as e:
        raise HTTPException(502, f"Screenplay generation failed: {str(e)}")
    project = {"id": str(uuid.uuid4()), "idea": req.idea, "style": req.style, "status":"screenplay_ready", "script":script, "clips":[], "published":False}
    items = load_projects(); items.insert(0, project); save_projects(items)
    if req.generate_video:
        background.add_task(generate_clips, project["id"])
    return project

async def generate_clips(project_id: str):
    token = os.getenv("FAL_KEY")
    model = os.getenv("FAL_TEXT_TO_VIDEO_MODEL")
    if not token or not model:
        return
    items = load_projects()
    project = next((p for p in items if p["id"] == project_id), None)
    if not project: return
    project["status"] = "generating_video"
    save_projects(items)
    clips = []
    async with httpx.AsyncClient(timeout=60) as client:
        for scene in project["script"].get("scenes", []):
            prompt = "Cinematic realistic film shot. " + str(scene.get("visual",""))
            try:
                r = await client.post(f"https://queue.fal.run/{model}", headers={"Authorization":f"Key {token}"}, json={"prompt":prompt})
                r.raise_for_status()
                data = r.json()
                clips.append({"scene":scene.get("time"),"request_id":data.get("request_id"),"status_url":data.get("status_url"),"response_url":data.get("response_url")})
            except Exception as e:
                clips.append({"scene":scene.get("time"),"error":str(e)})
    items = load_projects()
    project = next((p for p in items if p["id"] == project_id), None)
    if project:
        project["clips"] = clips
        project["status"] = "video_requests_submitted"
        save_projects(items)

@app.post("/api/projects/{project_id}/publish")
def publish(project_id: str):
    items = load_projects()
    project = next((p for p in items if p["id"] == project_id), None)
    if not project: raise HTTPException(404, "Project not found")
    project["published"] = True
    save_projects(items)
    return project
