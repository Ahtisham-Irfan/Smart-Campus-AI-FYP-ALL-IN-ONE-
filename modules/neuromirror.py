# ================================================================
# Smart Campus AI v3 — Module 4: NeuroMirror AI
# PRODUCTION-LEVEL Classroom Engagement Monitoring System
#
# Architecture:
#   FaceTracker          — centroid-based persistent face IDs
#   StudentStateBuffer   — per-face rolling history + smoothing
#   SnapshotWorker       — background thread queue, never blocks UI
#   DistractionManager   — transition detection + interval capture
#   NeuroMirrorModule    — main CTk UI with 4 tabs
#
# Key upgrades over v3:
#   • Temporal smoothing: state confirmed over N consecutive frames
#   • Per-face rolling history (deque) with confidence scoring
#   • Transition detection: Active→Distracted / Active→Inactive
#   • Continuous interval capture while distracted/inactive
#   • Async snapshot saving via queue — zero UI blocking
#   • Blur fallback relaxation — never silently skips valid faces
#   • Flickering prevention via hysteresis threshold
# ================================================================
import customtkinter as ctk
from tkinter import messagebox
import threading, os, sys, time, uuid, csv, math, queue
from collections import deque
from datetime import datetime
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Colours ──────────────────────────────────────────────────
C = {
    "bg":    "#0a0c14", "card":  "#12151f", "card2": "#0e1018",
    "border":"#1e2235", "purple":"#7c3aed", "green": "#10b981",
    "amber": "#f59e0b", "red":   "#ef4444", "teal":  "#06b6d4",
    "blue":  "#4f8ef7", "text":  "#f1f5f9", "muted": "#64748b",
    "muted2":"#94a3b8",
}

# ── State definitions ─────────────────────────────────────────
STATES = {
    "active":     {"label":"Active / Attentive", "color":"#10b981","icon":"🟢"},
    "distracted": {"label":"Distracted",          "color":"#f59e0b","icon":"🟡"},
    "inactive":   {"label":"Inactive / Away",     "color":"#ef4444","icon":"🔴"},
    "no_face":    {"label":"No Face Detected",    "color":"#64748b","icon":"⚫"},
}

# ── Tuning constants ──────────────────────────────────────────
SMOOTH_WINDOW      = 8      # frames in rolling history
CONFIRM_FRAMES     = 4      # consecutive frames needed to confirm state change
CENTROID_MAX_DIST  = 90     # px — max centroid shift = same face
FACE_ABSENT_MAX    = 15     # frames before track expires
MIN_FACE_PX        = 55     # minimum face dimension for snapshot
BLUR_THRESHOLD     = 45.0   # Laplacian variance floor (relaxed vs v3's 60)
BLUR_FALLBACK      = 20.0   # absolute fallback — never reject above this
INTERVAL_FIRST     = 0      # seconds after transition before first snap (immediate)
INTERVAL_REPEAT    = 45     # seconds between repeat snaps while still distracted
SNAP_DIR           = os.path.join(os.path.dirname(__file__), "..", "assets", "snapshots")


# ════════════════════════════════════════════════════════════════
# 1.  FACE TRACKER  — centroid matching, persistent IDs
# ════════════════════════════════════════════════════════════════
class FaceTracker:
    """
    Assigns a stable integer ID to each detected face.
    Matches new detections to existing tracks by minimum
    Euclidean centroid distance with a hard distance cap.
    Expired tracks (absent > FACE_ABSENT_MAX frames) are pruned.
    """
    def __init__(self):
        self._next_id = 1
        self._tracks  = {}   # id -> {cx, cy, absent}

    def update(self, boxes):
        """
        boxes : list of (x, y, w, h)
        returns: list of int IDs parallel to boxes
        """
        centroids  = [(x + w//2, y + h//2) for x,y,w,h in boxes]
        track_ids  = list(self._tracks.keys())
        assigned   = {}      # centroid_idx -> face_id
        used       = set()

        for ci, (cx, cy) in enumerate(centroids):
            best_id, best_d = None, float("inf")
            for tid in track_ids:
                if tid in used: continue
                dx = cx - self._tracks[tid]["cx"]
                dy = cy - self._tracks[tid]["cy"]
                d  = math.sqrt(dx*dx + dy*dy)
                if d < best_d and d < CENTROID_MAX_DIST:
                    best_d, best_id = d, tid
            if best_id is not None:
                assigned[ci] = best_id
                used.add(best_id)
            else:
                fid = self._next_id; self._next_id += 1
                assigned[ci] = fid
                used.add(fid)

        # Update positions
        for ci, (cx, cy) in enumerate(centroids):
            fid = assigned[ci]
            self._tracks[fid] = {"cx": cx, "cy": cy, "absent": 0}

        # Age unmatched tracks
        for tid in list(self._tracks.keys()):
            if tid not in used:
                self._tracks[tid]["absent"] += 1
                if self._tracks[tid]["absent"] > FACE_ABSENT_MAX:
                    del self._tracks[tid]

        return [assigned[i] for i in range(len(boxes))]

    def reset(self):
        self._tracks  = {}
        self._next_id = 1


# ════════════════════════════════════════════════════════════════
# 2.  STUDENT STATE BUFFER  — per-face rolling history
# ════════════════════════════════════════════════════════════════
class StudentStateBuffer:
    """
    Maintains a rolling window of raw state observations for one
    face ID.  Exposes:
      • smoothed_state   — majority vote over last SMOOTH_WINDOW frames
      • confidence       — fraction of frames matching smoothed_state
      • stable_state     — state confirmed by CONFIRM_FRAMES consecutive
      • prev_stable      — previous confirmed state (for transition detection)
      • confirm_counter  — how many consecutive frames match candidate
    """
    def __init__(self, face_id: int):
        self.face_id      = face_id
        self._history     = deque(maxlen=SMOOTH_WINDOW)
        self._consecutive = deque(maxlen=CONFIRM_FRAMES)
        self.stable_state = "active"    # last confirmed state
        self.prev_stable  = "active"    # state before last transition
        self._candidate   = "active"    # current candidate for confirmation
        self._streak      = 0           # consecutive frames matching _candidate
        self.confidence   = 0.0

    def push(self, raw_state: str) -> bool:
        """
        Push one raw observation.
        Returns True if a STATE TRANSITION just occurred (prev→stable changed).
        """
        self._history.append(raw_state)

        # Majority vote for smoothed state
        counts = {}
        for s in self._history:
            counts[s] = counts.get(s, 0) + 1
        smoothed  = max(counts, key=counts.get)
        self.confidence = counts[smoothed] / len(self._history)

        # Consecutive-frame confirmation (hysteresis)
        if smoothed == self._candidate:
            self._streak += 1
        else:
            self._candidate = smoothed
            self._streak    = 1

        transition = False
        if self._streak >= CONFIRM_FRAMES and smoothed != self.stable_state:
            self.prev_stable  = self.stable_state
            self.stable_state = smoothed
            self._streak      = 0
            transition        = True

        return transition

    def reset(self):
        self._history.clear()
        self._consecutive.clear()
        self.stable_state = "active"
        self.prev_stable  = "active"
        self._candidate   = "active"
        self._streak      = 0
        self.confidence   = 0.0


# ════════════════════════════════════════════════════════════════
# 3.  SNAPSHOT WORKER  — non-blocking async save queue
# ════════════════════════════════════════════════════════════════
class SnapshotWorker(threading.Thread):
    """
    Daemon thread that drains a queue of (face_crop_bgr, filepath).
    All disk I/O is off the camera thread — zero UI blocking.
    """
    def __init__(self):
        super().__init__(daemon=True, name="SnapshotWorker")
        self._q       = queue.Queue()
        self._running = True
        self.start()

    def enqueue(self, crop_bgr, filepath: str):
        self._q.put((crop_bgr, filepath))

    def run(self):
        while self._running:
            try:
                crop, path = self._q.get(timeout=1.0)
                self._save(crop, path)
                self._q.task_done()
            except queue.Empty:
                continue

    @staticmethod
    def _save(crop, path: str):
        try:
            import cv2
            os.makedirs(os.path.dirname(path), exist_ok=True)
            cv2.imwrite(path, crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
        except Exception as e:
            print(f"[SnapWorker] save error: {e}")

    def stop(self):
        self._running = False


# ════════════════════════════════════════════════════════════════
# 4.  DISTRACTION MANAGER  — transition + interval capture
# ════════════════════════════════════════════════════════════════
class DistractionManager:
    """
    Decides when to request a snapshot for a given face_id.

    Policy
    ──────
    • On TRANSITION into distracted/inactive → immediate capture
    • While REMAINING distracted/inactive    → capture every INTERVAL_REPEAT sec
    • On return to active                    → reset timer (fresh cycle next time)
    • Quality gates (size, blur) with fallback relaxation
    • All saves delegated to SnapshotWorker (non-blocking)
    """
    def __init__(self, session_id: str, worker: SnapshotWorker):
        self.session_id   = session_id
        self.worker       = worker
        self.session_dir  = os.path.join(SNAP_DIR, session_id)
        os.makedirs(self.session_dir, exist_ok=True)
        self._timers      = {}   # face_id -> float (epoch of last capture)
        self._states      = {}   # face_id -> last known stable state
        self.snapshots    = []   # [{face_id, ts, path, reason, blur, size}]
        self._lock        = threading.Lock()

    # ── Called once per frame per face ───────────────────────
    def process(self, face_id: int, buf: StudentStateBuffer,
                frame, x: int, y: int, w: int, h: int) -> bool:
        """
        Returns True if a snapshot was enqueued this call.
        """
        state      = buf.stable_state
        transition = buf.prev_stable != state   # True on the frame of transition
        prev       = self._states.get(face_id, "active")

        is_bad  = state in ("distracted", "inactive")
        was_bad = prev  in ("distracted", "inactive")

        if not is_bad:
            # Student is active → reset timer so next bad period starts fresh
            with self._lock:
                self._timers.pop(face_id, None)
                self._states[face_id] = state
            return False

        now      = time.time()
        last_cap = self._timers.get(face_id, None)

        # Determine if we should capture
        should_capture = False
        reason         = ""

        if last_cap is None:
            # First bad frame — immediate capture (transition trigger)
            should_capture = True
            reason         = f"transition {buf.prev_stable}→{state}"
        elif (now - last_cap) >= INTERVAL_REPEAT:
            # Continuing bad state — interval repeat
            should_capture = True
            reason         = f"interval ({state})"

        with self._lock:
            self._states[face_id] = state

        if not should_capture:
            return False

        # ── Quality gate ─────────────────────────────────────
        ok, crop = self._quality_crop(frame, x, y, w, h)
        if not ok:
            # Relax blur threshold once — if still no good, skip silently
            ok, crop = self._quality_crop(frame, x, y, w, h,
                                          blur_override=BLUR_FALLBACK)
        if not ok or crop is None:
            return False

        # ── Build path & enqueue ──────────────────────────────
        ts    = datetime.now().strftime("%H%M%S_%f")[:12]
        fname = f"face{face_id}_{ts}.jpg"
        fpath = os.path.join(self.session_dir, fname)
        self.worker.enqueue(crop, fpath)

        with self._lock:
            self._timers[face_id] = now
            self.snapshots.append({
                "face_id":   face_id,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "state":     state,
                "reason":    reason,
                "path":      fpath,
                "size":      f"{w}×{h}",
                "blur":      round(self._last_blur, 1),
            })

        return True

    # ── Internal helpers ──────────────────────────────────────
    _last_blur = 0.0

    def _quality_crop(self, frame, x, y, w, h,
                      blur_override=None):
        try:
            import cv2, numpy as np
            if w < MIN_FACE_PX or h < MIN_FACE_PX:
                return False, None
            pad  = 8
            ih, iw = frame.shape[:2]
            x1   = max(0, x - pad);  y1 = max(0, y - pad)
            x2   = min(iw, x+w+pad); y2 = min(ih, y+h+pad)
            crop = frame[y1:y2, x1:x2].copy()
            if crop.size == 0:
                return False, None
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            bv   = cv2.Laplacian(gray, cv2.CV_64F).var()
            self._last_blur = bv
            threshold = blur_override if blur_override else BLUR_THRESHOLD
            if bv < threshold:
                return False, None
            return True, crop
        except Exception:
            return False, None

    def reset(self, session_id: str):
        self.session_id  = session_id
        self.session_dir = os.path.join(SNAP_DIR, session_id)
        os.makedirs(self.session_dir, exist_ok=True)
        with self._lock:
            self._timers   = {}
            self._states   = {}
            self.snapshots = []


# ════════════════════════════════════════════════════════════════
# 5.  NEUROMIRROR MODULE  — main UI (4 tabs)
# ════════════════════════════════════════════════════════════════
class NeuroMirrorModule(ctk.CTkFrame):
    def __init__(self, parent, user):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.user         = user
        self.cap          = None
        self.running      = False
        self.session_id   = ""

        # Session accumulators
        self.state_counts     = {s: 0 for s in STATES}
        self.frame_total      = 0
        self.attention_scores = []
        self.events           = []

        # Per-face state buffers  face_id -> StudentStateBuffer
        self._bufs = {}

        # Core subsystems
        self._tracker = FaceTracker()
        self._worker  = SnapshotWorker()
        self._snap_mgr= DistractionManager("init", self._worker)

        os.makedirs(SNAP_DIR, exist_ok=True)
        self._build_ui()

    # ─── UI BUILD ────────────────────────────────────────────
    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(sticky="ew", padx=24, pady=(16, 8))
        ctk.CTkLabel(hdr, text="🧠  NeuroMirror AI — Classroom Engagement",
                     font=ctk.CTkFont("Segoe UI", 20, "bold"),
                     text_color=C["purple"]).pack(side="left")
        self.snap_badge = ctk.CTkLabel(hdr, text="📸 Snapshots: 0",
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=C["amber"])
        self.snap_badge.pack(side="right", padx=(0, 8))
        self.engine_lbl = ctk.CTkLabel(hdr, text="",
                                        font=ctk.CTkFont("Segoe UI", 10),
                                        text_color=C["muted2"])
        self.engine_lbl.pack(side="right", padx=(0, 16))

        # Tabs
        self.tabs = ctk.CTkTabview(self, fg_color=C["card"],
                                   segmented_button_selected_color=C["purple"],
                                   segmented_button_fg_color=C["card2"])
        self.tabs.grid(sticky="nsew", padx=24, pady=(0, 16))
        for t in ["Live Monitoring", "Engagement Analytics",
                  "Distraction Snapshots", "Session Report"]:
            self.tabs.add(t)

        self._build_live(self.tabs.tab("Live Monitoring"))
        self._build_analytics(self.tabs.tab("Engagement Analytics"))
        self._build_snapshots(self.tabs.tab("Distraction Snapshots"))
        self._build_report(self.tabs.tab("Session Report"))

    # ──────────────────────────────────────────────────────────
    # TAB 1: LIVE MONITORING
    # ──────────────────────────────────────────────────────────
    def _build_live(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)

        # ── Camera panel
        left = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=10,
                            border_width=1, border_color=C["border"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(left, fg_color="transparent")
        ctrl.grid(sticky="ew", padx=14, pady=12)
        ctk.CTkLabel(ctrl, text="Class:",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=C["muted2"]).pack(side="left", padx=(0, 6))
        self.class_var = ctk.StringVar(value="Computer Science")
        ctk.CTkEntry(ctrl, textvariable=self.class_var,
                     width=155, height=34,
                     font=ctk.CTkFont("Segoe UI", 12),
                     fg_color=C["card"], corner_radius=8,
                     border_color=C["border"]).pack(side="left", padx=(0, 10))
        self.s_btn = ctk.CTkButton(ctrl, text="▶  Start",
                                   width=100, height=34, corner_radius=8,
                                   font=ctk.CTkFont("Segoe UI", 12, "bold"),
                                   fg_color=C["purple"], command=self._start)
        self.s_btn.pack(side="left", padx=(0, 6))
        self.x_btn = ctk.CTkButton(ctrl, text="■  Stop",
                                   width=80, height=34, corner_radius=8,
                                   font=ctk.CTkFont("Segoe UI", 12, "bold"),
                                   fg_color=C["red"], state="disabled",
                                   command=self._stop)
        self.x_btn.pack(side="left")

        self.cam_lbl = ctk.CTkLabel(
            left,
            text="📷  Classroom Camera\n\n"
                 "NeuroMirror AI — Production-Grade Engagement Monitor\n\n"
                 "🟢 Active  — eyes open, forward gaze (confirmed 4 frames)\n"
                 "🟡 Distracted — looking away / eye inconsistency\n"
                 "🔴 Inactive — absent / eyes closed\n\n"
                 "📸 Snapshots: transition-triggered + interval repeats\n"
                 "⚡ Async saving — zero camera lag",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=C["muted2"], justify="center")
        self.cam_lbl.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 8))

        self.stat_lbl = ctk.CTkLabel(left, text="Monitoring inactive",
                                     font=ctk.CTkFont("Segoe UI", 11),
                                     text_color=C["teal"])
        self.stat_lbl.grid(sticky="w", padx=14, pady=(0, 10))

        # ── Right: attention dashboard
        right = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=10,
                             border_width=1, border_color=C["border"])
        right.grid(row=0, column=1, sticky="nsew", pady=8)

        ctk.CTkLabel(right, text="Live Attention Dashboard",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=C["text"]).pack(padx=14, pady=(14, 8), anchor="w")

        self.attn_num = ctk.CTkLabel(right, text="—",
                                     font=ctk.CTkFont("Segoe UI", 42, "bold"),
                                     text_color=C["purple"])
        self.attn_num.pack()
        ctk.CTkLabel(right, text="Attention Score",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["muted2"]).pack(pady=(0, 6))
        self.attn_bar = ctk.CTkProgressBar(right, height=14, corner_radius=7,
                                           progress_color=C["purple"],
                                           fg_color=C["card"])
        self.attn_bar.pack(fill="x", padx=16, pady=(0, 10))
        self.attn_bar.set(0)

        # State cards
        self.state_vals = {}
        for st, info in STATES.items():
            if st == "no_face": continue
            row = ctk.CTkFrame(right, fg_color=C["card"], corner_radius=8)
            row.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(row, text=info["icon"],
                         font=ctk.CTkFont("Segoe UI Emoji", 18)
                         ).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=info["label"],
                         font=ctk.CTkFont("Segoe UI", 12),
                         text_color=info["color"]).pack(side="left")
            v = ctk.CTkLabel(row, text="0",
                             font=ctk.CTkFont("Segoe UI", 18, "bold"),
                             text_color=info["color"])
            v.pack(side="right", padx=10)
            self.state_vals[st] = v

        ctk.CTkFrame(right, height=1, fg_color=C["border"]).pack(
            fill="x", padx=14, pady=8)

        # Students in frame
        fc_row = ctk.CTkFrame(right, fg_color=C["card"], corner_radius=8)
        fc_row.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(fc_row, text="👥 In frame:",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=C["muted2"]).pack(side="left", padx=10, pady=8)
        self.faces_lbl = ctk.CTkLabel(fc_row, text="0",
                                      font=ctk.CTkFont("Segoe UI", 18, "bold"),
                                      text_color=C["teal"])
        self.faces_lbl.pack(side="right", padx=10)

        # Snapshots live
        sn_row = ctk.CTkFrame(right, fg_color=C["card"], corner_radius=8)
        sn_row.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(sn_row, text="📸 Snaps captured:",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=C["muted2"]).pack(side="left", padx=10, pady=8)
        self.snap_cnt = ctk.CTkLabel(sn_row, text="0",
                                     font=ctk.CTkFont("Segoe UI", 18, "bold"),
                                     text_color=C["amber"])
        self.snap_cnt.pack(side="right", padx=10)

        # Confidence strip
        conf_row = ctk.CTkFrame(right, fg_color=C["card"], corner_radius=8)
        conf_row.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(conf_row, text="🎯 Detection confidence:",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=C["muted2"]).pack(side="left", padx=10, pady=8)
        self.conf_lbl = ctk.CTkLabel(conf_row, text="—",
                                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                                     text_color=C["green"])
        self.conf_lbl.pack(side="right", padx=10)

        # Event log
        ctk.CTkLabel(right, text="Event Log",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=C["muted2"]).pack(padx=14, anchor="w", pady=(8, 2))
        self.event_scroll = ctk.CTkScrollableFrame(right, fg_color="transparent",
                                                    height=95)
        self.event_scroll.pack(fill="x", padx=14, pady=(0, 14))

    # ──────────────────────────────────────────────────────────
    # TAB 2: ENGAGEMENT ANALYTICS
    # ──────────────────────────────────────────────────────────
    def _build_analytics(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=8,
                            border_width=1, border_color=C["border"])
        ctrl.grid(sticky="ew", pady=8)
        cr = ctk.CTkFrame(ctrl, fg_color="transparent")
        cr.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(cr, text="🔄  Refresh",
                      width=110, height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color=C["purple"],
                      command=self._refresh_analytics).pack(side="left", padx=(0, 8))
        ctk.CTkButton(cr, text="📥  Export CSV",
                      width=120, height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color=C["card"], border_width=1,
                      border_color=C["border"],
                      command=self._export_csv).pack(side="left")

        self.anal_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.anal_scroll.grid(sticky="nsew", pady=(0, 8))
        self._refresh_analytics()

    # ──────────────────────────────────────────────────────────
    # TAB 3: DISTRACTION SNAPSHOTS
    # ──────────────────────────────────────────────────────────
    def _build_snapshots(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=8,
                            border_width=1, border_color=C["border"])
        ctrl.grid(sticky="ew", pady=8)
        cr = ctk.CTkFrame(ctrl, fg_color="transparent")
        cr.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(cr,
                     text="📸  Distraction Snapshots  |  "
                          "Transition-triggered + 45s repeat  |  "
                          "Async save  |  Blur-filtered",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["muted2"]).pack(side="left")
        ctk.CTkButton(cr, text="🔄",
                      width=36, height=28, corner_radius=6,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color=C["purple"],
                      command=self._refresh_snapshots).pack(side="right", padx=(0, 4))
        ctk.CTkButton(cr, text="📂 Folder",
                      width=80, height=28, corner_radius=6,
                      font=ctk.CTkFont("Segoe UI", 10),
                      fg_color=C["card"], border_width=1,
                      border_color=C["border"],
                      command=self._open_folder).pack(side="right", padx=(0, 4))
        ctk.CTkButton(cr, text="🗑",
                      width=36, height=28, corner_radius=6,
                      font=ctk.CTkFont("Segoe UI", 10),
                      fg_color=C["red"],
                      command=self._clear_snapshots).pack(side="right")

        self.snap_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.snap_scroll.grid(sticky="nsew", pady=(0, 8))
        self._refresh_snapshots()

    # ──────────────────────────────────────────────────────────
    # TAB 4: SESSION REPORT
    # ──────────────────────────────────────────────────────────
    def _build_report(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=8,
                            border_width=1, border_color=C["border"])
        ctrl.grid(sticky="ew", pady=8)
        cr = ctk.CTkFrame(ctrl, fg_color="transparent")
        cr.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(cr, text="📥  Export TXT",
                      width=110, height=28, corner_radius=6,
                      font=ctk.CTkFont("Segoe UI", 10),
                      fg_color=C["card"], border_width=1,
                      border_color=C["border"],
                      command=self._export_txt).pack(side="right")

        self.report_box = ctk.CTkTextbox(tab,
                                          font=ctk.CTkFont("Consolas", 12),
                                          fg_color=C["card2"],
                                          border_width=1,
                                          border_color=C["border"],
                                          wrap="word")
        self.report_box.grid(sticky="nsew", pady=(0, 8))
        self.report_box.insert("end",
            "NeuroMirror AI — Session Report\n"
            "════════════════════════════════\n\n"
            "Start a monitoring session to generate a report.")
        self.report_box.configure(state="disabled")

    # ─── SESSION CONTROL ─────────────────────────────────────
    def _start(self):
        self.session_id       = str(uuid.uuid4())[:8]
        self.state_counts     = {s: 0 for s in STATES}
        self.frame_total      = 0
        self.attention_scores = []
        self.events           = []
        self._bufs            = {}
        self._tracker.reset()
        self._snap_mgr.reset(self.session_id)
        self.running = True
        self.s_btn.configure(state="disabled")
        self.x_btn.configure(state="normal")
        self.engine_lbl.configure(text=f"Session: {self.session_id}")
        threading.Thread(target=self._monitor_loop,
                         daemon=True, name="NMCamLoop").start()

    def _stop(self):
        self.running = False
        self.s_btn.configure(state="normal")
        self.x_btn.configure(state="disabled")
        snaps = len(self._snap_mgr.snapshots)
        self.stat_lbl.configure(
            text=f"Session {self.session_id} ended — "
                 f"{self.frame_total} frames  |  {snaps} snapshots")
        self.after(400, self._generate_report)
        self.after(400, self._refresh_analytics)
        self.after(400, self._refresh_snapshots)

    # ─── MONITOR LOOP ────────────────────────────────────────
    def _monitor_loop(self):
        try:
            import cv2
        except ImportError:
            self.after(0, lambda: self.stat_lbl.configure(
                text="⚠ OpenCV not installed"))
            return

        fc = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        ec = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml")

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.after(0, lambda: self.stat_lbl.configure(
                text="⚠ Camera not found!"))
            self.running = False
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

        prev_fc    = 0
        low_streak = 0

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.1, 5, minSize=(70, 70))
            boxes = list(faces)
            ids   = self._tracker.update(boxes)

            active_cnt = 0
            dist_cnt   = 0
            inact_cnt  = 0
            conf_sum   = 0.0
            snap_taken = 0

            for fi, (x, y, w, h) in enumerate(boxes):
                fid       = ids[fi]
                face_gray = gray[y:y+h, x:x+w]
                face_col  = frame[y:y+h, x:x+w]

                # ── Eye detection
                eyes      = ec.detectMultiScale(
                    face_gray, 1.1, 5, minSize=(18, 18))
                has_eyes  = len(eyes) >= 2
                eyes_open = False
                if has_eyes:
                    ex, ey, ew, eh = eyes[0]
                    eye_mean  = float(face_gray[ey:ey+eh, ex:ex+ew].mean())
                    eyes_open = eye_mean > 55

                # ── Head direction (centroid offset heuristic)
                face_cx    = x + w // 2
                frame_cx   = frame.shape[1] // 2
                looking_fwd= abs(face_cx - frame_cx) < (frame.shape[1] * 0.26)

                # ── Raw state
                if has_eyes and eyes_open and looking_fwd:
                    raw = "active"
                elif has_eyes and not looking_fwd:
                    raw = "distracted"
                else:
                    raw = "inactive"

                # ── Push to per-face buffer
                if fid not in self._bufs:
                    self._bufs[fid] = StudentStateBuffer(fid)
                self._bufs[fid].push(raw)

                stable = self._bufs[fid].stable_state
                conf   = self._bufs[fid].confidence
                conf_sum += conf

                self.state_counts[stable] = \
                    self.state_counts.get(stable, 0) + 1

                if stable == "active":     active_cnt += 1
                elif stable == "distracted": dist_cnt  += 1
                else:                        inact_cnt += 1

                # ── Snapshot manager
                taken = self._snap_mgr.process(
                    fid, self._bufs[fid], frame, x, y, w, h)
                if taken:
                    snap_taken += 1
                    ts  = datetime.now().strftime("%H:%M:%S")
                    ev  = (f"📸 Face #{fid} [{stable}] — "
                           f"snapshot saved")
                    self.events.append((ts, ev))
                    self.after(0, lambda t=ts, e=ev: self._add_event(t, e))

                # ── Draw overlay
                col_map = {
                    "active":    (0, 220, 120),
                    "distracted":(0, 180, 255),
                    "inactive":  (80, 80, 230),
                }
                col = col_map.get(stable, (180, 180, 180))
                cv2.rectangle(frame, (x, y), (x+w, y+h), col, 2)
                lbl = f"#{fid} {stable}  {round(conf*100)}%"
                cv2.putText(frame, lbl, (x, y-8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, col, 2)
                for (ex, ey, ew, eh) in eyes[:2]:
                    cv2.rectangle(face_col, (ex, ey),
                                  (ex+ew, ey+eh), (255, 240, 0), 1)

            if not boxes:
                self.state_counts["no_face"] = \
                    self.state_counts.get("no_face", 0) + 1

            # Attention score
            fc_total = len(boxes)
            if fc_total > 0:
                attn = round(
                    (active_cnt * 100 + dist_cnt * 40) / fc_total)
                avg_conf = round(conf_sum / fc_total * 100)
            else:
                attn, avg_conf = 0, 0

            self.frame_total += 1
            self.attention_scores.append(attn)

            # Events
            if fc_total == 0 and prev_fc > 0:
                ts = datetime.now().strftime("%H:%M:%S")
                ev = "⚫ All students left frame"
                self.events.append((ts, ev))
                self.after(0, lambda t=ts, e=ev: self._add_event(t, e))
            if fc_total > 0 and prev_fc == 0:
                ts = datetime.now().strftime("%H:%M:%S")
                ev = f"🟢 {fc_total} student(s) entered frame"
                self.events.append((ts, ev))
                self.after(0, lambda t=ts, e=ev: self._add_event(t, e))
            if attn < 30 and self.frame_total > 20:
                low_streak += 1
                if low_streak == 30:
                    ts = datetime.now().strftime("%H:%M:%S")
                    ev = "⚠️ Sustained low attention"
                    self.events.append((ts, ev))
                    self.after(0, lambda t=ts, e=ev: self._add_event(t, e))
            else:
                low_streak = 0
            prev_fc = fc_total

            # HUD overlay
            snap_n = len(self._snap_mgr.snapshots)
            hud = (f"ID:{self.session_id}  "
                   f"Faces:{fc_total}  "
                   f"Active:{active_cnt}  "
                   f"Dist:{dist_cnt}  "
                   f"Attn:{attn}%  "
                   f"Conf:{avg_conf}%  "
                   f"Snaps:{snap_n}")
            cv2.putText(frame, hud, (6, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 230, 200), 1)

            # Push to GUI
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img.thumbnail((500, 380))
            ci  = ctk.CTkImage(img, size=img.size)
            self.after(0,
                lambda i=ci, a=attn, fc2=fc_total,
                       ac=active_cnt, dc=dist_cnt,
                       ic=inact_cnt, cn=avg_conf,
                       sn=snap_n, m=hud:
                self._update_live(i, a, fc2, ac, dc, ic, cn, sn, m))
            self.cam_lbl.image_ref = ci
            time.sleep(0.033)   # ~30 fps cap

        self.cap.release()

    # ─── LIVE UI UPDATE ──────────────────────────────────────
    def _update_live(self, img, attn, fc, ac, dc, ic, cn, sn, msg):
        self.cam_lbl.configure(image=img, text="")
        self.stat_lbl.configure(text=msg)
        self.faces_lbl.configure(text=str(fc))
        self.snap_cnt.configure(text=str(sn))
        self.snap_badge.configure(text=f"📸 Snapshots: {sn}")

        col = (C["green"] if attn >= 65 else
               C["amber"] if attn >= 35 else C["red"])
        self.attn_num.configure(text=f"{attn}%", text_color=col)
        self.attn_bar.configure(progress_color=col)
        self.attn_bar.set(attn / 100)

        c_col = C["green"] if cn >= 70 else C["amber"] if cn >= 45 else C["red"]
        self.conf_lbl.configure(text=f"{cn}%", text_color=c_col)

        for state, val in [("active", ac), ("distracted", dc), ("inactive", ic)]:
            self.state_vals[state].configure(text=str(val))

    def _add_event(self, ts: str, ev: str):
        row = ctk.CTkLabel(self.event_scroll,
                           text=f"{ts}  {ev}",
                           font=ctk.CTkFont("Segoe UI", 10),
                           text_color=C["amber"])
        row.pack(anchor="w")
        kids = self.event_scroll.winfo_children()
        if len(kids) > 60:
            kids[0].destroy()

    # ─── ANALYTICS ───────────────────────────────────────────
    def _refresh_analytics(self):
        for w in self.anal_scroll.winfo_children():
            w.destroy()
        total = self.frame_total
        if total == 0:
            ctk.CTkLabel(self.anal_scroll,
                         text="🧠  No data yet.\n\nStart a session first.",
                         font=ctk.CTkFont("Segoe UI", 14),
                         text_color=C["muted2"],
                         justify="center").pack(pady=60)
            return

        avg_attn = round(sum(self.attention_scores) /
                         len(self.attention_scores)) \
                   if self.attention_scores else 0
        active  = self.state_counts.get("active", 0)
        dist    = self.state_counts.get("distracted", 0)
        inact   = self.state_counts.get("inactive", 0)
        no_face = self.state_counts.get("no_face", 0)
        snaps   = len(self._snap_mgr.snapshots)

        # KPIs
        kf = ctk.CTkFrame(self.anal_scroll, fg_color="transparent")
        kf.pack(fill="x", pady=(0, 14))
        for i in range(5):
            kf.grid_columnconfigure(i, weight=1)
        attn_col = (C["green"] if avg_attn >= 65 else
                    C["amber"] if avg_attn >= 35 else C["red"])
        for i, (lbl, val, col) in enumerate([
            ("Total Frames",  str(total),     C["teal"]),
            ("Avg Attention", f"{avg_attn}%", attn_col),
            ("Active",        str(active),    C["green"]),
            ("Distracted",    str(dist),      C["amber"]),
            ("Snapshots",     str(snaps),     C["purple"]),
        ]):
            card = ctk.CTkFrame(kf, fg_color=C["card2"],
                                corner_radius=10, border_width=1,
                                border_color=C["border"])
            card.grid(row=0, column=i, padx=5, sticky="ew")
            ctk.CTkLabel(card, text=val,
                         font=ctk.CTkFont("Segoe UI", 20, "bold"),
                         text_color=col).grid(pady=(12, 2))
            ctk.CTkLabel(card, text=lbl,
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=C["muted2"]).grid(pady=(0, 12))

        # State distribution bars
        self._sec("Attention State Distribution")
        dc_card = ctk.CTkFrame(self.anal_scroll, fg_color=C["card2"],
                               corner_radius=10, border_width=1,
                               border_color=C["border"])
        dc_card.pack(fill="x", pady=(0, 14))
        inn = ctk.CTkFrame(dc_card, fg_color="transparent")
        inn.pack(fill="x", padx=20, pady=16)
        total_s = max(active + dist + inact + no_face, 1)
        for st, cnt, col, lbl in [
            ("active",    active,  C["green"],  "🟢 Active / Attentive"),
            ("distracted",dist,    C["amber"],  "🟡 Distracted"),
            ("inactive",  inact,   C["red"],    "🔴 Inactive / Away"),
            ("no_face",   no_face, C["muted2"], "⚫ No Face Detected"),
        ]:
            pct = round(cnt / total_s * 100)
            r   = ctk.CTkFrame(inn, fg_color="transparent")
            r.pack(fill="x", pady=4)
            ctk.CTkLabel(r, text=lbl, width=170, anchor="w",
                         font=ctk.CTkFont("Segoe UI", 12),
                         text_color=col).pack(side="left")
            bar = ctk.CTkProgressBar(r, height=16, corner_radius=8,
                                     progress_color=col, fg_color=C["card"])
            bar.pack(side="left", fill="x", expand=True, padx=(8, 8))
            bar.set(cnt / total_s)
            ctk.CTkLabel(r, text=f"{pct}% ({cnt})", width=90,
                         font=ctk.CTkFont("Segoe UI", 11),
                         text_color=C["muted2"]).pack(side="left")

        # Attention timeline
        if len(self.attention_scores) > 10:
            self._sec("Attention Score Timeline")
            tc = ctk.CTkFrame(self.anal_scroll, fg_color=C["card2"],
                              corner_radius=10, border_width=1,
                              border_color=C["border"])
            tc.pack(fill="x", pady=(0, 14))
            ti = ctk.CTkFrame(tc, fg_color="transparent")
            ti.pack(fill="x", padx=20, pady=12)
            sc  = self.attention_scores
            stp = max(1, len(sc) // 30)
            for i, v in enumerate(sc[::stp][-30:]):
                col = (C["green"] if v >= 65 else
                       C["amber"] if v >= 35 else C["red"])
                r   = ctk.CTkFrame(ti, fg_color="transparent")
                r.pack(fill="x", pady=1)
                ctk.CTkLabel(r, text=f"T{i+1:02d}", width=30,
                             font=ctk.CTkFont("Consolas", 10),
                             text_color=C["muted"]).pack(side="left", padx=(0, 6))
                b = ctk.CTkProgressBar(r, height=10, corner_radius=5,
                                       progress_color=col, fg_color=C["card"])
                b.pack(side="left", fill="x", expand=True, padx=(0, 6))
                b.set(v / 100)
                ctk.CTkLabel(r, text=f"{v}%", width=38,
                             font=ctk.CTkFont("Segoe UI", 10),
                             text_color=col).pack(side="left")

        # Snapshot log in analytics
        if self._snap_mgr.snapshots:
            self._sec(f"Distraction Snapshot Log ({snaps})")
            sl = ctk.CTkFrame(self.anal_scroll, fg_color=C["card2"],
                              corner_radius=10, border_width=1,
                              border_color=C["border"])
            sl.pack(fill="x", pady=(0, 14))
            for s in self._snap_mgr.snapshots:
                r = ctk.CTkFrame(sl, fg_color="transparent")
                r.pack(fill="x", padx=16, pady=3)
                ctk.CTkLabel(r,
                             text=f"📸  Face #{s['face_id']}  "
                                  f"@ {s['timestamp']}  "
                                  f"[{s['state']}]  "
                                  f"Reason: {s['reason']}  "
                                  f"Size: {s['size']}  "
                                  f"Blur: {s['blur']}",
                             font=ctk.CTkFont("Segoe UI", 11),
                             text_color=C["amber"]).pack(anchor="w")

        # Events
        if self.events:
            self._sec("Key Events")
            ev_card = ctk.CTkFrame(self.anal_scroll, fg_color=C["card2"],
                                   corner_radius=10, border_width=1,
                                   border_color=C["border"])
            ev_card.pack(fill="x", pady=(0, 14))
            for ts, ev in self.events[-25:]:
                ctk.CTkLabel(ev_card, text=f"  {ts}   {ev}",
                             font=ctk.CTkFont("Segoe UI", 11),
                             text_color=C["amber"],
                             anchor="w").pack(padx=12, pady=3, anchor="w")

        # Recommendations
        self._sec("AI Instructor Recommendations")
        rc = ctk.CTkFrame(self.anal_scroll, fg_color=C["card2"],
                          corner_radius=10, border_width=1,
                          border_color=C["border"])
        rc.pack(fill="x", pady=(0, 14))
        for rec in self._recommendations(avg_attn, active, dist,
                                          inact, total_s, snaps):
            ctk.CTkLabel(rc, text=rec,
                         font=ctk.CTkFont("Segoe UI", 12),
                         text_color=C["text"], anchor="w",
                         wraplength=700, justify="left").pack(
                padx=20, pady=6, anchor="w")

    def _sec(self, title: str):
        ctk.CTkLabel(self.anal_scroll, text=title,
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(8, 6))

    # ─── SNAPSHOT GALLERY ────────────────────────────────────
    def _refresh_snapshots(self):
        for w in self.snap_scroll.winfo_children():
            w.destroy()
        all_files = []
        if os.path.exists(SNAP_DIR):
            for sess in sorted(os.listdir(SNAP_DIR), reverse=True):
                sp = os.path.join(SNAP_DIR, sess)
                if os.path.isdir(sp):
                    for f in sorted(os.listdir(sp)):
                        if f.lower().endswith(".jpg"):
                            all_files.append((sess, f, os.path.join(sp, f)))

        if not all_files:
            ctk.CTkLabel(self.snap_scroll,
                         text="📸  No snapshots yet.\n\n"
                              "Snapshots are captured when a student transitions\n"
                              "to Distracted or Inactive state.\n\n"
                              "Continuous captures every 45 seconds while state persists.\n"
                              "Async saving — zero FPS impact.",
                         font=ctk.CTkFont("Segoe UI", 13),
                         text_color=C["muted2"],
                         justify="center").pack(pady=40)
            return

        ctk.CTkLabel(self.snap_scroll,
                     text=f"  📸  {len(all_files)} snapshot(s)  —  "
                          f"{SNAP_DIR}",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["muted2"]).pack(anchor="w", pady=(0, 8))

        gf = ctk.CTkFrame(self.snap_scroll, fg_color="transparent")
        gf.pack(fill="x")
        cols = 4
        for i in range(cols):
            gf.grid_columnconfigure(i, weight=1)

        for idx, (sess, fname, fpath) in enumerate(all_files):
            r, c = divmod(idx, cols)
            card = ctk.CTkFrame(gf, fg_color=C["card"],
                                corner_radius=10, border_width=1,
                                border_color=C["border"])
            card.grid(row=r, column=c, padx=6, pady=6, sticky="ew")
            try:
                pil = Image.open(fpath)
                pil.thumbnail((120, 120))
                cti = ctk.CTkImage(pil, size=pil.size)
                il  = ctk.CTkLabel(card, image=cti, text="")
                il.pack(padx=8, pady=(10, 4))
                il.image_ref = cti
            except Exception:
                ctk.CTkLabel(card, text="🖼",
                             font=ctk.CTkFont("Segoe UI Emoji", 30)
                             ).pack(padx=8, pady=(10, 4))
            ctk.CTkLabel(card, text=fname[:18],
                         font=ctk.CTkFont("Consolas", 9),
                         text_color=C["amber"],
                         wraplength=130).pack(padx=6, pady=(0, 2))
            ctk.CTkLabel(card, text=f"Sess: {sess}",
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=C["muted"]).pack(padx=6, pady=(0, 8))

    def _open_folder(self):
        import subprocess, platform
        os.makedirs(SNAP_DIR, exist_ok=True)
        p = os.path.abspath(SNAP_DIR)
        if platform.system() == "Windows":
            subprocess.Popen(f'explorer "{p}"')
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])

    def _clear_snapshots(self):
        if messagebox.askyesno("Clear", "Delete all distraction snapshots?"):
            import shutil
            if os.path.exists(SNAP_DIR):
                shutil.rmtree(SNAP_DIR)
            os.makedirs(SNAP_DIR, exist_ok=True)
            self._snap_mgr.snapshots = []
            self._refresh_snapshots()
            self.snap_badge.configure(text="📸 Snapshots: 0")

    # ─── RECOMMENDATIONS ─────────────────────────────────────
    def _recommendations(self, avg, act, dis, ina, tot, snaps):
        recs = []
        pa = act / tot * 100 if tot else 0
        pd = dis / tot * 100 if tot else 0
        pi = ina / tot * 100 if tot else 0
        if avg >= 70:
            recs.append("✅  Excellent engagement — class is highly attentive.")
        elif avg >= 50:
            recs.append("⚠️  Moderate engagement. Add interactive activities or Q&A.")
        else:
            recs.append("❌  Low attention. Take a break, use visuals, or pose questions.")
        if pd > 30:
            recs.append("💡  High distraction. Try calling on students or group work.")
        if pi > 25:
            recs.append("💡  High inactivity. Consider a stand-up or physical activity.")
        if pa > 70:
            recs.append("🌟  Strong active participation — maintain this approach!")
        if snaps > 5:
            recs.append(f"📸  {snaps} distraction events — review snapshots for patterns.")
        if not recs:
            recs.append("📊  Keep monitoring to gather more recommendations.")
        return recs

    # ─── REPORT ──────────────────────────────────────────────
    def _generate_report(self):
        total = self.frame_total
        if total == 0:
            return
        avg   = round(sum(self.attention_scores) /
                      len(self.attention_scores)) if self.attention_scores else 0
        act   = self.state_counts.get("active", 0)
        dis   = self.state_counts.get("distracted", 0)
        ina   = self.state_counts.get("inactive", 0)
        nf    = self.state_counts.get("no_face", 0)
        snaps = self._snap_mgr.snapshots
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M")

        L = ["=" * 64,
             "   NEUROMIRROR AI — CLASSROOM ENGAGEMENT REPORT",
             "=" * 64,
             f"  Session ID      : {self.session_id}",
             f"  Class           : {self.class_var.get()}",
             f"  Generated       : {ts}",
             f"  Total Frames    : {total}",
             f"  Algorithm       : Temporal smoothing + centroid tracking",
             f"  Confirm window  : {CONFIRM_FRAMES} frames  |  "
             f"Smooth window: {SMOOTH_WINDOW} frames",
             "",
             "  ATTENTION SUMMARY",
             "-" * 64,
             f"  Average Attention  : {avg}%",
             f"  Assessment         : "
             f"{'Excellent' if avg>=70 else 'Moderate' if avg>=50 else 'Needs Improvement'}",
             "",
             "  STATE BREAKDOWN",
             "-" * 64,
             f"  🟢 Active       : {act:>6} frames  ({round(act/total*100)}%)",
             f"  🟡 Distracted   : {dis:>6} frames  ({round(dis/total*100)}%)",
             f"  🔴 Inactive     : {ina:>6} frames  ({round(ina/total*100)}%)",
             f"  ⚫ No Face      : {nf:>6} frames  ({round(nf/total*100)}%)",
             "",
             f"  DISTRACTION SNAPSHOTS  ({len(snaps)} captured)",
             "-" * 64,
             ]
        if snaps:
            for s in snaps:
                L.append(f"  📸 Face #{s['face_id']}  "
                         f"@ {s['timestamp']}  [{s['state']}]  "
                         f"Reason: {s['reason']}  "
                         f"Size:{s['size']}  Blur:{s['blur']}  "
                         f"→ {os.path.basename(s['path'])}")
        else:
            L.append("  No snapshots taken.")

        L += ["", "  KEY EVENTS", "-" * 64]
        for ts2, ev in (self.events if self.events
                        else [("—", "No events recorded.")]):
            L.append(f"  {ts2}   {ev}")

        L += ["", "  AI RECOMMENDATIONS", "-" * 64]
        ts3 = max(act + dis + ina + nf, 1)
        for r in self._recommendations(avg, act, dis, ina, ts3, len(snaps)):
            L.append(f"  {r}")

        L += ["", "=" * 64,
              "  Smart Campus AI — NeuroMirror Module (Production)",
              f"  University of Agriculture, Faisalabad | {datetime.now().year}"]

        report = "\n".join(L)
        self.report_box.configure(state="normal")
        self.report_box.delete("1.0", "end")
        self.report_box.insert("end", report)
        self.report_box.configure(state="disabled")

    def _export_csv(self):
        if not self.attention_scores:
            messagebox.showinfo("No Data", "Run a session first."); return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"neuromirror_{self.session_id}_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Frame", "Attention Score"])
                for i, sc in enumerate(self.attention_scores, 1):
                    w.writerow([i, sc])
            messagebox.showinfo("Exported", f"Saved:\n{path}")

    def _export_txt(self):
        report = self.report_box.get("1.0", "end")
        if "No data" in report or "Start a" in report:
            messagebox.showinfo("No Data", "Run a session first."); return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"neuromirror_report_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            filetypes=[("Text", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(report)
            messagebox.showinfo("Exported", f"Report saved:\n{path}")

    # ─── CLEANUP ─────────────────────────────────────────────
    def destroy(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self._worker.stop()
        super().destroy()

