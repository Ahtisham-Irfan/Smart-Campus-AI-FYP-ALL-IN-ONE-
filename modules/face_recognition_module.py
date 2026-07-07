# ============================================================
# Smart Campus AI v2 — Module 1: Face Recognition
# Persistent enrollment — survives restarts
# ============================================================
import customtkinter as ctk
from tkinter import messagebox
import threading, os, sys, time
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_helper import (add_student, get_all_students, student_exists,
                                 update_student_photos, delete_student, update_student)

BASE   = os.path.join(os.path.dirname(__file__), "..", "assets", "dataset")
MODEL  = os.path.join(os.path.dirname(__file__), "..", "models", "face_model.yml")
MAPF   = os.path.join(os.path.dirname(__file__), "..", "models", "label_map.txt")
os.makedirs(BASE, exist_ok=True)
os.makedirs(os.path.dirname(MODEL), exist_ok=True)

C = {
    "bg":"#0a0c14","card":"#12151f","card2":"#0e1018","border":"#1e2235",
    "accent":"#06b6d4","green":"#10b981","amber":"#f59e0b","red":"#ef4444",
    "text":"#f1f5f9","muted":"#64748b","muted2":"#94a3b8",
}


class FaceRecognitionModule(ctk.CTkFrame):
    def __init__(self, parent, user):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.user    = user
        self.cap     = None
        self.running = False
        self.photos  = 0
        self._build()

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(sticky="ew", padx=24, pady=(16,8))
        ctk.CTkLabel(hdr, text="👁  Face Recognition — Persistent Enrollment",
                     font=ctk.CTkFont("Segoe UI",20,"bold"),
                     text_color=C["accent"]).pack(side="left")
        ctk.CTkButton(hdr, text="🔄  Refresh List",
                      width=120, height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["card"], border_width=1, border_color=C["border"],
                      command=self._refresh_table).pack(side="right")

        # Body — tabs
        self.tabs = ctk.CTkTabview(self, fg_color=C["card"],
                                   segmented_button_selected_color=C["accent"],
                                   segmented_button_fg_color=C["card2"])
        self.tabs.grid(sticky="nsew", padx=24, pady=(0,16))
        self.tabs.add("Enroll New Student")
        self.tabs.add("Enrolled Students")
        self.tabs.add("Train / Manage Model")

        self._build_enroll(self.tabs.tab("Enroll New Student"))
        self._build_list(self.tabs.tab("Enrolled Students"))
        self._build_train(self.tabs.tab("Train / Manage Model"))

    # ── TAB 1: ENROLL ───────────────────────────────────────
    def _build_enroll(self, tab):
        tab.grid_columnconfigure(0, weight=2)
        tab.grid_columnconfigure(1, weight=3)
        tab.grid_rowconfigure(0, weight=1)

        # Left form
        lf = ctk.CTkScrollableFrame(tab, fg_color=C["card2"],
                                    corner_radius=10, border_width=1,
                                    border_color=C["border"])
        lf.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=8)

        ctk.CTkLabel(lf, text="Student Information",
                     font=ctk.CTkFont("Segoe UI",13,"bold"),
                     text_color=C["text"]).pack(padx=16, pady=(14,10), anchor="w")

        self.ev = {}
        for lbl, key, ph in [
            ("Student ID *", "sid",  "2022-AG-0001"),
            ("Full Name *",  "name", "Ahmed Ali"),
            ("Department",   "dept", "Computer Science"),
            ("Semester",     "sem",  "7th Semester"),
        ]:
            ctk.CTkLabel(lf, text=lbl, font=ctk.CTkFont("Segoe UI",11),
                         text_color=C["muted2"]).pack(padx=16, anchor="w")
            v = ctk.StringVar()
            self.ev[key] = v
            ctk.CTkEntry(lf, textvariable=v, height=36, placeholder_text=ph,
                         font=ctk.CTkFont("Segoe UI",12),
                         fg_color=C["card"], corner_radius=8,
                         border_color=C["border"]).pack(padx=16, pady=(3,10), fill="x")

        ctk.CTkLabel(lf, text="Photos to Capture",
                     font=ctk.CTkFont("Segoe UI",11),
                     text_color=C["muted2"]).pack(padx=16, anchor="w")
        self.ph_var = ctk.IntVar(value=60)
        sr = ctk.CTkFrame(lf, fg_color="transparent")
        sr.pack(padx=16, fill="x", pady=(3,10))
        ctk.CTkSlider(sr, from_=30, to=120, variable=self.ph_var,
                      button_color=C["accent"],
                      command=lambda v: self.ph_lbl.configure(
                          text=f"{int(v)} photos")).pack(side="left", fill="x", expand=True)
        self.ph_lbl = ctk.CTkLabel(sr, text="60 photos", width=70,
                                   font=ctk.CTkFont("Segoe UI",11),
                                   text_color=C["accent"])
        self.ph_lbl.pack(side="left", padx=(8,0))

        self.prog = ctk.CTkProgressBar(lf, height=8, progress_color=C["green"])
        self.prog.pack(padx=16, fill="x", pady=(0,4))
        self.prog.set(0)
        self.prog_lbl = ctk.CTkLabel(lf, text="Ready",
                                     font=ctk.CTkFont("Segoe UI",11),
                                     text_color=C["muted2"])
        self.prog_lbl.pack(padx=16, anchor="w", pady=(0,12))

        br = ctk.CTkFrame(lf, fg_color="transparent")
        br.pack(padx=16, fill="x", pady=(0,12))
        br.columnconfigure(0, weight=1); br.columnconfigure(1, weight=1)

        self.start_btn = ctk.CTkButton(br, text="▶  Start Camera",
                                       height=38, corner_radius=8,
                                       font=ctk.CTkFont("Segoe UI",12,"bold"),
                                       fg_color=C["accent"],
                                       command=self._start)
        self.start_btn.grid(row=0, column=0, padx=(0,4), sticky="ew")

        self.stop_btn = ctk.CTkButton(br, text="■  Stop",
                                      height=38, corner_radius=8,
                                      font=ctk.CTkFont("Segoe UI",12,"bold"),
                                      fg_color=C["red"], state="disabled",
                                      command=self._stop)
        self.stop_btn.grid(row=0, column=1, padx=(4,0), sticky="ew")

        self.status_lbl = ctk.CTkLabel(lf, text="",
                                       font=ctk.CTkFont("Segoe UI",12),
                                       text_color=C["green"], wraplength=280)
        self.status_lbl.pack(padx=16, pady=(0,16))

        # Right: camera preview
        rf = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=10,
                          border_width=1, border_color=C["border"])
        rf.grid(row=0, column=1, sticky="nsew", pady=8)
        rf.grid_rowconfigure(0, weight=1)
        rf.grid_columnconfigure(0, weight=1)

        self.cam_lbl = ctk.CTkLabel(rf,
                                    text="📷  Camera Preview\n\nClick 'Start Camera' to begin enrollment\n\nTips for accurate results:\n• Good lighting\n• Face camera directly\n• Slight angle variations",
                                    font=ctk.CTkFont("Segoe UI",13),
                                    text_color=C["muted2"], justify="center")
        self.cam_lbl.grid(sticky="nsew", padx=16, pady=16)

    # ── TAB 2: ENROLLED LIST ────────────────────────────────
    def _build_list(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Header row
        hrow = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=8,
                            border_width=1, border_color=C["border"])
        hrow.grid(sticky="ew", pady=(8,4))
        for col, w in [("Student ID",160),("Full Name",200),("Department",160),
                       ("Photos",80),("Trained",80),("Enrolled",120),("Actions",120)]:
            ctk.CTkLabel(hrow, text=col, width=w,
                         font=ctk.CTkFont("Segoe UI",11,"bold"),
                         text_color=C["muted2"]).pack(side="left", padx=8, pady=8)

        self.list_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.list_scroll.grid(sticky="nsew", pady=(0,8))
        self._refresh_table()

    # ── TAB 3: TRAIN ────────────────────────────────────────
    def _build_train(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        info_card = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=10,
                                 border_width=1, border_color=C["border"])
        info_card.grid(sticky="ew", padx=0, pady=8)
        inner = ctk.CTkFrame(info_card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(inner, text="Model Training",
                     font=ctk.CTkFont("Segoe UI",14,"bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0,8))

        bullets = [
            "✅  Train model after enrolling ALL students",
            "✅  Model is saved permanently — survives restarts",
            "✅  Re-train only when you add new students",
            "✅  Supports unlimited number of students",
            "⚠️   Minimum 30 photos per student recommended",
        ]
        for b in bullets:
            ctk.CTkLabel(inner, text=b,
                         font=ctk.CTkFont("Segoe UI",12),
                         text_color=C["muted2"]).pack(anchor="w", pady=2)

        self.train_btn = ctk.CTkButton(inner, text="🧠  Train Face Recognition Model",
                                       height=44, corner_radius=10,
                                       font=ctk.CTkFont("Segoe UI",13,"bold"),
                                       fg_color=C["amber"], text_color="#1a1a1a",
                                       hover_color="#d97706",
                                       command=self._train)
        self.train_btn.pack(fill="x", pady=(14,0))

        self.train_lbl = ctk.CTkLabel(inner, text="",
                                      font=ctk.CTkFont("Segoe UI",12),
                                      text_color=C["green"], wraplength=500)
        self.train_lbl.pack(pady=(10,0))

        # Model info
        self.model_info = ctk.CTkTextbox(tab, height=200,
                                         font=ctk.CTkFont("Consolas",11),
                                         fg_color=C["card2"],
                                         border_width=1, border_color=C["border"])
        self.model_info.grid(sticky="nsew", pady=(0,8))
        self._load_model_info()

    def _load_model_info(self):
        self.model_info.configure(state="normal")
        self.model_info.delete("1.0", "end")
        exists = os.path.exists(MODEL)
        students = get_all_students()
        lines = [
            f"Model file : {'EXISTS ✅' if exists else 'NOT TRAINED ❌'}",
            f"Model path : {MODEL}",
            f"Students enrolled : {len(students)}",
            "",
        ]
        if students:
            lines.append("Enrolled students:")
            for s in students:
                ph = s.get("photo_count", 0)
                trained = "✅" if s.get("model_trained") else "⏳"
                lines.append(f"  {trained}  {s['student_id']}  |  {s['full_name']}  |  {ph} photos")
        self.model_info.insert("end", "\n".join(lines))
        self.model_info.configure(state="disabled")

    # ── Camera ───────────────────────────────────────────────
    def _start(self):
        sid  = self.ev["sid"].get().strip()
        name = self.ev["name"].get().strip()
        if not sid or not name:
            messagebox.showwarning("Missing Info", "Student ID and Full Name are required!")
            return

        if not student_exists(sid):
            add_student(sid, name,
                        self.ev["dept"].get().strip() or "Computer Science",
                        self.ev["sem"].get().strip()  or "—")

        self.cur_sid  = sid
        self.cur_name = name
        self.save_dir = os.path.join(BASE, sid)
        os.makedirs(self.save_dir, exist_ok=True)

        # Count existing photos
        existing = len([f for f in os.listdir(self.save_dir)
                        if f.lower().endswith(".jpg")])
        self.photos   = existing
        self.target   = int(self.ph_var.get()) + existing
        self.running  = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.prog.set(0)
        threading.Thread(target=self._cam_loop, daemon=True).start()

    def _cam_loop(self):
        try:
            import cv2, numpy as np
        except ImportError:
            self.after(0, lambda: self.status_lbl.configure(
                text="⚠ OpenCV not installed", text_color=C["red"]))
            return

        cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        fc = cv2.CascadeClassifier(cascade)
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.after(0, lambda: self.status_lbl.configure(
                text="⚠ Camera not found!", text_color=C["red"]))
            self.running = False
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        target = int(self.ph_var.get())

        while self.running and self.photos < (self.photos + target - target + target):
            ret, frame = self.cap.read()
            if not ret: break
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.3, 5, minSize=(80,80))
            local_count = len([f for f in os.listdir(self.save_dir) if f.endswith(".jpg")])

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x,y), (x+w,y+h), (0,220,150), 2)
                if local_count < target:
                    roi = gray[y:y+h, x:x+w]
                    cv2.imwrite(os.path.join(self.save_dir, f"{local_count:04d}.jpg"), roi)
                    local_count += 1

            prog  = local_count / target
            msg   = f"Captured: {local_count}/{target}"
            cv2.putText(frame, msg, (10,26), cv2.FONT_HERSHEY_SIMPLEX,
                        0.65, (0,220,150), 2)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img.thumbnail((480,360))
            ci  = ctk.CTkImage(img, size=img.size)
            self.after(0, lambda i=ci, p=prog, m=msg: (
                self.cam_lbl.configure(image=i, text=""),
                self.prog.set(p),
                self.prog_lbl.configure(text=m),
            ))
            self.cam_lbl.image_ref = ci

            if local_count >= target:
                self.running = False
                update_student_photos(self.cur_sid, local_count)
                self.after(0, lambda n=local_count: self._enroll_done(n))
                break
            time.sleep(0.03)

        self.cap.release()
        self.after(0, self._reset_btns)

    def _enroll_done(self, n):
        self.status_lbl.configure(
            text=f"✅  {n} photos captured!\nNow go to 'Train / Manage Model' tab.",
            text_color=C["green"])
        self._refresh_table()

    def _stop(self):
        self.running = False
        self._reset_btns()

    def _reset_btns(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _refresh_table(self):
        for w in self.list_scroll.winfo_children():
            w.destroy()
        students = get_all_students()
        if not students:
            ctk.CTkLabel(self.list_scroll,
                         text="No students enrolled yet.\nUse 'Enroll New Student' tab.",
                         font=ctk.CTkFont("Segoe UI",13),
                         text_color=C["muted2"],
                         justify="center").pack(pady=30)
            return
        for i, s in enumerate(students):
            bg = C["card"] if i%2==0 else C["card2"]
            row = ctk.CTkFrame(self.list_scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=2)
            trained = "✅ Yes" if s.get("model_trained") else "⏳ No"
            t_color = C["green"] if s.get("model_trained") else C["amber"]
            for txt, w, tc in [
                (s["student_id"],          160, C["accent"]),
                (s["full_name"][:22],       200, C["text"]),
                (s.get("department","")[:18],160, C["muted2"]),
                (str(s.get("photo_count",0)),80, C["muted2"]),
                (trained,                    80, t_color),
                (s.get("enrolled_at","")[:10],120, C["muted"]),
            ]:
                ctk.CTkLabel(row, text=txt, width=w,
                             font=ctk.CTkFont("Segoe UI",11),
                             text_color=tc).pack(side="left", padx=8, pady=5)
            # Delete button
            ctk.CTkButton(row, text="🗑",
                          width=40, height=26, corner_radius=6,
                          font=ctk.CTkFont("Segoe UI",11),
                          fg_color=C["red"], hover_color="#b91c1c",
                          command=lambda sid=s["student_id"]: self._del_student(sid)
                          ).pack(side="left", padx=4)

    def _del_student(self, sid):
        if messagebox.askyesno("Delete", f"Delete student {sid} and all their data?"):
            import shutil
            folder = os.path.join(BASE, sid)
            if os.path.exists(folder):
                shutil.rmtree(folder)
            delete_student(sid)
            self._refresh_table()
            messagebox.showinfo("Deleted", f"Student {sid} removed.")

    # ── Train ────────────────────────────────────────────────
    def _train(self):
        self.train_btn.configure(state="disabled", text="⏳ Training…")
        self.train_lbl.configure(text="Building model — please wait…",
                                 text_color=C["amber"])
        threading.Thread(target=self._do_train, daemon=True).start()

    def _do_train(self):
        try:
            import cv2, numpy as np
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            faces_data, labels, label_map, lc = [], [], {}, 0

            for folder in os.listdir(BASE):
                path = os.path.join(BASE, folder)
                if not os.path.isdir(path): continue
                label_map[lc] = folder
                for fname in os.listdir(path):
                    if fname.lower().endswith((".jpg",".png")):
                        img = cv2.imread(os.path.join(path, fname),
                                         cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            faces_data.append(img)
                            labels.append(lc)
                lc += 1
                update_student_photos(folder,
                    len([f for f in os.listdir(path)
                         if f.lower().endswith((".jpg",".png"))]),
                    trained=True)

            if not faces_data:
                self.after(0, lambda: self.train_lbl.configure(
                    text="⚠ No data found! Enroll students first.",
                    text_color=C["red"]))
                return

            recognizer.train(faces_data, np.array(labels))
            recognizer.save(MODEL)
            with open(MAPF, "w") as f:
                for k, v in label_map.items():
                    f.write(f"{k}:{v}\n")

            n = len(set(labels))
            self.after(0, lambda: (
                self.train_lbl.configure(
                    text=f"✅ Model trained on {n} students! Face Attendance ready.",
                    text_color=C["green"]),
                self._refresh_table(),
                self._load_model_info(),
            ))
        except Exception as e:
            self.after(0, lambda: self.train_lbl.configure(
                text=f"⚠ Error: {e}", text_color=C["red"]))
        finally:
            self.after(0, lambda: self.train_btn.configure(
                state="normal", text="🧠  Train Face Recognition Model"))

    def destroy(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        super().destroy()
