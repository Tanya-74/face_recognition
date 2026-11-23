"use strict";
/* Page logic. No libraries, no outside requests. */

const $ = (id) => document.getElementById(id);
const IMAGE_EXT = /\.(jpe?g|png|bmp|webp)$/i;
const BATCH = 6;                       // folder photos sent per request

const el = {
  status: $("engine-status"), error: $("error"), lib: $("lib"),
  pickFolder: $("pick-folder"), folderInput: $("folder-input"), folderInfo: $("folder-info"),
  pickGroup: $("pick-group"), groupInput: $("group-input"), groupInfo: $("group-info"),
  run: $("run"), cancel: $("cancel"),
  progress: $("progress"), barFill: $("bar-fill"), progressText: $("progress-text"),
  threshold: $("threshold"), thresholdValue: $("threshold-value"),
  results: $("results"), summary: $("summary"), canvas: $("canvas"), rows: $("rows"),
  notes: $("notes"), notesTitle: $("notes-title"), notesList: $("notes-list"),
};

const state = {
  ready: false,
  folderFiles: [],          // accepted picture files from the folder
  folderIgnored: 0,         // files that were not pictures
  groupFile: null,
  sessionId: null,
  loadedKey: null,          // identifies the folder that is already processed on the server
  analysis: null,           // last answer for the group photo
  image: null,              // loaded <img> of the processed group photo
  notes: [],                // messages about skipped / special folder photos
  abort: null,
};

/* ---------- small helpers ---------- */
function showError(msg, warn = false) {
  el.error.textContent = msg;
  el.error.classList.toggle("warn", warn);
  el.error.hidden = false;
  el.error.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
function clearError() { el.error.hidden = true; el.error.textContent = ""; }
function plural(n, one, many) { return `${n} ${n === 1 ? one : many}`; }
function folderKey() {
  return state.folderFiles.map((f) => `${f.name}|${f.size}|${f.lastModified}`).join("\n");
}
function updateRunButton() {
  el.run.disabled = !(state.ready && state.folderFiles.length && state.groupFile);
}
function setProgress(fraction, text, busy = false) {
  el.progress.hidden = false;
  const bar = el.progress.querySelector(".bar");
  bar.classList.toggle("busy", busy);
  const pct = Math.round(fraction * 100);
  el.barFill.style.width = pct + "%";
  bar.setAttribute("aria-valuenow", String(pct));
  el.progressText.textContent = text;
}

async function api(path, options) {
  let res;
  try {
    res = await fetch(path, options);
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw new Error("Cannot reach the app. Is the black window (server) still running?");
  }
  let body = null;
  try { body = await res.json(); } catch (_) { /* not JSON */ }
  if (!res.ok) throw new Error((body && body.detail) || `The app answered with an error (${res.status}).`);
  return body;
}

/* ---------- engine status ---------- */
async function pollStatus() {
  try {
    const s = await api("/api/status");
    el.lib.textContent = s.library;
    if (s.error) {
      el.status.textContent = "Face models not found";
      el.status.className = "pill bad";
      showError(s.error);
      return;
    }
    if (s.ready) {
      state.ready = true;
      el.status.textContent = "Ready - works offline";
      el.status.className = "pill ok";
      updateRunButton();
      return;
    }
    el.status.textContent = "Starting up (loading the face models)...";
  } catch (e) {
    el.status.textContent = "Not connected";
    el.status.className = "pill bad";
  }
  setTimeout(pollStatus, 1000);
}

/* ---------- step 1: folder ---------- */
el.pickFolder.addEventListener("click", () => el.folderInput.click());
el.folderInput.addEventListener("change", () => {
  clearError();
  const all = Array.from(el.folderInput.files);
  state.folderFiles = all.filter((f) => IMAGE_EXT.test(f.name));
  state.folderIgnored = all.length - state.folderFiles.length;
  if (!all.length) {
    el.folderInfo.textContent = "";
  } else if (!state.folderFiles.length) {
    el.folderInfo.textContent = "";
    showError("That folder has no pictures in it. Choose a folder with JPG, PNG, BMP or WEBP photos.");
  } else {
    let t = `✓ ${plural(state.folderFiles.length, "photo", "photos")} found`;
    if (state.folderIgnored) t += ` (${plural(state.folderIgnored, "other file", "other files")} will be ignored)`;
    el.folderInfo.textContent = t;
  }
  updateRunButton();
});

/* ---------- step 2: group photo ---------- */
el.pickGroup.addEventListener("click", () => el.groupInput.click());
el.groupInput.addEventListener("change", () => {
  clearError();
  const f = el.groupInput.files[0] || null;
  state.groupFile = f;
  if (f && !f.type.startsWith("image/") && !IMAGE_EXT.test(f.name)) {
    state.groupFile = null;
    el.groupInfo.textContent = "";
    showError("That file is not a picture. Please choose a JPG, PNG, BMP or WEBP photo.");
  } else {
    el.groupInfo.textContent = f ? `✓ ${f.name}` : "";
  }
  updateRunButton();
});

/* ---------- step 3: run ---------- */
el.cancel.addEventListener("click", () => { if (state.abort) state.abort.abort(); });

el.run.addEventListener("click", async () => {
  clearError();
  state.abort = new AbortController();
  el.run.disabled = true;
  el.cancel.hidden = false;
  el.pickFolder.disabled = el.pickGroup.disabled = true;
  try {
    await processFolderIfNeeded();
    await analyseGroup();
    el.progress.hidden = true;
  } catch (e) {
    el.progress.hidden = true;
    if (e.name === "AbortError") {
      state.loadedKey = null;                // folder only partly processed
      showError("Cancelled. Press Run to start again.", true);
    } else {
      showError(e.message);
    }
  } finally {
    el.cancel.hidden = true;
    el.pickFolder.disabled = el.pickGroup.disabled = false;
    updateRunButton();
  }
});

async function processFolderIfNeeded() {
  const key = folderKey();
  if (state.sessionId && state.loadedKey === key) {
    setProgress(1, "Known people are already processed - skipping that step.");
    return;                                  // cached embeddings on the server
  }
  state.sessionId = null;
  state.loadedKey = null;
  state.notes = [];
  const { session_id } = await api("/api/session", { method: "POST", signal: state.abort.signal });
  const files = state.folderFiles;
  let done = 0, people = 0, used = 0;
  for (let i = 0; i < files.length; i += BATCH) {
    const batch = files.slice(i, i + BATCH);
    const form = new FormData();
    batch.forEach((f) => form.append("files", f, f.name));
    setProgress(done / files.length,
      `Reading known people: ${done} of ${files.length} photos (${batch[0].name})`);
    const r = await api(`/api/session/${session_id}/known`, { method: "POST", body: form, signal: state.abort.signal });
    r.results.forEach((x) => {
      if (x.status === "ok") used++;
      if (x.note) state.notes.push(`${x.file}: ${x.note}`);
    });
    people = r.people;
    done += batch.length;
  }
  setProgress(1, `Known people ready: ${plural(people, "person", "people")}.`);
  if (used === 0) {
    showNotes();
    throw new Error("None of the photos in the folder showed a face I could use, so there is nobody to look for. " +
      "Check the notes below, then choose another folder.");
  }
  state.sessionId = session_id;
  state.loadedKey = folderKey();
}

async function analyseGroup() {
  setProgress(1, "Looking at the group photo...", true);
  const form = new FormData();
  form.append("file", state.groupFile, state.groupFile.name);
  let data;
  try {
    data = await api(`/api/session/${state.sessionId}/group`, { method: "POST", body: form, signal: state.abort.signal });
  } catch (e) {
    if (/expired/.test(e.message)) { state.sessionId = null; state.loadedKey = null; }
    throw e;
  }
  state.analysis = data;
  state.image = await loadImage(data.image);
  el.results.hidden = false;
  render();
  showNotes();
  el.results.scrollIntoView({ behavior: "smooth", block: "start" });
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("The group photo could not be shown."));
    img.src = src;
  });
}

function showNotes() {
  if (!state.notes.length) { el.notes.hidden = true; return; }
  el.notes.hidden = false;
  el.notesTitle.textContent = `Notes about the folder (${state.notes.length})`;
  el.notesList.replaceChildren(...state.notes.map((n) => {
    const li = document.createElement("li"); li.textContent = n; return li;
  }));
}

/* ---------- threshold + drawing (no server calls here) ---------- */
function labelFor(face, t) {
  const known = face.distance <= t;
  return { known, name: known ? face.nearest : "Unknown" };
}

el.threshold.addEventListener("input", () => {
  el.thresholdValue.textContent = Number(el.threshold.value).toFixed(2);
  if (state.analysis) render();
});

function render() {
  const t = Number(el.threshold.value);
  const a = state.analysis;
  const img = state.image;
  const faces = a.faces.map((f) => ({ ...f, ...labelFor(f, t) }));

  /* summary */
  if (!faces.length) {
    el.summary.textContent = "No faces were found in the group photo. Try a clearer or larger photo.";
  } else {
    const k = faces.filter((f) => f.known).length;
    el.summary.textContent = `${plural(faces.length, "face", "faces")} found: ${k} known, ${faces.length - k} unknown.`;
  }

  /* picture with boxes */
  const c = el.canvas;
  c.width = img.naturalWidth; c.height = img.naturalHeight;
  const g = c.getContext("2d");
  g.drawImage(img, 0, 0);
  const fontPx = Math.max(15, Math.round(c.width / 55));
  const line = Math.max(2, Math.round(c.width / 450));
  g.font = `600 ${fontPx}px "Segoe UI", system-ui, Arial, sans-serif`;
  g.textBaseline = "middle";
  faces.forEach((f) => {
    const x = f.box.x * c.width, y = f.box.y * c.height, w = f.box.w * c.width, h = f.box.h * c.height;
    const color = f.known ? "#17803d" : "#b45309";
    g.lineWidth = line; g.strokeStyle = color; g.strokeRect(x, y, w, h);
    const text = `${f.id}. ${f.name}`;
    const padX = fontPx * 0.45, boxH = fontPx * 1.5;
    const tw = g.measureText(text).width + padX * 2;
    let lx = Math.min(Math.max(0, x), Math.max(0, c.width - tw));
    let ly = y - boxH; if (ly < 0) ly = y;           // no room above: put the label inside the box
    g.fillStyle = color; g.fillRect(lx, ly, tw, boxH);
    g.fillStyle = "#fff"; g.fillText(text, lx + padX, ly + boxH / 2);
  });

  /* results list */
  const rows = faces.map((f) => {
    const tr = document.createElement("tr");
    const cells = [String(f.id), null, f.distance.toFixed(3), null];
    cells.forEach((txt, i) => {
      const td = document.createElement("td");
      if (i === 1) {
        td.textContent = f.name;
        td.style.fontWeight = "600";
        if (!f.known) {
          const hint = document.createElement("span");
          hint.className = "hint";
          hint.textContent = `closest: ${f.nearest}`;
          td.appendChild(hint);
        }
      } else if (i === 3) {
        const b = document.createElement("span");
        b.className = "badge " + (f.known ? "known" : "unknown");
        b.textContent = f.known ? "Known" : "Unknown";
        td.appendChild(b);
      } else {
        td.textContent = txt;
      }
      tr.appendChild(td);
    });
    return tr;
  });
  el.rows.replaceChildren(...rows);
}

pollStatus();
