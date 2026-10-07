import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from core.config import config
from core.ollama_client import ollama_client
from core.llm_provider import llm_provider
from core.agent import agent
from core.tools import (
    get_system_info, get_notes, save_note,
    get_todos, add_todo, complete_todo,
    add_knowledge_document, search_knowledge_base
)
from voice.tts import tts

app = FastAPI(title=config.PROJECT_NAME, version=config.VERSION)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    voice_output: bool = False

class ApiKeyRequest(BaseModel):
    provider: str
    key: str

class NoteRequest(BaseModel):
    title: str
    content: str
    tags: Optional[str] = ""

class TodoRequest(BaseModel):
    task: str
    priority: Optional[str] = "medium"

class PullModelRequest(BaseModel):
    model_name: str

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi import Response
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Personal AI Agent Web UI</h1>")

@app.get("/api/status")
async def get_status():
    provider_info = llm_provider.get_status_info()
    models = ollama_client.get_model_names() if provider_info["ollama_online"] else []
    sys_info = get_system_info()
    return {
        "provider": provider_info["provider"],
        "provider_name": provider_info["provider_name"],
        "configured": provider_info["configured"],
        "current_model": agent.model_name or provider_info["model"],
        "ollama_online": provider_info["ollama_online"],
        "ollama_version": ollama_client.get_version() if provider_info["ollama_online"] else None,
        "models": models,
        "system": sys_info
    }

@app.post("/api/config/key")
async def save_api_key(req: ApiKeyRequest):
    env_path = Path(__file__).resolve().parent.parent / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    
    key_var = "GEMINI_API_KEY" if req.provider == "gemini" else "GROQ_API_KEY"
    new_lines = []
    found_key = False
    found_prov = False
    for line in lines:
        if line.startswith(f"{key_var}="):
            new_lines.append(f"{key_var}={req.key}")
            found_key = True
        elif line.startswith("AI_PROVIDER="):
            new_lines.append(f"AI_PROVIDER={req.provider}")
            found_prov = True
        else:
            new_lines.append(line)
            
    if not found_key:
        new_lines.append(f"{key_var}={req.key}")
    if not found_prov:
        new_lines.append(f"AI_PROVIDER={req.provider}")
        
    env_path.write_text("\n".join(new_lines), encoding="utf-8")
    
    # Reload in-memory config
    if req.provider == "gemini":
        config.GEMINI_API_KEY = req.key
        config.AI_PROVIDER = "gemini"
        agent.set_model(config.GEMINI_DEFAULT_MODEL)
    elif req.provider == "groq":
        config.GROQ_API_KEY = req.key
        config.AI_PROVIDER = "groq"
        agent.set_model(config.GROQ_DEFAULT_MODEL)
        
    return {"success": True, "provider": req.provider}

@app.get("/api/models")
async def list_models():
    models = ollama_client.list_models()
    return {
        "installed": models,
        "recommended": [
            {"name": "llama3.2:3b", "desc": "Meta Llama 3.2 (3B) - Fast, lightweight, smart (Default)", "size": "~2.0 GB"},
            {"name": "llama3.2:1b", "desc": "Meta Llama 3.2 (1B) - Ultra-lightweight & fast", "size": "~1.3 GB"},
            {"name": "qwen2.5:3b", "desc": "Qwen 2.5 (3B) - Excellent coding & tool calling", "size": "~2.0 GB"},
            {"name": "phi3.5:mini", "desc": "Microsoft Phi 3.5 Mini (3.8B) - Strong reasoning", "size": "~2.2 GB"},
        ]
    }

@app.post("/api/models/pull")
async def pull_model(req: PullModelRequest):
    def event_stream():
        for progress in ollama_client.pull_model(req.model_name):
            yield f"data: {json.dumps(progress)}\n\n"
        yield "data: {\"status\": \"success\", \"completed\": true}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if req.model:
        agent.set_model(req.model)

    def event_generator():
        last_answer = ""
        for event in agent.run(req.message):
            if event["type"] == "done":
                last_answer = event["full_answer"]
                if req.voice_output and last_answer:
                    # Clean markdown formatting for spoken text
                    clean_text = last_answer.replace("*", "").replace("#", "").replace("`", "")
                    tts.speak(clean_text[:300])
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/system")
async def system_endpoint():
    return get_system_info()

@app.get("/api/notes")
async def get_notes_endpoint(q: str = ""):
    return get_notes(q)

@app.post("/api/notes")
async def create_note_endpoint(req: NoteRequest):
    return save_note(req.title, req.content, req.tags or "")

@app.get("/api/todos")
async def get_todos_endpoint(status: str = "pending"):
    return get_todos(status)

@app.post("/api/todos")
async def create_todo_endpoint(req: TodoRequest):
    return add_todo(req.task, req.priority or "medium")

@app.post("/api/todos/{todo_id}/complete")
async def complete_todo_endpoint(todo_id: int):
    return complete_todo(todo_id)

@app.post("/api/knowledge/upload")
async def upload_knowledge_file(file: UploadFile = File(...)):
    try:
        content = (await file.read()).decode("utf-8", errors="replace")
        res = add_knowledge_document(file.filename, content)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/speak")
async def speak_text(req: Dict[str, str]):
    text = req.get("text", "")
    if text:
        tts.speak(text)
    return {"status": "speaking"}
