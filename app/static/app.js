"use strict";
/* Page logic. No libraries, no outside requests. */

const $ = (id) => document.getElementById(id);
const IMAGE_EXT = /\.(jpe?g|png|bmp|webp)$/i;
const BATCH = 6;                       // folder photos sent per request

const el = {
  status: $("engine-status"), error: $("error"), lib: $("lib"),
  pickFolder: $("pick-folder"), folderInput: $("folder-input"), folderInfo: $("folder-info"), zoneFolder: $("zone-folder"),
  pickGroup: $("pick-group"), groupInput: $("group-input"), groupInfo: $("group-info"), zoneGroup: $("zone-group"),
  run: $("run"), cancel: $("cancel"),
  stage: $("stage"), empty: $("empty"), photo: $("results"), canvas: $("canvas"),
  progress: $("progress"), progressPct: $("progress-pct"), barFill: $("bar-fill"), progressText: $("progress-text"),
  threshold: $("threshold"), thresholdValue: $("threshold-value"),
  panel: document.querySelector(".panel"), summary: $("summary"), panelEmpty: $("panel-empty"), rows: $("rows"),
  stats: $("stats"), statTotal: $("stat-total"), statKnown: $("stat-known"), statUnknown: $("stat-unknown"),
  chips: $("chips"), chipAll: $("chip-all"), chipKnown: $("chip-known"), chipUnknown: $("chip-unknown"),
  openGallery: $("open-gallery"), galleryCount: $("gallery-count"), galleryDialog: $("gallery-dialog"),
  galleryTitle: $("gallery-title"), galleryGrid: $("gallery-grid"), galleryMore: $("gallery-more"),
  openNotes: $("open-notes"), notesCount: $("notes-count"), notesDialog: $("notes-dialog"),
  notesTitle: $("notes-title"), notesList: $("notes-list"),
  tools: $("tools"), dlPng: $("dl-png"), dlCsv: $("dl-csv"),
};

const state = {
  ready: false,
  folderFiles: [],          // accepted picture files from the folder
  people: new Map(),        // person name -> first picture file with that name (for showing the matched photo)
  photoUrls: new Map(),     // person name -> local object URL (made on demand, never uploaded)
  crops: [],                // small face pictures cut from the group photo, by face number
  folderIgnored: 0,         // files that were not pictures
  groupFile: null,
  sessionId: null,
  loadedKey: null,          // identifies the folder that is already processed on the server
  analysis: null,           // last answer for the group photo
  faces: [],                // faces with their label at the current threshold
  filter: "all",            // which faces to show: all | known | unknown
  hoverId: null,            // face under the mouse / keyboard focus
  selectedId: null,         // face the user clicked
  image: null,              // loaded <img> of the processed group photo
  notes: [],                // messages about skipped / special folder photos
  abort: null,
  reveal: null,             // box fade-in animation state
  animateRows: false,
  busy: false,              // true while Run is working (drops are ignored)
};

/* ---------- small helpers ---------- */
function showError(msg, warn = false) {
  el.error.textContent = msg;
  el.error.classList.toggle("warn", warn);
  el.error.hidden = false;
}
function clearError() { el.error.hidden = true; el.error.textContent = ""; }
/* restart a CSS animation class */
function replay(node, cls) { node.classList.remove(cls); void node.offsetWidth; node.classList.add(cls); }
function plural(n, one, many) { return `${n} ${n === 1 ? one : many}`; }
/* same rule as the server: 'dir/Priya Sharma.jpg' -> 'Priya Sharma' */
function personName(filename) {
  const base = filename.split(/[\\/]/).pop();
  const dot = base.lastIndexOf(".");
  return (dot > 0 ? base.slice(0, dot) : base).trim();
}
function indexPeople() {
  state.photoUrls.forEach((u) => URL.revokeObjectURL(u));
  state.photoUrls.clear();
  state.people = new Map();
  state.folderFiles.forEach((f) => {
    const n = personName(f.name);
    if (n && !state.people.has(n)) state.people.set(n, f);
  });
}
function photoUrl(name) {
  if (!state.people.has(name)) return null;
  if (!state.photoUrls.has(name)) state.photoUrls.set(name, URL.createObjectURL(state.people.get(name)));
  return state.photoUrls.get(name);
}
/* a small square picture of one face, cut from the group photo in the browser */
function makeCrops() {
  const img = state.image, W = img.naturalWidth, H = img.naturalHeight, OUT = 112;
  state.crops = state.analysis.faces.map((f) => {
    const bw = f.box.w * W, bh = f.box.h * H;
    const side = Math.max(bw, bh) * 1.5;                       // a little room around the face
    let sx = f.box.x * W + bw / 2 - side / 2, sy = f.box.y * H + bh / 2 - side / 2;
    sx = Math.min(Math.max(0, sx), Math.max(0, W - side)); sy = Math.min(Math.max(0, sy), Math.max(0, H - side));
    const s = Math.min(side, W, H);
    const c = document.createElement("canvas"); c.width = c.height = OUT;
    c.getContext("2d").drawImage(img, sx, sy, s, s, 0, 0, OUT, OUT);
    return c.toDataURL("image/jpeg", 0.85);
  });
}
function folderKey() {
  return state.folderFiles.map((f) => `${f.name}|${f.size}|${f.lastModified}`).join("\n");
}
/* the short text under the buttons and inside the drop zones */
function setFolderNote(text) { el.folderInfo.textContent = text; el.folderInfo.title = text; el.zoneFolder.textContent = text; }
function setGroupNote(text) { el.groupInfo.textContent = text; el.groupInfo.title = text; el.zoneGroup.textContent = text; }
function updateRunButton() {
  $("drop-folder").classList.toggle("done", state.folderFiles.length > 0);   // green when a step is finished
  $("drop-group").classList.toggle("done", !!state.groupFile);
  el.run.disabled = !(state.ready && state.folderFiles.length && state.groupFile);
}
function setProgress(fraction, text, busy = false) {
  el.progress.hidden = false;
  const bar = el.progress.querySelector(".bar");
  bar.classList.toggle("busy", busy);
  const pct = Math.round(fraction * 100);
  el.barFill.style.width = pct + "%";
  el.progressPct.textContent = busy ? "" : pct + "%";           // no percentage when we cannot know it
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

/* ---------- pop-up drawers ---------- */
document.querySelectorAll("dialog.drawer").forEach((dlg) => {
  dlg.addEventListener("click", (ev) => { if (ev.target === dlg) dlg.close(); });          // click on the dark area
  dlg.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => dlg.close()));
});

/* ---------- step 1: folder ---------- */
el.pickFolder.addEventListener("click", () => el.folderInput.click());
$("drop-folder").addEventListener("click", () => { if (!state.busy) el.folderInput.click(); });
el.folderInput.addEventListener("change", () => setFolder(Array.from(el.folderInput.files)));

function setFolder(all) {
  clearError();
  state.folderFiles = all.filter((f) => IMAGE_EXT.test(f.name));
  state.folderIgnored = all.length - state.folderFiles.length;
  indexPeople();
  if (!all.length) {
    setFolderNote("");
  } else if (!state.folderFiles.length) {
    setFolderNote("");
    showError("That folder has no pictures in it. Choose a folder with JPG, PNG, BMP or WEBP photos.");
  } else {
    let t = `✓ ${plural(state.folderFiles.length, "photo", "photos")} found`;
    if (state.folderIgnored) t += ` (${plural(state.folderIgnored, "other file", "other files")} will be ignored)`;
    setFolderNote(t);
  }
  renderGallery();
  updateRunButton();
}

/* ---------- gallery of the known people (a drawer, built from the local files) ---------- */
const GALLERY_FIRST = 48;                      // a huge folder is shown in two steps to keep it light
let galleryShowAll = false;

function renderGallery() {
  const names = Array.from(state.people.keys());
  galleryShowAll = false;
  el.galleryGrid.replaceChildren();
  el.openGallery.hidden = !names.length;
  el.galleryCount.textContent = `(${names.length})`;
  el.galleryTitle.textContent = `Known people in this folder (${names.length})`;
  if (el.galleryDialog.open) buildGallery();
}
function buildGallery() {
  const names = Array.from(state.people.keys());
  const shown = galleryShowAll ? names : names.slice(0, GALLERY_FIRST);
  if (el.galleryGrid.childElementCount !== shown.length) {
    el.galleryGrid.replaceChildren(...shown.map((n) => {
      const li = document.createElement("li");
      const img = document.createElement("img");
      img.className = "thumb"; img.alt = `Photo of ${n}`; img.loading = "lazy"; img.decoding = "async";
      img.src = photoUrl(n);
      img.addEventListener("error", () => { img.removeAttribute("src"); img.alt = "(cannot show this photo)"; });
      const cap = document.createElement("span"); cap.textContent = n; cap.title = n;
      li.append(img, cap);
      return li;
    }));
  }
  el.galleryMore.hidden = galleryShowAll || names.length <= GALLERY_FIRST;
  el.galleryMore.textContent = `Show all ${names.length} people`;
}
el.openGallery.addEventListener("click", () => { buildGallery(); el.galleryDialog.showModal(); });
el.galleryMore.addEventListener("click", () => { galleryShowAll = true; buildGallery(); });

/* ---------- step 2: group photo ---------- */
el.pickGroup.addEventListener("click", () => el.groupInput.click());
$("drop-group").addEventListener("click", () => { if (!state.busy) el.groupInput.click(); });
el.groupInput.addEventListener("change", () => setGroup(el.groupInput.files[0] || null));

function setGroup(f, extra = "") {
  clearError();
  state.groupFile = f;
  if (f && !f.type.startsWith("image/") && !IMAGE_EXT.test(f.name)) {
    state.groupFile = null;
    setGroupNote("");
    showError("That file is not a picture. Please choose a JPG, PNG, BMP or WEBP photo.");
  } else {
    setGroupNote(f ? `✓ ${f.name}${extra}` : "");
  }
  updateRunButton();
}

/* ---------- drag and drop ---------- */
const MAX_DROPPED = 20000;                     // safety stop when walking a dropped folder

function hasFiles(ev) { return ev.dataTransfer && Array.from(ev.dataTransfer.types || []).includes("Files"); }

async function readEntry(entry, out) {
  if (out.length >= MAX_DROPPED) return;
  if (entry.isFile) {
    try { out.push(await new Promise((res, rej) => entry.file(res, rej))); } catch (_) { /* unreadable file: skip */ }
  } else if (entry.isDirectory) {
    const reader = entry.createReader();
    for (;;) {                                  // readEntries returns the folder in chunks
      const chunk = await new Promise((res, rej) => reader.readEntries(res, rej)).catch(() => []);
      if (!chunk.length) break;
      for (const e of chunk) await readEntry(e, out);
    }
  }
}
/* every file in what was dropped, including files inside dropped folders */
async function filesFromDrop(dt) {
  const entries = Array.from(dt.items || [])
    .map((i) => (i.kind === "file" && i.webkitGetAsEntry ? i.webkitGetAsEntry() : null));   // must be read before any await
  if (!entries.length || entries.some((e) => !e)) return Array.from(dt.files);              // browser cannot list folders
  const out = [];
  for (const e of entries) await readEntry(e, out);
  return out;
}

function wireDrop(zone, onDrop, enabled = () => true) {
  let depth = 0;
  zone.addEventListener("dragenter", (ev) => {
    if (!hasFiles(ev) || state.busy || !enabled()) return;
    ev.preventDefault(); depth++; zone.classList.add("over");
  });
  zone.addEventListener("dragover", (ev) => {
    if (!hasFiles(ev) || !enabled()) return;
    ev.preventDefault();
    ev.dataTransfer.dropEffect = state.busy ? "none" : "copy";
  });
  zone.addEventListener("dragleave", () => {
    depth = Math.max(0, depth - 1);
    if (!depth) zone.classList.remove("over");
  });
  zone.addEventListener("drop", (ev) => {
    if (!enabled()) return;
    ev.preventDefault();
    depth = 0; zone.classList.remove("over");
    if (state.busy || !hasFiles(ev)) return;
    onDrop(ev.dataTransfer);
  });
}
function dropFolder(dt) {
  setFolderNote("Reading the dropped folder...");
  filesFromDrop(dt).then(setFolder);
}
function dropGroup(dt) {
  const files = Array.from(dt.files);
  const pics = files.filter((f) => f.type.startsWith("image/") || IMAGE_EXT.test(f.name));
  if (pics.length) setGroup(pics[0], pics.length > 1 ? ` (only the first of ${pics.length} photos is used)` : "");
  else setGroup(files[0] || null);              // shows the "not a picture" message
}
wireDrop($("drop-folder"), dropFolder);
wireDrop($("drop-group"), dropGroup);
/* once a result is on screen the drop zones are gone: a dropped folder is a new folder, a single photo a new group photo */
wireDrop(el.stage, (dt) => {
  const isFolder = Array.from(dt.items || []).some((i) => {
    const e = i.kind === "file" && i.webkitGetAsEntry ? i.webkitGetAsEntry() : null;
    return e && e.isDirectory;
  }) || dt.files.length > 1;
  if (isFolder) dropFolder(dt); else dropGroup(dt);
}, () => !el.photo.hidden);
/* a file dropped outside a drop zone must not make the browser leave the page */
["dragover", "drop"].forEach((t) => window.addEventListener(t, (ev) => { if (hasFiles(ev)) ev.preventDefault(); }));

/* ---------- step 3: run ---------- */
el.cancel.addEventListener("click", () => { if (state.abort) state.abort.abort(); });

el.run.addEventListener("click", async () => {
  clearError();
  state.abort = new AbortController();
  state.busy = true;
  el.tools.hidden = true;                    // no downloads while working (Cancel needs the room)
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
    state.busy = false;
    el.tools.hidden = !state.faces.length;     // downloads come back if there is a result to download
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
      "Open \"Folder notes\" at the top to see why, then choose another folder.");
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
  state.filter = "all";
  el.chips.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.filter === "all")));
  state.hoverId = state.selectedId = null;
  state.image = await loadImage(data.image);
  makeCrops();
  el.empty.hidden = true;
  el.photo.hidden = false;
  fitCanvas();
  state.animateRows = true;
  startReveal();                               // before the first draw, so the finished photo never flashes
  render();
  replay(el.photo, "enter");
  replay(el.panel, "enter");
  showNotes();
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
  const n = state.notes.length;
  el.openNotes.hidden = !n;
  el.notesCount.textContent = `(${n})`;
  el.notesTitle.textContent = `Notes about the folder (${n})`;
  el.notesList.replaceChildren(...state.notes.map((t) => {
    const li = document.createElement("li"); li.textContent = t; return li;
  }));
}
el.openNotes.addEventListener("click", () => el.notesDialog.showModal());

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
  state.faces = a.faces.map((f) => ({ ...f, ...labelFor(f, t) }));
  const faces = state.faces;

  /* summary */
  const knownCount = faces.filter((f) => f.known).length;
  if (!faces.length) {
    el.summary.textContent = "No faces were found in the group photo. Try a clearer or larger photo.";
  } else {
    el.summary.textContent = `${plural(faces.length, "face", "faces")} found: ${knownCount} known, ${faces.length - knownCount} unknown.`;
  }
  el.summary.classList.toggle("visually-hidden", faces.length > 0);   // the number cards show it instead
  el.panelEmpty.hidden = true;
  el.stats.hidden = el.chips.hidden = el.tools.hidden = !faces.length;
  el.statTotal.textContent = faces.length;
  el.statKnown.textContent = knownCount;
  el.statUnknown.textContent = faces.length - knownCount;

  el.chipAll.textContent = faces.length;
  el.chipKnown.textContent = knownCount;
  el.chipUnknown.textContent = faces.length - knownCount;
  drawCanvas();
  buildRows();
}

/* ---------- filter chips: All / Known / Unknown ---------- */
function visibleFaces() {
  return state.faces.filter((f) => state.filter === "all" || (state.filter === "known") === f.known);
}
el.chips.addEventListener("click", (ev) => {
  const b = ev.target.closest(".chip");
  if (!b || !state.analysis) return;
  state.filter = b.dataset.filter;
  el.chips.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === b)));
  state.hoverId = null;
  state.reveal = null;
  drawCanvas();
  buildRows();
});

/* ---------- the photo: sized to fit the area (no scrolling), boxes and labels drawn on a canvas ---------- */
function activeId() { return state.hoverId ?? state.selectedId; }

/* shows the whole photo inside the left area, keeping its shape */
function fitCanvas() {
  if (!state.image || el.photo.hidden) return;
  const pad = 12;
  const aw = el.photo.clientWidth - pad * 2, ah = el.photo.clientHeight - pad * 2;
  if (aw < 40 || ah < 40) return;
  const ratio = state.image.naturalWidth / state.image.naturalHeight;
  let w = aw, h = w / ratio;
  if (h > ah) { h = ah; w = h * ratio; }
  el.canvas.style.width = Math.floor(w) + "px";
  el.canvas.style.height = Math.floor(h) + "px";
}
new ResizeObserver(() => {
  fitCanvas();
  if (state.image && state.faces.length) drawCanvas();
}).observe(el.photo);

function drawCanvas() {
  const img = state.image;
  const c = el.canvas;
  if (c.width !== img.naturalWidth) { c.width = img.naturalWidth; c.height = img.naturalHeight; }
  const s = c.width / (c.clientWidth || c.width);            // picture pixels per screen pixel
  paint(c, visibleFaces(), activeId(), state.reveal, { fontBase: Math.max(11, 13 * s), line: Math.max(1.5, 2 * s) });
}

const fontCss = (px) => `600 ${px}px "Segoe UI", system-ui, Arial, sans-serif`;

/* Where does each name label go? First choice: above the box. If that has no room or would
   cover another label, shrink the text a little, then try inside the box, then below the box.
   Last resort: just the face number inside the box. */
function layoutLabels(g, c, faces, fontBase) {
  const placed = [], spots = new Map();
  const clash = (r) => placed.some((p) => r.x < p.x + p.w && r.x + r.w > p.x && r.y < p.y + p.h && r.y + r.h > p.y);
  const inPicture = (r) => r.x >= -0.5 && r.y >= -0.5 && r.x + r.w <= c.width + 0.5 && r.y + r.h <= c.height + 0.5;
  const fitText = (text, maxW) => {                          // shorten with "..." so it is not wider than maxW
    if (g.measureText(text).width <= maxW) return text;
    let t = text;
    while (t.length > 3 && g.measureText(t + "…").width > maxW) t = t.slice(0, -1);
    return t.length > 3 ? t + "…" : null;
  };
  [...faces].sort((a, b) => b.box.w * b.box.h - a.box.w * a.box.h).forEach((f) => {
    const x = f.box.x * c.width, y = f.box.y * c.height, w = f.box.w * c.width, h = f.box.h * c.height;
    const full = `${f.id}. ${f.name}`;
    let spot = null;
    for (const k of [1, 0.85, 0.72, 0.6]) {
      const px = fontBase * k, padX = px * 0.4, bh = px * 1.45;
      g.font = fontCss(px);
      const tw = g.measureText(full).width + padX * 2;
      const cx = Math.min(Math.max(0, x), Math.max(0, c.width - tw));
      const inside = fitText(full, w - padX * 2);
      const tries = [
        { x: cx, y: y - bh, w: tw, text: full },                                              // above the box
        inside && { x: x, y: y, w: g.measureText(inside).width + padX * 2, text: inside },     // inside, at the top
        { x: cx, y: y + h, w: tw, text: full },                                               // below the box
        inside && { x: x, y: y + h - bh, w: g.measureText(inside).width + padX * 2, text: inside }, // inside, at the bottom
      ];
      for (const t of tries) {
        if (!t) continue;
        const r = { x: t.x, y: t.y, w: t.w, h: bh, text: t.text, px, padX };
        if (inPicture(r) && !clash(r)) { spot = r; break; }
      }
      if (spot) break;
    }
    if (!spot) {                                              // no room anywhere: only the face number
      const px = fontBase * 0.8; g.font = fontCss(px);
      const w2 = g.measureText(String(f.id)).width + px * 0.8;
      spot = { x: x, y: y, w: w2, h: px * 1.45, text: String(f.id), px, padX: px * 0.4 };
    }
    placed.push(spot); spots.set(f.id, spot);
  });
  return spots;
}

/* draws the photo and the face boxes on any canvas (the page, or a hidden one for the PNG download) */
function paint(c, faces, act, rv, opts = {}) {
  const g = c.getContext("2d");
  g.drawImage(state.image, 0, 0, c.width, c.height);
  const fontBase = opts.fontBase || Math.max(15, Math.round(c.width / 55));
  const line = opts.line || Math.max(2, Math.round(c.width / 450));
  const spots = layoutLabels(g, c, faces, fontBase);
  const now = performance.now();
  g.textBaseline = "middle";
  const alphaOf = (f) => rv ? Math.min(1, Math.max(0, ((now - rv.start) - (faces.indexOf(f) / Math.max(1, rv.n)) * rv.dur) / 300)) : 1;
  const colorOf = (f) => (f.known ? "#17803d" : "#b45309");
  const ordered = [...faces.filter((f) => f.id !== act), ...faces.filter((f) => f.id === act)];   // highlighted face last, on top
  ordered.forEach((f) => {                                   // 1st pass: all the boxes
    g.globalAlpha = alphaOf(f);
    const x = f.box.x * c.width, y = f.box.y * c.height, w = f.box.w * c.width, h = f.box.h * c.height;
    const on = f.id === act;
    if (on) { g.fillStyle = colorOf(f) + "33"; g.fillRect(x, y, w, h); }
    g.lineWidth = on ? line * 2.5 : line; g.strokeStyle = colorOf(f); g.strokeRect(x, y, w, h);
  });
  ordered.forEach((f) => {                                   // 2nd pass: all the labels, so no box line crosses a name
    g.globalAlpha = alphaOf(f);
    const s = spots.get(f.id);
    g.fillStyle = colorOf(f); g.fillRect(s.x, s.y, s.w, s.h);
    g.font = fontCss(s.px); g.fillStyle = "#fff"; g.fillText(s.text, s.x + s.padX, s.y + s.h / 2);
  });
  g.globalAlpha = 1;
}

/* ---------- downloads (made in the browser, nothing is sent anywhere) ---------- */
function baseName() {
  const n = state.groupFile ? state.groupFile.name.replace(/\.[^.]*$/, "") : "group";
  return n.replace(/[\\/:*?"<>|]+/g, "_").trim() || "group";
}
function saveBlob(blob, filename) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 10000);
}
el.dlPng.addEventListener("click", () => {
  if (!state.image || !state.faces.length) return;
  const c = document.createElement("canvas");
  c.width = state.image.naturalWidth; c.height = state.image.naturalHeight;
  paint(c, state.faces, null, null);           // all faces, current strictness, no highlight
  c.toBlob((b) => b ? saveBlob(b, baseName() + "_annotated.png") : showError("The picture could not be saved."), "image/png");
});
function csvCell(v) {
  let t = String(v);
  if (/^[=+\-@\t\r]/.test(t)) t = "'" + t;      // stops spreadsheets from treating a name as a formula
  return /[",\r\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
}
el.dlCsv.addEventListener("click", () => {
  if (!state.faces.length) return;
  const t = Number(el.threshold.value).toFixed(2);
  const rows = [["Face number", "Name", "Status", "Distance", "Closest known person", "Strictness used", "Group photo"]];
  state.faces.forEach((f) => rows.push([f.id, f.name, f.known ? "Known" : "Unknown", f.distance.toFixed(3), f.nearest, t, state.groupFile ? state.groupFile.name : ""]));
  const text = "﻿" + rows.map((r) => r.map(csvCell).join(",")).join("\r\n") + "\r\n";   // BOM so Excel shows accents correctly
  saveBlob(new Blob([text], { type: "text/csv;charset=utf-8" }), baseName() + "_results.csv");
});

/* boxes appear one after another; skipped when the computer asks for less motion */
function startReveal() {
  state.reveal = null;
  const n = state.analysis.faces.length;
  if (reduceMotion() || !n) return;
  const dur = Math.min(900, 150 + n * 80);
  state.reveal = { start: performance.now(), n, dur };
  const tick = () => {
    if (!state.reveal) return;
    drawCanvas();
    if (performance.now() - state.reveal.start >= dur + 300) { state.reveal = null; drawCanvas(); return; }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/* the face under the mouse (smallest box wins when boxes overlap) */
function faceAt(ev) {
  const c = el.canvas, r = c.getBoundingClientRect();
  const px = (ev.clientX - r.left) / r.width, py = (ev.clientY - r.top) / r.height;
  let best = null;
  visibleFaces().forEach((f) => {
    const b = f.box;
    if (px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h) {
      if (!best || b.w * b.h < best.box.w * best.box.h) best = f;
    }
  });
  return best;
}

function setHover(id) {
  if (state.hoverId === id) return;
  state.hoverId = id;
  refreshHighlight();
}
function selectFace(id, scrollRow = false) {
  state.selectedId = state.selectedId === id ? null : id;
  refreshHighlight();
  if (scrollRow && state.selectedId !== null) {
    const card = el.rows.querySelector(`li[data-id="${id}"]`);
    if (card) card.scrollIntoView({ block: "nearest", behavior: scrollMode() });     // scrolls the list only
  }
}
function refreshHighlight() {
  el.rows.querySelectorAll("li[data-id]").forEach((li) => {
    const id = Number(li.dataset.id);
    li.classList.toggle("hover", id === state.hoverId);
    li.classList.toggle("selected", id === state.selectedId);
    li.setAttribute("aria-selected", id === state.selectedId ? "true" : "false");
  });
  drawCanvas();
}
function scrollMode() { return reduceMotion() ? "auto" : "smooth"; }
function reduceMotion() { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }

el.canvas.addEventListener("mousemove", (ev) => {
  const f = faceAt(ev);
  el.canvas.style.cursor = f ? "pointer" : "default";
  setHover(f ? f.id : null);
});
el.canvas.addEventListener("mouseleave", () => setHover(null));
el.canvas.addEventListener("click", (ev) => {
  const f = faceAt(ev);
  if (f) selectFace(f.id, true);
});

/* ---------- list of faces (cards) ---------- */
function buildRows() {
  const shown = visibleFaces();
  let index = 0;
  const cards = shown.map((f) => {
    const li = document.createElement("li");
    li.className = "face-card";
    li.dataset.id = f.id;
    if (state.animateRows) { li.classList.add("enter"); li.style.setProperty("--i", Math.min(index++, 12)); }
    li.tabIndex = 0;
    li.title = "Click to select this face";

    const cropWrap = document.createElement("div"); cropWrap.className = "crop-wrap";
    const crop = document.createElement("img");
    crop.className = "thumb face-img"; crop.alt = `Face ${f.id} in the group photo`; crop.src = state.crops[f.id - 1] || "";
    const no = document.createElement("span"); no.className = "face-no"; no.textContent = String(f.id);
    cropWrap.append(crop, no);

    const main = document.createElement("div"); main.className = "face-main";
    const nm = document.createElement("span"); nm.className = "person"; nm.textContent = f.name; main.appendChild(nm);
    if (!f.known) {
      const hint = document.createElement("span");
      hint.className = "hint";
      hint.textContent = `closest: ${f.nearest}`;
      main.appendChild(hint);
    }
    const dist = document.createElement("span"); dist.className = "dist"; dist.textContent = `distance ${f.distance.toFixed(3)}`;
    main.appendChild(dist);

    const side = document.createElement("div"); side.className = "face-side";
    const url = f.known ? photoUrl(f.nearest) : null;
    if (url) {
      const ref = document.createElement("img");
      ref.className = "thumb ref"; ref.alt = `Photo of ${f.nearest} from the folder`; ref.src = url;
      ref.decoding = "async"; ref.addEventListener("error", () => ref.remove());
      side.appendChild(ref);
    }
    const b = document.createElement("span");
    b.className = "badge " + (f.known ? "known" : "unknown");
    b.textContent = f.known ? "Known" : "Unknown";
    side.appendChild(b);

    li.append(cropWrap, main, side);
    li.addEventListener("mouseenter", () => setHover(f.id));
    li.addEventListener("mouseleave", () => setHover(null));
    li.addEventListener("focus", () => setHover(f.id));
    li.addEventListener("blur", () => setHover(null));
    li.addEventListener("click", () => selectFace(f.id));
    li.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); selectFace(f.id); }
    });
    return li;
  });
  if (!cards.length && state.faces.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = state.filter === "known" ? "Nobody was recognised at this strictness. Try moving the slider to the right."
                                              : "No unknown faces at this strictness.";
    cards.push(li);
  }
  el.rows.replaceChildren(...cards);
  state.animateRows = false;                   // only the first build fades in, not slider moves
  refreshHighlight();
}

pollStatus();
