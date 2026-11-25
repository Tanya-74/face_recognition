"""FastAPI app: serves the page and a small JSON API.

Run from the project folder:  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Everything is local: no CDN, no outside calls. Models come from ./models.
"""
import logging
import os
import sys
import threading
from contextlib import asynccontextmanager
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # so "import face_backend" works

from fastapi import Body, FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import engine
import face_backend
import learned
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
@app.exception_handler(learned.StoreError)
async def problem_handler(request: Request, exc: Exception):
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


@app.post("/api/session/{sid}/label")
def label_face(sid: str, body: Any = Body(None)):
    """Remember one face of the latest group scan under a name typed by the user."""
    session = engine.get_session(sid)
    if not isinstance(body, dict):
        raise Problem("The request was not understood.")
    return session.label(body.get("analysis_id"), body.get("face_id"), body.get("name"))


@app.get("/api/people")
def saved_people():
    """Names saved by labelling faces, with how many samples each has. No embeddings."""
    return {"people": engine.saved_people()}


@app.delete("/api/people")
def forget_person(name: str = ""):
    """Delete every saved sample of one name."""
    return {"removed": engine.forget_person(name)}


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
