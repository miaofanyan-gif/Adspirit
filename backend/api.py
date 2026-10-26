import asyncio
import json

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from db import SessionLocal, Task, create_task, get_task_with_stages, init_db
from graph import resume_pipeline, run_pipeline

app = FastAPI(title="CS697 pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


class CreateTaskRequest(BaseModel):
    product_url: str


@app.post("/tasks")
def create_task_endpoint(body: CreateTaskRequest, background_tasks: BackgroundTasks) -> dict:
    session = SessionLocal()
    try:
        task_id = create_task(session, body.product_url)
    finally:
        session.close()
    background_tasks.add_task(run_pipeline, task_id, body.product_url)
    return {"task_id": task_id}


@app.get("/tasks")
def list_tasks() -> list[dict]:
    session = SessionLocal()
    try:
        tasks = session.query(Task).order_by(Task.created_at.desc()).all()
        return [
            {
                "task_id": t.task_id,
                "product_url": t.product_url,
                "status": t.status,
                "current_stage": t.current_stage,
            }
            for t in tasks
        ]
    finally:
        session.close()


@app.get("/tasks/{task_id}")
def get_task_endpoint(task_id: str) -> dict:
    session = SessionLocal()
    try:
        task = get_task_with_stages(session, task_id)
    finally:
        session.close()
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.post("/tasks/{task_id}/resume")
def resume_task_endpoint(task_id: str, background_tasks: BackgroundTasks) -> dict:
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
    finally:
        session.close()
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status != "waiting_for_review":
        raise HTTPException(status_code=400, detail="task is not waiting for review")
    background_tasks.add_task(resume_pipeline, task_id)
    return {"task_id": task_id}


@app.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    async def event_generator():
        last_payload = None
        while True:
            session = SessionLocal()
            try:
                task = get_task_with_stages(session, task_id)
            finally:
                session.close()
            if task is None:
                break
            payload = json.dumps(task)
            if payload != last_payload:
                yield {"event": "task_update", "data": payload}
                last_payload = payload
            if task["status"] in ("completed", "failed", "waiting_for_review"):
                break
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
