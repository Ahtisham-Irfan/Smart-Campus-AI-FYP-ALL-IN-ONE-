# ============================================================
# Smart Campus AI v2 — Module 8: Admin Panel
# Full data management & control
# ============================================================
import customtkinter as ctk
from tkinter import messagebox
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_helper import (
    get_all_users, add_user, update_user, delete_user, change_password,
    get_all_students, delete_student, update_student,
    get_attendance, reset_attendance, get_attendance_stats,
    get_summaries, delete_summary, get_screenings, delete_screenings,
    get_study_plans, delete_study_plan, delete_emotion_logs,
)

C = {
    "bg":"#0a0c14","card":"#12151f","card2":"#0e1018","border":"#1e2235",
    "accent":"#4f8ef7","red":"#ef4444","green":"#10b981","amber":"#f59e0b",
    "teal":"#06b6d4","purple":"#7c3aed","text":"#f1f5f9","muted":"#64748b","muted2":"#94a3b8",
}


class AdminPanelModule(ctk.CTkFrame):
    def __init__(self, parent, user):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.user = user
        self._build()

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(sticky="ew", padx=24, pady=(16,8))
        ctk.CTkLabel(hdr, text="⚙  Admin Control Panel",
                     font=ctk.CTkFont("Segoe UI",20,"bold"),
                     text_color=C["red"]).pack(side="left")
        ctk.CTkLabel(hdr, text=f"Logged in as: {self.user['full_name']}",
                     font=ctk.CTkFont("Segoe UI",11),
                     text_color=C["muted2"]).pack(side="right")

        self.tabs = ctk.CTkTabview(self, fg_color=C["card"],
                                   segmented_button_selected_color=C["red"],
                                   segmented_button_fg_color=C["card2"])
        self.tabs.grid(sticky="nsew", padx=24, pady=(0,16))
        for t in ["User Management","Student Records","Attendance Data",
                  "System Data","Database Stats"]:
            self.tabs.add(t)

        self._build_users(self.tabs.tab("User Management"))
        self._build_students(self.tabs.tab("Student Records"))
        self._build_attendance(self.tabs.tab("Attendance Data"))
        self._build_sysdata(self.tabs.tab("System Data"))
        self._build_stats(self.tabs.tab("Database Stats"))

    # ─────────────────────────────────────────────────────────
    # TAB 1 — USERS
    # ─────────────────────────────────────────────────────────
    def _build_users(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Add user form
        form = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=10,
                            border_width=1, border_color=C["border"])
        form.grid(sticky="ew", pady=8)
        inner = ctk.CTkFrame(form, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(inner, text="Add New User",
                     font=ctk.CTkFont("Segoe UI",13,"bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0,10))

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")
        self.nu_vars = {}
        for lbl, key, ph, w in [
            ("Username","uname","username",120),
            ("Password","pwd","password",120),
            ("Full Name","fname","Full Name",160),
        ]:
            ctk.CTkLabel(row, text=lbl,
                         font=ctk.CTkFont("Segoe UI",10),
                         text_color=C["muted2"]).pack(side="left", padx=(0,4))
            v = ctk.StringVar()
            self.nu_vars[key] = v
            ctk.CTkEntry(row, textvariable=v, width=w, height=32,
                         placeholder_text=ph,
                         font=ctk.CTkFont("Segoe UI",11),
                         fg_color=C["card"], corner_radius=6,
                         border_color=C["border"]).pack(side="left", padx=(0,12))

        ctk.CTkLabel(row, text="Role",
                     font=ctk.CTkFont("Segoe UI",10),
                     text_color=C["muted2"]).pack(side="left", padx=(0,4))
        self.nu_role = ctk.StringVar(value="student")
        ctk.CTkOptionMenu(row, values=["student","teacher","admin"],
                          variable=self.nu_role,
                          width=100, height=32,
                          font=ctk.CTkFont("Segoe UI",11),
                          fg_color=C["card"],
                          button_color=C["accent"]).pack(side="left", padx=(0,12))
        ctk.CTkButton(row, text="➕ Add",
                      width=80, height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11,"bold"),
                      fg_color=C["green"],
                      command=self._add_user).pack(side="left")

        # Table
        th = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=4,
                          border_width=1, border_color=C["border"])
        th.grid(sticky="ew", pady=(0,4))
        for col, w in [("ID",40),("Username",120),("Full Name",180),
                       ("Role",80),("Created",120),("Actions",200)]:
            ctk.CTkLabel(th, text=col, width=w,
                         font=ctk.CTkFont("Segoe UI",10,"bold"),
                         text_color=C["muted2"]).pack(side="left", padx=6, pady=7)

        self.users_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.users_scroll.grid(sticky="nsew", pady=(0,8))
        self._load_users()

    def _load_users(self):
        for w in self.users_scroll.winfo_children():
            w.destroy()
        for i, u in enumerate(get_all_users()):
            bg  = C["card"] if i%2==0 else C["card2"]
            row = ctk.CTkFrame(self.users_scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            role_col = {"admin":C["red"],"teacher":C["green"],"student":C["teal"]}.get(u["role"],C["muted2"])
            for txt, w, tc in [
                (str(u["id"]),40,C["muted"]),
                (u["username"][:14],120,C["accent"]),
                (u["full_name"][:20],180,C["text"]),
                (u["role"],80,role_col),
                (u.get("created_at","")[:10],120,C["muted"]),
            ]:
                ctk.CTkLabel(row, text=txt, width=w,
                             font=ctk.CTkFont("Segoe UI",11),
                             text_color=tc).pack(side="left", padx=6, pady=5)
            # Buttons
            bframe = ctk.CTkFrame(row, fg_color="transparent", width=200)
            bframe.pack(side="left", padx=4)
            ctk.CTkButton(bframe, text="🔑 Pwd",
                          width=55, height=26, corner_radius=6,
                          font=ctk.CTkFont("Segoe UI",10),
                          fg_color=C["amber"], text_color="#1a1a1a",
                          command=lambda uid=u["id"]: self._change_pwd(uid)
                          ).pack(side="left", padx=2)
            if u["id"] != 1:
                ctk.CTkButton(bframe, text="🗑 Del",
                              width=55, height=26, corner_radius=6,
                              font=ctk.CTkFont("Segoe UI",10),
                              fg_color=C["red"],
                              command=lambda uid=u["id"]: self._del_user(uid)
                              ).pack(side="left", padx=2)

    def _add_user(self):
        u = self.nu_vars["uname"].get().strip()
        p = self.nu_vars["pwd"].get().strip()
        n = self.nu_vars["fname"].get().strip()
        r = self.nu_role.get()
        if not u or not p or not n:
            messagebox.showwarning("Missing", "All fields required!")
            return
        if add_user(u, p, n, r):
            for v in self.nu_vars.values(): v.set("")
            self._load_users()
            messagebox.showinfo("Added", f"User '{u}' added!")
        else:
            messagebox.showerror("Error", f"Username '{u}' already exists.")

    def _change_pwd(self, uid):
        d = ctk.CTkInputDialog(text="Enter new password:", title="Change Password")
        pwd = d.get_input()
        if pwd and pwd.strip():
            change_password(uid, pwd.strip())
            messagebox.showinfo("Updated", "Password changed!")

    def _del_user(self, uid):
        if messagebox.askyesno("Delete", f"Delete user ID {uid}?"):
            delete_user(uid)
            self._load_users()

    # ─────────────────────────────────────────────────────────
    # TAB 2 — STUDENTS
    # ─────────────────────────────────────────────────────────
    def _build_students(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=8,
                            border_width=1, border_color=C["border"])
        ctrl.grid(sticky="ew", pady=8)
        cr = ctk.CTkFrame(ctrl, fg_color="transparent")
        cr.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(cr, text="🔄 Refresh",
                      width=90, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["accent"],
                      command=self._load_students).pack(side="left", padx=(0,8))
        ctk.CTkButton(cr, text="🗑 Delete ALL Students",
                      width=160, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["red"],
                      command=self._del_all_students).pack(side="right")

        th = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=4,
                          border_width=1, border_color=C["border"])
        th.grid(sticky="ew", pady=(0,4))
        for col, w in [("Student ID",150),("Name",180),("Dept",150),
                       ("Semester",80),("Photos",70),("Trained",70),("Actions",90)]:
            ctk.CTkLabel(th, text=col, width=w,
                         font=ctk.CTkFont("Segoe UI",10,"bold"),
                         text_color=C["muted2"]).pack(side="left", padx=6, pady=7)

        self.studs_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.studs_scroll.grid(sticky="nsew", pady=(0,8))
        self._load_students()

    def _load_students(self):
        for w in self.studs_scroll.winfo_children():
            w.destroy()
        students = get_all_students()
        if not students:
            ctk.CTkLabel(self.studs_scroll, text="No students enrolled.",
                         font=ctk.CTkFont("Segoe UI",12),
                         text_color=C["muted2"]).pack(pady=20)
            return
        for i, s in enumerate(students):
            bg  = C["card"] if i%2==0 else C["card2"]
            row = ctk.CTkFrame(self.studs_scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            trained = "✅" if s.get("model_trained") else "⏳"
            for txt, w, tc in [
                (s["student_id"],         150, C["teal"]),
                (s["full_name"][:20],     180, C["text"]),
                (s.get("department","")[:16],150, C["muted2"]),
                (s.get("semester","")[:8], 80, C["muted2"]),
                (str(s.get("photo_count",0)),70, C["muted2"]),
                (trained,                  70, C["green"]),
            ]:
                ctk.CTkLabel(row, text=txt, width=w,
                             font=ctk.CTkFont("Segoe UI",11),
                             text_color=tc).pack(side="left", padx=6, pady=5)
            ctk.CTkButton(row, text="🗑",
                          width=40, height=26, corner_radius=6,
                          font=ctk.CTkFont("Segoe UI",11),
                          fg_color=C["red"],
                          command=lambda sid=s["student_id"]: self._del_student(sid)
                          ).pack(side="left", padx=4)

    def _del_student(self, sid):
        if messagebox.askyesno("Delete", f"Delete student {sid}?\nThis also removes all their attendance."):
            import shutil
            BASE = os.path.join(os.path.dirname(__file__), "..", "assets", "dataset")
            folder = os.path.join(BASE, sid)
            if os.path.exists(folder):
                shutil.rmtree(folder)
            delete_student(sid)
            self._load_students()

    def _del_all_students(self):
        if messagebox.askyesno("Delete ALL", "Delete ALL students and their data?"):
            import shutil
            BASE = os.path.join(os.path.dirname(__file__), "..", "assets", "dataset")
            for s in get_all_students():
                folder = os.path.join(BASE, s["student_id"])
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                delete_student(s["student_id"])
            self._load_students()

    # ─────────────────────────────────────────────────────────
    # TAB 3 — ATTENDANCE
    # ─────────────────────────────────────────────────────────
    def _build_attendance(self, tab):
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=8,
                            border_width=1, border_color=C["border"])
        ctrl.grid(sticky="ew", pady=8)
        cr = ctk.CTkFrame(ctrl, fg_color="transparent")
        cr.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(cr, text="🔄 Refresh",
                      width=90, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["accent"],
                      command=self._load_att).pack(side="left", padx=(0,8))
        ctk.CTkButton(cr, text="📥 Export CSV",
                      width=110, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["card"], border_width=1, border_color=C["border"],
                      command=self._export_att).pack(side="left", padx=(0,8))
        ctk.CTkButton(cr, text="🗑 Reset ALL Attendance",
                      width=170, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["red"],
                      command=self._reset_att).pack(side="right")

        th = ctk.CTkFrame(tab, fg_color=C["card2"], corner_radius=4,
                          border_width=1, border_color=C["border"])
        th.grid(sticky="ew", pady=(0,4))
        for col, w in [("ID",45),("Student ID",140),("Name",170),
                       ("Date",110),("Time",80),("Subject",150),("Actions",80)]:
            ctk.CTkLabel(th, text=col, width=w,
                         font=ctk.CTkFont("Segoe UI",10,"bold"),
                         text_color=C["muted2"]).pack(side="left", padx=6, pady=7)

        self.att_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.att_scroll.grid(sticky="nsew", pady=(0,8))
        self._load_att()

    def _load_att(self):
        for w in self.att_scroll.winfo_children():
            w.destroy()
        records = get_attendance()
        if not records:
            ctk.CTkLabel(self.att_scroll, text="No attendance records.",
                         font=ctk.CTkFont("Segoe UI",12),
                         text_color=C["muted2"]).pack(pady=20)
            return
        for i, r in enumerate(records):
            bg  = C["card"] if i%2==0 else C["card2"]
            row = ctk.CTkFrame(self.att_scroll, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            for txt, w, tc in [
                (str(r["id"]),45,C["muted"]),
                (r["student_id"][:14],140,C["teal"]),
                (r["full_name"][:18],170,C["text"]),
                (r["date"],110,C["muted2"]),
                (r["time"][:8],80,C["muted2"]),
                (r.get("subject","")[:16],150,C["muted2"]),
            ]:
                ctk.CTkLabel(row, text=txt, width=w,
                             font=ctk.CTkFont("Segoe UI",11),
                             text_color=tc).pack(side="left", padx=6, pady=4)
            ctk.CTkButton(row, text="🗑",
                          width=38, height=24, corner_radius=6,
                          font=ctk.CTkFont("Segoe UI",10),
                          fg_color=C["red"],
                          command=lambda rid=r["id"]: self._del_att_row(rid)
                          ).pack(side="left", padx=4)

    def _del_att_row(self, rid):
        from database.db_helper import delete_attendance
        delete_attendance(rid)
        self._load_att()

    def _reset_att(self):
        if messagebox.askyesno("Reset", "Delete ALL attendance records?"):
            reset_attendance()
            self._load_att()
            messagebox.showinfo("Reset", "All attendance cleared.")

    def _export_att(self):
        import csv
        from tkinter import filedialog
        records = get_attendance()
        path    = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"attendance_full_{datetime.now().strftime('%Y%m%d')}.csv",
            filetypes=[("CSV","*.csv")])
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["id","student_id","full_name",
                                                   "date","time","subject","status"])
                w.writeheader(); w.writerows(records)
            messagebox.showinfo("Exported", f"Saved:\n{path}")

    # ─────────────────────────────────────────────────────────
    # TAB 4 — SYSTEM DATA
    # ─────────────────────────────────────────────────────────
    def _build_sysdata(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=8)

        sections = [
            ("😊 Emotion Logs",      self._clear_emotions),
            ("📅 Study Plans",       self._clear_plans),
            ("📄 Summaries",         self._clear_summaries),
            ("📑 Resume Screenings", self._clear_screenings),
        ]
        for title, fn in sections:
            card = ctk.CTkFrame(scroll, fg_color=C["card2"], corner_radius=10,
                                border_width=1, border_color=C["border"])
            card.pack(fill="x", pady=6)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=12)
            ctk.CTkLabel(row, text=title,
                         font=ctk.CTkFont("Segoe UI",13,"bold"),
                         text_color=C["text"]).pack(side="left")
            ctk.CTkButton(row, text=f"🗑 Clear {title.split()[-1]}",
                          width=140, height=30, corner_radius=8,
                          font=ctk.CTkFont("Segoe UI",11),
                          fg_color=C["red"],
                          command=fn).pack(side="right")

        # Nuclear option
        nuke = ctk.CTkFrame(scroll, fg_color=C["card2"], corner_radius=10,
                            border_width=2, border_color=C["red"])
        nuke.pack(fill="x", pady=(12,0))
        in_n = ctk.CTkFrame(nuke, fg_color="transparent")
        in_n.pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(in_n, text="⚠️  Factory Reset",
                     font=ctk.CTkFont("Segoe UI",14,"bold"),
                     text_color=C["red"]).pack(anchor="w", pady=(0,4))
        ctk.CTkLabel(in_n,
                     text="Deletes ALL data: students, attendance, emotions, plans, summaries, screenings.\nThis action cannot be undone.",
                     font=ctk.CTkFont("Segoe UI",11),
                     text_color=C["muted2"], justify="left").pack(anchor="w", pady=(0,10))
        ctk.CTkButton(in_n, text="💥  FACTORY RESET — WIPE ALL DATA",
                      height=40, corner_radius=10,
                      font=ctk.CTkFont("Segoe UI",12,"bold"),
                      fg_color=C["red"], hover_color="#b91c1c",
                      command=self._factory_reset).pack(fill="x")

    def _clear_emotions(self):
        if messagebox.askyesno("Clear","Delete all emotion logs?"):
            delete_emotion_logs(); messagebox.showinfo("Done","Emotion logs cleared.")
    def _clear_plans(self):
        if messagebox.askyesno("Clear","Delete all study plans?"):
            from database.db_helper import _conn
            c = _conn(); c.execute("DELETE FROM study_plans"); c.commit(); c.close()
            messagebox.showinfo("Done","Study plans cleared.")
    def _clear_summaries(self):
        if messagebox.askyesno("Clear","Delete all summaries?"):
            from database.db_helper import _conn
            c = _conn(); c.execute("DELETE FROM summaries"); c.commit(); c.close()
            messagebox.showinfo("Done","Summaries cleared.")
    def _clear_screenings(self):
        if messagebox.askyesno("Clear","Delete all resume screenings?"):
            delete_screenings(); messagebox.showinfo("Done","Screenings cleared.")

    def _factory_reset(self):
        ans = messagebox.askyesno("FACTORY RESET",
                                  "⚠️ THIS WILL DELETE EVERYTHING!\n\n"
                                  "Students, attendance, emotions,\nplans, summaries, screenings.\n\n"
                                  "Are you absolutely sure?")
        if ans:
            import shutil
            from database.db_helper import _conn
            c = _conn()
            for tbl in ["students","attendance","emotion_logs",
                        "study_plans","summaries","resume_screenings"]:
                c.execute(f"DELETE FROM {tbl}")
            c.commit(); c.close()
            BASE = os.path.join(os.path.dirname(__file__),"..","assets","dataset")
            if os.path.exists(BASE):
                shutil.rmtree(BASE); os.makedirs(BASE)
            MODEL = os.path.join(os.path.dirname(__file__),"..","models","face_model.yml")
            if os.path.exists(MODEL): os.remove(MODEL)
            messagebox.showinfo("Reset","Factory reset complete.")

    # ─────────────────────────────────────────────────────────
    # TAB 5 — STATS
    # ─────────────────────────────────────────────────────────
    def _build_stats(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=8)

        ctk.CTkButton(scroll, text="🔄  Refresh Stats",
                      height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["accent"],
                      command=lambda: [w.destroy() for w in scroll.winfo_children()] or self._load_stats(scroll)
                      ).pack(anchor="w", pady=(0,14))
        self._load_stats(scroll)

    def _load_stats(self, scroll):
        from database.db_helper import _conn
        c    = _conn()
        tables = ["users","students","attendance","emotion_logs",
                  "study_plans","summaries","resume_screenings"]
        counts = {}
        for t in tables:
            try:
                counts[t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except:
                counts[t] = 0
        c.close()

        sf = ctk.CTkFrame(scroll, fg_color="transparent")
        sf.pack(fill="x", pady=(0,14))
        cols = 4
        for i in range(cols): sf.grid_columnconfigure(i, weight=1)

        items = list(counts.items())
        colors = [C["accent"],C["teal"],C["green"],C["amber"],C["purple"],C["red"],C["teal"]]
        for i, (tbl, cnt) in enumerate(items):
            r, cl = divmod(i, cols)
            card = ctk.CTkFrame(sf, fg_color=C["card2"], corner_radius=10,
                                border_width=1, border_color=C["border"])
            card.grid(row=r, column=cl, padx=5, pady=5, sticky="ew")
            ctk.CTkLabel(card, text=str(cnt),
                         font=ctk.CTkFont("Segoe UI",24,"bold"),
                         text_color=colors[i%len(colors)]).grid(pady=(12,2))
            ctk.CTkLabel(card, text=tbl.replace("_"," ").title(),
                         font=ctk.CTkFont("Segoe UI",10),
                         text_color=C["muted2"]).grid(pady=(0,12))

        # DB file size
        DB_PATH = os.path.join(os.path.dirname(__file__),"..","database","smart_campus.db")
        if os.path.exists(DB_PATH):
            size = os.path.getsize(DB_PATH)
            ctk.CTkLabel(scroll,
                         text=f"Database file size: {round(size/1024,1)} KB",
                         font=ctk.CTkFont("Segoe UI",12),
                         text_color=C["muted2"]).pack(anchor="w", pady=(8,4))
