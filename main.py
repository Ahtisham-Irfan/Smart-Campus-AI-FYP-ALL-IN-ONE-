# ============================================================
# Smart Campus AI
# Run: python main.py
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
import os, sys, importlib

sys.path.insert(0, os.path.dirname(__file__))
from database.db_setup  import initialize_database
from database.db_helper import verify_login, get_attendance_stats

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

C = {
    "bg":      "#0a0c14",
    "card":    "#12151f",
    "card2":   "#0e1018",
    "border":  "#1e2235",
    "accent":  "#4f8ef7",
    "purple":  "#7c3aed",
    "teal":    "#06b6d4",
    "green":   "#10b981",
    "amber":   "#f59e0b",
    "red":     "#ef4444",
    "pink":    "#ec4899",
    "text":    "#f1f5f9",
    "muted":   "#64748b",
    "muted2":  "#94a3b8",
}

def _center(win, w, h):
    win.update_idletasks()
    x = (win.winfo_screenwidth()  - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

# ═══════════════════════════════════════════════════════════
#  LOGIN
# ═══════════════════════════════════════════════════════════
class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Smart Campus AI by 2022-ag-9158")
        self.resizable(True, True)
        self.configure(fg_color=C["bg"])
        _center(self, 500, 620)
        self._ui()

    def _ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(sticky="nsew", padx=40, pady=30)
        outer.grid_columnconfigure(0, weight=1)

        # Logo
        ctk.CTkLabel(outer, text="🎓",
                     font=ctk.CTkFont("Segoe UI Emoji", 52)).grid(pady=(0,4))
        ctk.CTkLabel(outer, text="Smart Campus AI",
                     font=ctk.CTkFont("Segoe UI", 26, "bold"),
                     text_color=C["accent"]).grid()
        ctk.CTkLabel(outer, text="Emotion-Aware Intelligent Campus System",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=C["muted2"]).grid(pady=(2,2))
        ctk.CTkLabel(outer, text="University of Agriculture, Faisalabad",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["muted"]).grid(pady=(0,20))
        ctk.CTkLabel(outer, text="M. Ahtisham Irfan | 2022-ag-9158",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["muted"]).grid(pady=(0,20))

        # Card
        card = ctk.CTkFrame(outer, fg_color=C["card"], corner_radius=16,
                            border_width=1, border_color=C["border"])
        card.grid(sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Sign In",
                     font=ctk.CTkFont("Segoe UI", 18, "bold"),
                     text_color=C["text"]).grid(padx=28, pady=(24,16), sticky="w")

        for lbl, attr, ph, show in [
            ("Username", "u_var", "Enter username", ""),
            ("Password", "p_var", "Enter password", "●"),
        ]:
            ctk.CTkLabel(card, text=lbl, font=ctk.CTkFont("Segoe UI",11),
                         text_color=C["muted2"]).grid(padx=28, sticky="w")
            var = ctk.StringVar()
            setattr(self, attr, var)
            e = ctk.CTkEntry(card, textvariable=var, height=42, show=show,
                             placeholder_text=ph,
                             font=ctk.CTkFont("Segoe UI",13),
                             fg_color=C["card2"], corner_radius=8,
                             border_color=C["accent"])
            e.grid(padx=28, pady=(4,12), sticky="ew")
            if attr == "u_var":
                e.focus(); var.set("admin")
            else:
                var.set("admin123")

        self.show_var = ctk.BooleanVar()
        ctk.CTkCheckBox(card, text="Show password", variable=self.show_var,
                        command=self._toggle,
                        font=ctk.CTkFont("Segoe UI",11),
                        text_color=C["muted2"]).grid(padx=28, sticky="w")

        self.err_lbl = ctk.CTkLabel(card, text="",
                                    font=ctk.CTkFont("Segoe UI",12),
                                    text_color=C["red"])
        self.err_lbl.grid(pady=(8,0))

        self.btn = ctk.CTkButton(card, text="🔐  Sign In",
                                 height=44, corner_radius=10,
                                 font=ctk.CTkFont("Segoe UI",14,"bold"),
                                 fg_color=C["accent"], hover_color="#3a7de8",
                                 command=self._login)
        self.btn.grid(padx=28, pady=(8,24), sticky="ew")

        ctk.CTkLabel(outer,
                     text="admin/admin123  ·  teacher/teacher123  ·  student/student123",
                     font=ctk.CTkFont("Segoe UI",10),
                     text_color=C["muted"]).grid(pady=(14,0))

        self.bind("<Return>", lambda e: self._login())

    def _toggle(self):
        # find password entry — it's the one with show="●"
        for w in self.winfo_children():
            self._recurse_toggle(w)

    def _recurse_toggle(self, widget):
        for child in widget.winfo_children():
            if isinstance(child, ctk.CTkEntry) and child.cget("show") in ("●", ""):
                if hasattr(self, "p_var") and child.cget("textvariable") == str(self.p_var) \
                        or child._textvariable == self.p_var:
                    child.configure(show="" if self.show_var.get() else "●")
            self._recurse_toggle(child)

    def _login(self):
        u = self.u_var.get().strip()
        p = self.p_var.get().strip()
        if not u or not p:
            self.err_lbl.configure(text="⚠  Please fill both fields")
            return
        self.btn.configure(state="disabled", text="Signing in…")
        self.err_lbl.configure(text="")
        self.after(200, lambda: self._check(u, p))

    def _check(self, u, p):
        user = verify_login(u, p)
        if user:
            self.withdraw()
            Dashboard(user, self).mainloop()
        else:
            self.err_lbl.configure(text="✗  Invalid credentials")
            self.btn.configure(state="normal", text="🔐  Sign In")

# ═══════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════
class Dashboard(ctk.CTkToplevel):
    NAV = [
        ("🏠", "Dashboard",         "_home"),
        ("👁", "Face Recognition",  "face_recognition_module.FaceRecognitionModule"),
        ("📋", "AI Attendance",     "face_attendance.FaceAttendanceModule"),
        ("😊", "Emotion Detection", "emotion_detection.EmotionDetectionModule"),
        ("🧠", "NeuroMirror AI",    "neuromirror.NeuroMirrorModule"),
        ("📅", "Study Planner",     "study_planner.StudyPlannerModule"),
        ("📄", "Doc Summarizer",    "doc_summarizer.DocSummarizerModule"),
        ("📑", "Resume Screener",   "resume_screener.ResumeScreenerModule"),
        ("⚙",  "Admin Panel",      "admin_panel.AdminPanelModule"),
    ]

    def __init__(self, user, login):
        super().__init__()
        self.user  = user
        self.login = login
        self.title(f"Smart Campus AI — {user['role'].title()} Panel")
        self.configure(fg_color=C["bg"])
        _center(self, 1300, 800)
        self.minsize(1000, 650)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build()

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ── Sidebar  (pack-based — no row conflicts)
        sb = ctk.CTkFrame(self, width=220, fg_color=C["card"],
                          corner_radius=0, border_width=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.pack_propagate(False)

        # ── Logo
        ctk.CTkLabel(sb, text="🎓 Smart Campus AI",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=C["accent"],
                     wraplength=200).pack(pady=(20, 2), padx=14, anchor="w")
        ctk.CTkLabel(sb, text="UAF · FYP 2022-AG-9158",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=C["muted"]).pack(padx=14, anchor="w")

        ctk.CTkFrame(sb, height=1, fg_color=C["border"]).pack(
            fill="x", padx=14, pady=12)

        # ── User info
        role_c = {
            "admin": C["accent"], "teacher": C["green"], "student": C["teal"]
        }.get(self.user["role"], C["muted2"])
        ctk.CTkLabel(sb, text=f"👤  {self.user['full_name']}",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=C["text"]).pack(padx=14, anchor="w")
        ctk.CTkLabel(sb, text=f"  {self.user['role'].upper()}",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=role_c).pack(padx=14, anchor="w", pady=(0, 10))

        ctk.CTkFrame(sb, height=1, fg_color=C["border"]).pack(
            fill="x", padx=14, pady=(0, 8))

        # ── Main content area
        self.main = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        # ── Nav buttons — ALL packed, no row conflicts
        self.nav_btns = []
        for i, (icon, label, target) in enumerate(self.NAV):
            btn = ctk.CTkButton(sb, text=f"{icon}  {label}",
                                anchor="w", height=38, corner_radius=8,
                                font=ctk.CTkFont("Segoe UI", 12),
                                fg_color="transparent",
                                hover_color=C["border"],
                                text_color=C["muted2"],
                                command=lambda t=target, idx=i: self._nav(t, idx))
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_btns.append(btn)

        # ── Logout
        ctk.CTkButton(sb, text="🚪  Logout",
                      anchor="w", height=38, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 12),
                      fg_color="transparent", hover_color="#2a1010",
                      text_color=C["red"],
                      command=self._logout).pack(fill="x", padx=8, pady=(0, 16))

        self._nav("_home", 0)

    def _clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def _highlight(self, idx):
        for i, btn in enumerate(self.nav_btns):
            if i == idx:
                btn.configure(fg_color=C["border"], text_color=C["text"])
            else:
                btn.configure(fg_color="transparent", text_color=C["muted2"])

    def _nav(self, target, idx):
        self._highlight(idx)
        self._clear()
        if target == "_home":
            self._home_page()
        else:
            mod_name, cls_name = target.rsplit(".", 1)
            try:
                mod = importlib.import_module(f"modules.{mod_name}")
                cls = getattr(mod, cls_name)
                cls(self.main, self.user)
            except Exception as e:
                self._placeholder(f"{cls_name} — Error: {e}")

    def _placeholder(self, msg):
        ctk.CTkLabel(self.main, text=msg,
                     font=ctk.CTkFont("Segoe UI",14),
                     text_color=C["muted2"],
                     justify="center").place(relx=0.5, rely=0.5, anchor="center")

    def _home_page(self):
        scroll = ctk.CTkScrollableFrame(self.main, fg_color="transparent")
        scroll.grid(sticky="nsew", padx=24, pady=16)
        scroll.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(scroll,
                     text=f"Welcome back, {self.user['full_name']} 👋",
                     font=ctk.CTkFont("Segoe UI",22,"bold"),
                     text_color=C["text"]).grid(sticky="w", pady=(0,4))
        ctk.CTkLabel(scroll, text="Smart Campus AI  ·  All modules overview",
                     font=ctk.CTkFont("Segoe UI",13),
                     text_color=C["muted2"]).grid(sticky="w", pady=(0,20))

        # Stats
        stats = get_attendance_stats()
        sf = ctk.CTkFrame(scroll, fg_color="transparent")
        sf.grid(sticky="ew", pady=(0,20))
        for i in range(4): sf.grid_columnconfigure(i, weight=1)
        for i, (icon, lbl, val, col) in enumerate([
            ("📋", "Total Attendance",  str(stats["total"]),           C["accent"]),
            ("📅", "Today's Records",   str(stats["today"]),           C["green"]),
            ("👥", "Unique Students",   str(stats["unique_students"]), C["teal"]),
            ("🤖", "AI Modules Active", "8",                           C["purple"]),
        ]):
            card = ctk.CTkFrame(sf, fg_color=C["card"], corner_radius=12,
                                border_width=1, border_color=C["border"])
            card.grid(row=0, column=i, padx=6, sticky="ew")
            ctk.CTkLabel(card, text=icon,
                         font=ctk.CTkFont("Segoe UI Emoji",28)).grid(pady=(14,4))
            ctk.CTkLabel(card, text=val,
                         font=ctk.CTkFont("Segoe UI",24,"bold"),
                         text_color=col).grid()
            ctk.CTkLabel(card, text=lbl,
                         font=ctk.CTkFont("Segoe UI",10),
                         text_color=C["muted2"]).grid(pady=(2,14))

        ctk.CTkLabel(scroll, text="Modules",
                     font=ctk.CTkFont("Segoe UI",15,"bold"),
                     text_color=C["text"]).grid(sticky="w", pady=(0,10))

        mf = ctk.CTkFrame(scroll, fg_color="transparent")
        mf.grid(sticky="ew")
        for i in range(4): mf.grid_columnconfigure(i, weight=1)

        modules = [
            ("👁",  "Face Recognition",   "Enroll & train student faces",       C["teal"],   1),
            ("📋",  "AI Attendance",       "Auto-mark via live camera",          C["accent"], 2),
            ("😊",  "Emotion Detection",   "Real-time emotion analysis",         C["amber"],  3),
            ("🧠",  "NeuroMirror AI",      "Classroom engagement dashboard",     C["purple"], 4),
            ("📅",  "Study Planner",       "AI-generated study schedules",       C["green"],  5),
            ("📄",  "Doc Summarizer",      "NLP key-point extraction",           C["pink"],   6),
            ("📑",  "Resume Screener",     "AI-ranked resume shortlisting",      C["amber"],  7),
            ("⚙",   "Admin Panel",         "Full data management & control",     C["red"],    8),
        ]
        for i, (icon, title, desc, col, idx) in enumerate(modules):
            r, c_idx = divmod(i, 4)
            card = ctk.CTkFrame(mf, fg_color=C["card"], corner_radius=12,
                                border_width=1, border_color=C["border"],
                                cursor="hand2")
            card.grid(row=r, column=c_idx, padx=6, pady=6, sticky="ew")
            inn = ctk.CTkFrame(card, fg_color="transparent")
            inn.pack(fill="both", expand=True, padx=16, pady=16)
            ctk.CTkLabel(inn, text=icon,
                         font=ctk.CTkFont("Segoe UI Emoji",28)).pack(anchor="w")
            ctk.CTkLabel(inn, text=title,
                         font=ctk.CTkFont("Segoe UI",13,"bold"),
                         text_color=col).pack(anchor="w", pady=(6,2))
            ctk.CTkLabel(inn, text=desc,
                         font=ctk.CTkFont("Segoe UI",11),
                         text_color=C["muted2"],
                         justify="left").pack(anchor="w")
            ctk.CTkButton(inn, text="Open →",
                          height=28, corner_radius=6,
                          font=ctk.CTkFont("Segoe UI",11),
                          fg_color=col, hover_color=col,
                          command=lambda t=self.NAV[idx][2], n=idx: self._nav(t, n)
                          ).pack(anchor="w", pady=(10,0))

    def _logout(self):
        if messagebox.askyesno("Logout", "Logout and return to login?"):
            self.destroy()
            self.login.deiconify()

    def _close(self):
        self.destroy()
        self.login.destroy()

if __name__ == "__main__":
    initialize_database()
    LoginWindow().mainloop()
