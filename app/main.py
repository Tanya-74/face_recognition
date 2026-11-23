"""FastAPI app: serves the page and a small JSON API.

Run from the project folder:  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Everything is local: no CDN, no outside calls. Models come from ./models.
"""
import logging
import os
import sys
import threading
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # so "import face_backend" works

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import engine
import face_backend
from engine import Problem

log = logging.getLogger("uvicorn.error")
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
state = {"ready": False, "error": ""}


def _warm_up():
    """Load the models in the background so the first Run is quick."""
    try:
        face_backend.load()
        state["ready"] = True
    except Exception as e:
        state["error"] = str(e)
        log.error("Model loading failed: %s", e)


@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=_warm_up, daemon=True).start()
    yield


app = FastAPI(title="Face Recognition (offline)", lifespan=lifespan)


@app.exception_handler(Problem)
async def problem_handler(request: Request, exc: Problem):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(Exception)
async def crash_handler(request: Request, exc: Exception):
    log.exception("Unexpected error")
    return JSONResponse({"detail": "Something went wrong on the server. "
                                   "Please try again; if it keeps happening, restart the app."},
                        status_code=500)


@app.get("/api/status")
def status():
    return {"ready": state["ready"], "error": state["error"], "library": face_backend.NAME}


@app.post("/api/session")
def create_session():
    if state["error"]:
        raise Problem(state["error"])
    return {"session_id": engine.new_session()}


@app.post("/api/session/{sid}/known")
def add_known(sid: str, files: list[UploadFile] = File(...)):
    """Process a batch of known-people photos (the page sends a few at a time)."""
    session = engine.get_session(sid)
    results = []
    for f in files:
        data = f.file.read(engine.MAX_FILE_BYTES + 1)
        results.append(session.add_reference(f.filename or "", data))
    return {"results": results, "people": session.n_people, "photos": session.n_photos}


@app.post("/api/session/{sid}/group")
def analyse_group(sid: str, file: UploadFile = File(...)):
    session = engine.get_session(sid)
    data = file.file.read(engine.MAX_FILE_BYTES + 1)
    return session.analyse_group(data, file.filename or "group photo")


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
