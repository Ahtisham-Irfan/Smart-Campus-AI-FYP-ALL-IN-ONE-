# ============================================================
# Smart Campus AI v2 — Module 2: Smart Attendance
# Full history · Percentage · Daily/Weekly/Monthly
# ============================================================
import customtkinter as ctk
from tkinter import messagebox
import threading, os, sys, time, csv
from datetime import datetime
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_helper import (mark_attendance, get_attendance,
                                 get_attendance_stats, get_student_attendance_stats,
                                 get_attendance_by_period, get_all_students,
                                 reset_attendance, delete_attendance)

MODEL = os.path.join(os.path.dirname(__file__), "..", "models", "face_model.yml")
MAPF  = os.path.join(os.path.dirname(__file__), "..", "models", "label_map.txt")

C = {
    "bg":"#0a0c14","card":"#12151f","card2":"#0e1018","border":"#1e2235",
    "accent":"#4f8ef7","green":"#10b981","amber":"#f59e0b","red":"#ef4444",
    "teal":"#06b6d4","text":"#f1f5f9","muted":"#64748b","muted2":"#94a3b8",
}


class FaceAttendanceModule(ctk.CTkFrame):
    def __init__(self, parent, user):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.user    = user
        self.cap     = None
        self.running = False
        self.marked  = set()
        self._build()

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(sticky="ew", padx=24, pady=(16,8))
        ctk.CTkLabel(hdr, text="📋  Smart Attendance System",
                     font=ctk.CTkFont("Segoe UI",20,"bold"),
                     text_color=C["accent"]).pack(side="left")

        # Tabs
        self.tabs = ctk.CTkTabview(self, fg_color=C["card"],
                                   segmented_button_selected_color=C["accent"],
                                   segmented_button_fg_color=C["card2"])
        self.tabs.grid(sticky="nsew", padx=24, pady=(0,16))
        for t in ["Live Attendance","Attendance History","Analytics & Stats"]:
            self.tabs.add(t)

        self._build_live(self.tabs.tab("Live Attendance"))
        self._build_history(self.tabs.tab("Attendance History"))
        self._build_analytics(self.tabs.tab("Analytics & Stats"))

    # ── LIVE ────────────────────────────────────────────────
    def _build_live(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)

        # Camera panel
        left = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=10,
                            border_width=1, border_color=C["border"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=8)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(left, fg_color="transparent")
        ctrl.grid(sticky="ew", padx=14, pady=12)

        ctk.CTkLabel(ctrl, text="Subject:",
                     font=ctk.CTkFont("Segoe UI",12),
                     text_color=C["muted2"]).pack(side="left", padx=(0,6))
        self.subj_var = ctk.StringVar(value="Computer Science")
        ctk.CTkEntry(ctrl, textvariable=self.subj_var,
                     width=180, height=34, font=ctk.CTkFont("Segoe UI",12),
                     fg_color=C["card"], corner_radius=8,
                     border_color=C["border"]).pack(side="left", padx=(0,10))

        self.s_btn = ctk.CTkButton(ctrl, text="▶  Start",
                                   width=100, height=34, corner_radius=8,
                                   font=ctk.CTkFont("Segoe UI",12,"bold"),
                                   fg_color=C["green"], command=self._start)
        self.s_btn.pack(side="left", padx=(0,6))
        self.x_btn = ctk.CTkButton(ctrl, text="■  Stop",
                                   width=80, height=34, corner_radius=8,
                                   font=ctk.CTkFont("Segoe UI",12,"bold"),
                                   fg_color=C["red"], state="disabled",
                                   command=self._stop)
        self.x_btn.pack(side="left")

        self.cam_lbl = ctk.CTkLabel(left,
                                    text="📷  Camera Feed\n\nTrain model first in Face Recognition module.\nThen click Start to begin session.",
                                    font=ctk.CTkFont("Segoe UI",13),
                                    text_color=C["muted2"], justify="center")
        self.cam_lbl.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0,8))

        self.stat_lbl = ctk.CTkLabel(left, text="Session inactive",
                                     font=ctk.CTkFont("Segoe UI",11),
                                     text_color=C["teal"])
        self.stat_lbl.grid(sticky="w", padx=14, pady=(0,10))

        # Right: today's log
        right = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=10,
                             border_width=1, border_color=C["border"])
        right.grid(row=0, column=1, sticky="nsew", pady=8)
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="Today's Attendance",
                     font=ctk.CTkFont("Segoe UI",13,"bold"),
                     text_color=C["text"]).grid(padx=14, pady=(14,6), sticky="w")

        # Stats row
        sr = ctk.CTkFrame(right, fg_color=C["card"], corner_radius=8)
        sr.grid(padx=14, pady=(0,8), sticky="ew")
        sr.grid_columnconfigure(0, weight=1)
        sr.grid_columnconfigure(1, weight=1)
        self.t_lbl = self._mini(sr, "0", "Total Today", 0)
        self.s_lbl = self._mini(sr, "0", "This Session", 1)

        # Table header
        th = ctk.CTkFrame(right, fg_color=C["card"], corner_radius=4)
        th.grid(padx=8, sticky="ew")
        for col, w in [("Name",130),("Time",70),("Subject",100)]:
            ctk.CTkLabel(th, text=col, width=w,
                         font=ctk.CTkFont("Segoe UI",10,"bold"),
                         text_color=C["muted2"]).pack(side="left", padx=6, pady=5)

        self.live_table = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.live_table.grid(row=2, column=0, padx=8, pady=(0,8), sticky="nsew")

        # Export
        ctk.CTkButton(right, text="📥  Export CSV",
                      height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["card"], border_width=1, border_color=C["border"],
                      command=self._export).grid(padx=14, pady=(0,14), sticky="ew")
        self._refresh_live()

    def _mini(self, parent, val, lbl, col):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, padx=8, pady=8, sticky="ew")
        v = ctk.CTkLabel(f, text=val,
                         font=ctk.CTkFont("Segoe UI",20,"bold"),
                         text_color=C["accent"])
        v.pack()
        ctk.CTkLabel(f, text=lbl,
                     font=ctk.CTkFont("Segoe UI",10),
                     text_color=C["muted2"]).pack()
        return v

    def _refresh_live(self):
        for w in self.live_table.winfo_children():
            w.destroy()
        today   = datetime.now().strftime("%Y-%m-%d")
        records = get_attendance(date=today)
        self.t_lbl.configure(text=str(len(records)))
        self.s_lbl.configure(text=str(len(self.marked)))
        for i, r in enumerate(records):
            bg  = C["card"] if i%2==0 else C["card2"]
            row = ctk.CTkFrame(self.live_table, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            for txt, w in [(r["full_name"][:16],130),
                           (r["time"][:5],70),
                           (r.get("subject","")[:14],100)]:
                ctk.CTkLabel(row, text=txt, width=w,
                             font=ctk.CTkFont("Segoe UI",11),
                             text_color=C["green"]).pack(side="left", padx=6, pady=4)

    # ── HISTORY ─────────────────────────────────────────────
    def _build_history(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Filters
        filt = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=8,
                            border_width=1, border_color=C["border"])
        filt.grid(sticky="ew", pady=8)
        inner = ctk.CTkFrame(filt, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(inner, text="Filter by Date:",
                     font=ctk.CTkFont("Segoe UI",12),
                     text_color=C["muted2"]).pack(side="left", padx=(0,6))
        self.hist_date = ctk.StringVar()
        ctk.CTkEntry(inner, textvariable=self.hist_date, width=120, height=32,
                     placeholder_text="YYYY-MM-DD",
                     font=ctk.CTkFont("Segoe UI",11),
                     fg_color=C["card"], corner_radius=8,
                     border_color=C["border"]).pack(side="left", padx=(0,8))

        ctk.CTkLabel(inner, text="Subject:",
                     font=ctk.CTkFont("Segoe UI",12),
                     text_color=C["muted2"]).pack(side="left", padx=(0,6))
        self.hist_subj = ctk.StringVar()
        ctk.CTkEntry(inner, textvariable=self.hist_subj, width=150, height=32,
                     placeholder_text="All subjects",
                     font=ctk.CTkFont("Segoe UI",11),
                     fg_color=C["card"], corner_radius=8,
                     border_color=C["border"]).pack(side="left", padx=(0,8))

        ctk.CTkButton(inner, text="🔍 Search",
                      width=90, height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["accent"],
                      command=self._search_history).pack(side="left", padx=(0,8))
        ctk.CTkButton(inner, text="All Records",
                      width=100, height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["card"], border_width=1, border_color=C["border"],
                      command=lambda: (self.hist_date.set(""),
                                       self.hist_subj.set(""),
                                       self._search_history())).pack(side="left")
        ctk.CTkButton(inner, text="📥 Export",
                      width=90, height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["card"], border_width=1, border_color=C["border"],
                      command=self._export).pack(side="right")

        # Table
        th = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=4,
                          border_width=1, border_color=C["border"])
        th.grid(sticky="ew", pady=(0,4))
        for col, w in [("#",50),("Student ID",140),("Name",180),
                       ("Date",110),("Time",80),("Subject",150),("Status",90)]:
            ctk.CTkLabel(th, text=col, width=w,
                         font=ctk.CTkFont("Segoe UI",11,"bold"),
                         text_color=C["muted2"]).pack(side="left", padx=6, pady=7)

        self.hist_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.hist_scroll.grid(sticky="nsew", pady=(0,8))
        self._search_history()

    def _search_history(self):
        for w in self.hist_scroll.winfo_children():
            w.destroy()
        date = self.hist_date.get().strip() or None
        subj = self.hist_subj.get().strip() or None
        records = get_attendance(date=date, subject=subj)

        if not records:
            ctk.CTkLabel(self.hist_scroll, text="No records found.",
                         font=ctk.CTkFont("Segoe UI",12),
                         text_color=C["muted2"]).pack(pady=20)
            return

        for i, r in enumerate(records):
            bg  = C["card"] if i%2==0 else C["card2"]
            row = ctk.CTkFrame(self.hist_scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            for txt, w, tc in [
                (str(i+1),50,C["muted"]),
                (r["student_id"][:14],140,C["teal"]),
                (r["full_name"][:18],180,C["text"]),
                (r["date"],110,C["muted2"]),
                (r["time"][:8],80,C["muted2"]),
                (r.get("subject","")[:16],150,C["muted2"]),
                ("✅ Present",90,C["green"]),
            ]:
                ctk.CTkLabel(row, text=txt, width=w,
                             font=ctk.CTkFont("Segoe UI",11),
                             text_color=tc).pack(side="left", padx=6, pady=4)

    # ── ANALYTICS ───────────────────────────────────────────
    def _build_analytics(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=8,
                            border_width=1, border_color=C["border"])
        ctrl.grid(sticky="ew", pady=8)
        cr = ctk.CTkFrame(ctrl, fg_color="transparent")
        cr.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(cr, text="Period:",
                     font=ctk.CTkFont("Segoe UI",12),
                     text_color=C["muted2"]).pack(side="left", padx=(0,8))
        self.period_var = ctk.StringVar(value="daily")
        ctk.CTkSegmentedButton(cr,
                               values=["daily","weekly","monthly","yearly"],
                               variable=self.period_var,
                               selected_color=C["accent"],
                               font=ctk.CTkFont("Segoe UI",11),
                               command=lambda v: self._load_analytics()
                               ).pack(side="left", padx=(0,12))

        ctk.CTkButton(cr, text="🔄 Refresh",
                      width=90, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["accent"],
                      command=self._load_analytics).pack(side="left", padx=(0,8))
        ctk.CTkButton(cr, text="🗑 Reset All Attendance",
                      width=160, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["red"],
                      command=self._reset_all).pack(side="right")

        self.anal_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.anal_scroll.grid(sticky="nsew", pady=(0,8))
        self._load_analytics()

    def _load_analytics(self):
        for w in self.anal_scroll.winfo_children():
            w.destroy()

        stats  = get_attendance_stats()
        period = self.period_var.get()
        data   = get_attendance_by_period(period)

        # Top stats
        sf = ctk.CTkFrame(self.anal_scroll, fg_color="transparent")
        sf.pack(fill="x", pady=(0,14))
        for i in range(4): sf.grid_columnconfigure(i, weight=1)
        for i, (lbl, val, col) in enumerate([
            ("Total Records",   str(stats["total"]),           C["accent"]),
            ("Today",           str(stats["today"]),           C["green"]),
            ("Unique Students", str(stats["unique_students"]), C["teal"]),
            ("Period Entries",  str(len(data)),                C["amber"]),
        ]):
            card = ctk.CTkFrame(sf, fg_color=C["card2"], corner_radius=8,
                                border_width=1, border_color=C["border"])
            card.grid(row=0, column=i, padx=5, sticky="ew")
            ctk.CTkLabel(card, text=val,
                         font=ctk.CTkFont("Segoe UI",22,"bold"),
                         text_color=col).grid(pady=(10,2))
            ctk.CTkLabel(card, text=lbl,
                         font=ctk.CTkFont("Segoe UI",10),
                         text_color=C["muted2"]).grid(pady=(0,10))

        # Period bar chart (text-based)
        ctk.CTkLabel(self.anal_scroll,
                     text=f"Attendance — {period.title()} View",
                     font=ctk.CTkFont("Segoe UI",13,"bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0,8))

        if data:
            max_cnt = max(d["cnt"] for d in data) or 1
            chart_f = ctk.CTkFrame(self.anal_scroll, fg_color=C["card2"],
                                   corner_radius=10, border_width=1,
                                   border_color=C["border"])
            chart_f.pack(fill="x", pady=(0,14))
            for row in data:
                period_key = row.get("date") or row.get("wk") or row.get("mo") or row.get("yr","—")
                cnt = row["cnt"]
                pct = cnt / max_cnt

                r = ctk.CTkFrame(chart_f, fg_color="transparent")
                r.pack(fill="x", padx=16, pady=3)
                ctk.CTkLabel(r, text=str(period_key), width=110, anchor="e",
                             font=ctk.CTkFont("Consolas",11),
                             text_color=C["muted2"]).pack(side="left", padx=(0,10))
                bar = ctk.CTkProgressBar(r, height=16, corner_radius=8,
                                         progress_color=C["accent"],
                                         fg_color=C["card"])
                bar.pack(side="left", fill="x", expand=True, padx=(0,8))
                bar.set(pct)
                ctk.CTkLabel(r, text=str(cnt), width=36,
                             font=ctk.CTkFont("Segoe UI",11),
                             text_color=C["accent"]).pack(side="left")

        # Per-student stats
        ctk.CTkLabel(self.anal_scroll, text="Per-Student Attendance & Percentage",
                     font=ctk.CTkFont("Segoe UI",13,"bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(8,8))

        students = get_all_students()
        if not students:
            ctk.CTkLabel(self.anal_scroll, text="No students enrolled.",
                         font=ctk.CTkFont("Segoe UI",12),
                         text_color=C["muted2"]).pack()
            return

        for s in students:
            ss = get_student_attendance_stats(s["student_id"])
            pct = ss["percentage"]
            pct_color = (C["green"] if pct >= 75 else
                         C["amber"] if pct >= 50 else C["red"])

            card = ctk.CTkFrame(self.anal_scroll, fg_color=C["card2"],
                                corner_radius=8, border_width=1,
                                border_color=C["border"])
            card.pack(fill="x", pady=3)
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(10,4))

            ctk.CTkLabel(top, text=s["full_name"],
                         font=ctk.CTkFont("Segoe UI",12,"bold"),
                         text_color=C["text"]).pack(side="left")
            ctk.CTkLabel(top, text=s["student_id"],
                         font=ctk.CTkFont("Segoe UI",10),
                         text_color=C["teal"]).pack(side="left", padx=(8,0))
            ctk.CTkLabel(top, text=f"{pct}%",
                         font=ctk.CTkFont("Segoe UI",16,"bold"),
                         text_color=pct_color).pack(side="right")

            bot = ctk.CTkFrame(card, fg_color="transparent")
            bot.pack(fill="x", padx=14, pady=(0,10))

            bar = ctk.CTkProgressBar(bot, height=10, corner_radius=5,
                                     progress_color=pct_color, fg_color=C["card"])
            bar.pack(fill="x", pady=(0,4))
            bar.set(pct / 100)

            ctk.CTkLabel(bot,
                         text=f"Days attended: {ss['total']}  |  Last: {ss['last_date']}  |  Total school days: {ss['school_days']}",
                         font=ctk.CTkFont("Segoe UI",10),
                         text_color=C["muted2"]).pack(anchor="w")

    # ── Camera Logic ────────────────────────────────────────
    def _load_recognizer(self):
        try:
            import cv2
            if not os.path.exists(MODEL):
                return None, None, None
            rec = cv2.face.LBPHFaceRecognizer_create()
            rec.read(MODEL)
            label_map = {}
            if os.path.exists(MAPF):
                with open(MAPF) as f:
                    for line in f:
                        parts = line.strip().split(":")
                        if len(parts) == 2:
                            label_map[int(parts[0])] = parts[1]
            fc = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            return rec, label_map, fc
        except:
            return None, None, None

    def _start(self):
        self.running = True
        self.marked  = set()
        self.s_btn.configure(state="disabled")
        self.x_btn.configure(state="normal")
        threading.Thread(target=self._cam_loop, daemon=True).start()

    def _stop(self):
        self.running = False
        self.s_btn.configure(state="normal")
        self.x_btn.configure(state="disabled")
        self.stat_lbl.configure(text="Session ended.")

    def _cam_loop(self):
        try:
            import cv2
        except ImportError:
            self.after(0, lambda: self.stat_lbl.configure(text="OpenCV not installed"))
            return

        rec, label_map, fc = self._load_recognizer()
        if rec is None:
            self.after(0, lambda: self.stat_lbl.configure(
                text="⚠ No trained model! Train in Face Recognition module first."))
            self.running = False
            return

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.after(0, lambda: self.stat_lbl.configure(text="⚠ Camera not found!"))
            self.running = False
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        subj = self.subj_var.get().strip()

        while self.running:
            ret, frame = self.cap.read()
            if not ret: break
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.3, 5, minSize=(80,80))

            for (x, y, w, h) in faces:
                roi = gray[y:y+h, x:x+w]
                try:
                    label, conf = rec.predict(roi)
                except:
                    continue
                sid   = label_map.get(label, "unknown")
                score = round(100 - conf, 1)

                if conf < 70 and sid != "unknown":
                    color = (0,220,120)
                    dname = sid.replace("-"," ").title()
                    txt   = f"{dname} ({score}%)"
                    if sid not in self.marked:
                        ok = mark_attendance(sid, dname, subj)
                        if ok:
                            self.marked.add(sid)
                            self.after(0, self._refresh_live)
                else:
                    color = (100,120,255)
                    txt   = "Unknown"

                cv2.rectangle(frame,(x,y),(x+w,y+h),color,2)
                cv2.putText(frame, txt,(x,y-8),
                            cv2.FONT_HERSHEY_SIMPLEX,0.6,color,2)

            msg = f"Active | Marked: {len(self.marked)} | Faces: {len(faces)}"
            cv2.putText(frame, msg,(10,26),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,220,200),2)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img.thumbnail((500,380))
            ci  = ctk.CTkImage(img, size=img.size)
            self.after(0, lambda i=ci, m=msg: (
                self.cam_lbl.configure(image=i, text=""),
                self.stat_lbl.configure(text=m),
            ))
            self.cam_lbl.image_ref = ci
            time.sleep(0.04)

        self.cap.release()

    def _export(self):
        from tkinter import filedialog
        today   = datetime.now().strftime("%Y-%m-%d")
        records = get_attendance()
        path    = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"attendance_{today}.csv",
            filetypes=[("CSV","*.csv")])
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["student_id","full_name",
                                                   "date","time","subject","status"])
                w.writeheader(); w.writerows(records)
            messagebox.showinfo("Exported", f"Saved to:\n{path}")

    def _reset_all(self):
        if messagebox.askyesno("Reset", "Delete ALL attendance records?"):
            reset_attendance()
            self._refresh_live()
            self._search_history()
            self._load_analytics()
            messagebox.showinfo("Reset", "All attendance records cleared.")

    def destroy(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        super().destroy()
