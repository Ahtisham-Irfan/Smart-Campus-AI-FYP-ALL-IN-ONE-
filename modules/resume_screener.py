# ============================================================
# Smart Campus AI — Module 7: Intelligent Resume Screener
# File: modules/resume_screener.py
# ============================================================

import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading, os, sys, re, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_helper import save_screening, get_screenings

COLORS = {
    "bg": "#0f1117", "card": "#1a1d2e", "card2": "#16192a",
    "accent": "#f59e0b", "success": "#10b981", "warning": "#f59e0b",
    "danger": "#ef4444", "text": "#f1f5f9", "muted": "#94a3b8",
    "teal": "#06b6d4", "purple": "#7c3aed",
}

# Comprehensive skill dictionary
SKILL_KEYWORDS = {
    "Programming":   ["python", "java", "c++", "c#", "javascript", "typescript",
                      "php", "ruby", "go", "kotlin", "swift", "scala", "r"],
    "Web":           ["html", "css", "react", "angular", "vue", "django", "flask",
                      "node.js", "nodejs", "express", "bootstrap", "tailwind"],
    "Database":      ["sql", "mysql", "postgresql", "mongodb", "sqlite", "oracle",
                      "redis", "firebase", "nosql", "database"],
    "AI/ML":         ["machine learning", "deep learning", "tensorflow", "pytorch",
                      "scikit-learn", "nlp", "computer vision", "neural networks",
                      "pandas", "numpy", "opencv", "keras"],
    "DevOps":        ["docker", "kubernetes", "git", "github", "ci/cd", "jenkins",
                      "aws", "azure", "gcp", "linux", "bash"],
    "Soft Skills":   ["leadership", "communication", "teamwork", "problem solving",
                      "critical thinking", "management", "collaboration"],
}

EDUCATION_KEYWORDS = ["bachelor", "master", "phd", "bs", "ms", "bsc", "msc",
                       "degree", "university", "college", "diploma", "cgpa", "gpa"]

EXPERIENCE_KEYWORDS = ["experience", "internship", "project", "worked", "developed",
                        "designed", "implemented", "managed", "led", "built", "created"]


class ResumeScreenerModule(ctk.CTkFrame):
    def __init__(self, parent, user):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.user    = user
        self.resumes = []   # list of (filename, text) tuples
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(16, 8))
        ctk.CTkLabel(hdr, text="📑  Intelligent Resume Screener",
                     font=ctk.CTkFont("Segoe UI", 20, "bold"),
                     text_color=COLORS["accent"]).pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=8)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        # ── Left: Controls
        left = ctk.CTkScrollableFrame(body, fg_color=COLORS["card"],
                                      corner_radius=12, border_width=1,
                                      border_color="#2a2d40")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(left, text="Job Criteria",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=COLORS["text"]).pack(padx=16, pady=(16, 8), anchor="w")

        # Job Title
        ctk.CTkLabel(left, text="Job Title *",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.job_title_var = ctk.StringVar(value="Software Engineer")
        ctk.CTkEntry(left, textvariable=self.job_title_var, height=34,
                     font=ctk.CTkFont("Segoe UI", 12),
                     fg_color="#0d0f1a", corner_radius=8).pack(padx=16, pady=(4, 10), fill="x")

        # Required Skills
        ctk.CTkLabel(left, text="Required Skills (comma separated)",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.skills_var = ctk.StringVar(value="Python, Machine Learning, SQL, Django, Git")
        ctk.CTkEntry(left, textvariable=self.skills_var, height=34,
                     font=ctk.CTkFont("Segoe UI", 12),
                     fg_color="#0d0f1a", corner_radius=8).pack(padx=16, pady=(4, 10), fill="x")

        # Job Description
        ctk.CTkLabel(left, text="Job Description",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.jd_box = ctk.CTkTextbox(left, height=80,
                                     font=ctk.CTkFont("Segoe UI", 11),
                                     fg_color="#0d0f1a", border_width=1,
                                     border_color="#2a2d40")
        self.jd_box.pack(padx=16, pady=(4, 10), fill="x")
        self.jd_box.insert("end",
                           "Looking for a passionate developer with strong Python skills, "
                           "experience in machine learning, and good communication skills.")

        # Minimum experience
        ctk.CTkLabel(left, text="Min. Years of Experience",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.exp_var = ctk.IntVar(value=1)
        exp_row = ctk.CTkFrame(left, fg_color="transparent")
        exp_row.pack(padx=16, fill="x", pady=(4, 10))
        ctk.CTkSlider(exp_row, from_=0, to=10, variable=self.exp_var,
                      command=lambda v: self.exp_lbl.configure(text=f"{int(v)} yrs"),
                      button_color=COLORS["accent"]).pack(side="left", fill="x", expand=True)
        self.exp_lbl = ctk.CTkLabel(exp_row, text="1 yrs", width=50,
                                    font=ctk.CTkFont("Segoe UI", 12),
                                    text_color=COLORS["accent"])
        self.exp_lbl.pack(side="left", padx=(8, 0))

        # Weights
        ctk.CTkLabel(left, text="Scoring Weights",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=COLORS["text"]).pack(padx=16, pady=(8, 6), anchor="w")

        self.weights = {}
        weight_items = [("Skills Match",  "skills",  40),
                        ("Education",     "edu",     25),
                        ("Experience",    "exp",     20),
                        ("Keywords",      "kw",      15)]
        for label, key, default in weight_items:
            var = ctk.IntVar(value=default)
            self.weights[key] = var
            w_row = ctk.CTkFrame(left, fg_color="transparent")
            w_row.pack(padx=16, fill="x", pady=2)
            ctk.CTkLabel(w_row, text=f"{label}:", width=100, anchor="w",
                         font=ctk.CTkFont("Segoe UI", 11),
                         text_color=COLORS["muted"]).pack(side="left")
            ctk.CTkLabel(w_row, textvariable=var, width=30,
                         font=ctk.CTkFont("Segoe UI", 11),
                         text_color=COLORS["accent"]).pack(side="right")
            sl = ctk.CTkSlider(w_row, from_=0, to=60, variable=var,
                               button_color=COLORS["accent"], height=14)
            sl.pack(side="left", fill="x", expand=True, padx=(8, 4))

        # Resume upload
        ctk.CTkFrame(left, height=1, fg_color="#2a2d40").pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(left, text="Upload Resumes",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=COLORS["text"]).pack(padx=16, anchor="w", pady=(0, 8))

        ctk.CTkButton(left, text="📂  Add Resumes (PDF/TXT)",
                      height=36, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 12),
                      fg_color="#2a2d40",
                      command=self._add_resumes).pack(padx=16, fill="x", pady=(0, 6))

        self.resume_count_lbl = ctk.CTkLabel(left, text="No resumes loaded",
                                             font=ctk.CTkFont("Segoe UI", 11),
                                             text_color=COLORS["muted"])
        self.resume_count_lbl.pack(padx=16, anchor="w", pady=(0, 8))

        # Screen button
        self.screen_btn = ctk.CTkButton(left, text="🔍  Screen & Rank Resumes",
                                        height=42, corner_radius=10,
                                        font=ctk.CTkFont("Segoe UI", 13, "bold"),
                                        fg_color=COLORS["accent"],
                                        text_color="#1a1a1a",
                                        command=self._screen)
        self.screen_btn.pack(padx=16, pady=(0, 16), fill="x")

        # ── Right: Results
        right = ctk.CTkFrame(body, fg_color=COLORS["card"],
                             corner_radius=12, border_width=1,
                             border_color="#2a2d40")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        out_hdr = ctk.CTkFrame(right, fg_color="transparent")
        out_hdr.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(out_hdr, text="Screening Results — Ranked",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=COLORS["text"]).pack(side="left")
        ctk.CTkButton(out_hdr, text="📥  Export CSV",
                      width=100, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color="#2a2d40",
                      command=self._export_results).pack(side="right")

        self.results_scroll = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.results_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        ctk.CTkLabel(self.results_scroll,
                     text="📑  Upload resumes and click 'Screen & Rank' to see ranked results.\n\n"
                          "Supports PDF and TXT formats.\nMultiple resumes can be uploaded at once.",
                     font=ctk.CTkFont("Segoe UI", 13),
                     text_color=COLORS["muted"],
                     justify="center").pack(pady=40)

    # ── Logic ────────────────────────────────────────────────
    def _add_resumes(self):
        paths = filedialog.askopenfilenames(
            title="Select Resumes",
            filetypes=[("PDF/TXT files", "*.pdf *.txt"), ("All files", "*.*")]
        )
        if not paths:
            return
        for path in paths:
            text = self._extract_text(path)
            if text:
                fname = os.path.basename(path)
                self.resumes.append((fname, text))
        n = len(self.resumes)
        self.resume_count_lbl.configure(
            text=f"✅  {n} resume{'s' if n>1 else ''} loaded",
            text_color=COLORS["success"])

    def _extract_text(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    return "\n".join(p.extract_text() or "" for p in pdf.pages)
            except:
                try:
                    import fitz
                    doc = fitz.open(path)
                    return "\n".join(p.get_text() for p in doc)
                except:
                    return ""
        else:
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except:
                return ""

    def _screen(self):
        if not self.resumes:
            messagebox.showwarning("No Resumes",
                                   "Please upload at least one resume first.")
            return
        self.screen_btn.configure(state="disabled", text="⏳  Screening…")
        threading.Thread(target=self._do_screen, daemon=True).start()

    def _do_screen(self):
        job_title    = self.job_title_var.get().strip()
        req_skills   = [s.strip().lower() for s in self.skills_var.get().split(",")]
        jd_text      = self.jd_box.get("1.0", "end").strip().lower()
        min_exp      = int(self.exp_var.get())

        results = []
        for fname, text in self.resumes:
            r = self._analyze_resume(fname, text, req_skills, jd_text, min_exp)
            results.append(r)

        # Rank by score
        results.sort(key=lambda x: x["score"], reverse=True)
        for i, r in enumerate(results):
            r["rank"] = i + 1

        self.screening_results = results
        self.after(0, lambda: self._show_results(results, job_title))

    def _analyze_resume(self, fname, text, req_skills, jd_text, min_exp):
        text_lower = text.lower()
        result = {"filename": fname, "text": text}

        # ── Extract name (first non-empty line heuristic)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        result["name"] = lines[0][:40] if lines else fname.replace(".pdf", "")

        # ── Skills match
        found_skills = []
        for skill in req_skills:
            if skill in text_lower:
                found_skills.append(skill)
        # Also detect from SKILL_KEYWORDS
        all_detected = []
        for cat, kws in SKILL_KEYWORDS.items():
            for kw in kws:
                if kw.lower() in text_lower:
                    all_detected.append(kw)

        skill_score = (len(found_skills) / max(len(req_skills), 1)) * 100
        result["matched_skills"] = found_skills
        result["all_skills"]     = list(set(all_detected))[:15]

        # ── Education
        edu_matches = sum(1 for kw in EDUCATION_KEYWORDS if kw in text_lower)
        edu_score   = min(100, edu_matches * 15)
        result["education"] = self._extract_edu(text)

        # ── Experience
        exp_matches = sum(1 for kw in EXPERIENCE_KEYWORDS if kw in text_lower)
        years_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience', text_lower)
        years_found = int(years_match.group(1)) if years_match else 0
        exp_score   = min(100, (exp_matches * 8) + (years_found * 10))
        result["experience"] = f"{years_found} yrs" if years_found else "Not specified"

        # ── JD keyword overlap
        jd_words  = set(re.findall(r'\b\w+\b', jd_text)) - {"the","a","an","is","in","of"}
        res_words = set(re.findall(r'\b\w+\b', text_lower))
        kw_score  = (len(jd_words & res_words) / max(len(jd_words), 1)) * 100

        # ── Weighted total
        w = {k: v.get() for k, v in self.weights.items()}
        total_w = sum(w.values()) or 100
        score   = (
            skill_score * w["skills"] +
            edu_score   * w["edu"]    +
            exp_score   * w["exp"]    +
            kw_score    * w["kw"]
        ) / total_w

        result["score"]       = round(score, 1)
        result["skill_score"] = round(skill_score, 1)
        result["edu_score"]   = round(edu_score, 1)
        result["exp_score"]   = round(exp_score, 1)
        result["kw_score"]    = round(kw_score, 1)

        return result

    def _extract_edu(self, text):
        patterns = [
            r"(bachelor[s']?\s+(?:of\s+)?(?:science|arts|engineering|computer)[^,\n]*)",
            r"(master[s']?\s+(?:of\s+)?(?:science|arts|engineering)[^,\n]*)",
            r"(phd[^,\n]*)",
            r"(b\.?s\.?c?[^,\n]{0,30})",
            r"(m\.?s\.?c?[^,\n]{0,30})",
        ]
        for pat in patterns:
            m = re.search(pat, text.lower())
            if m:
                return m.group(1).strip().title()[:60]
        return "Not specified"

    def _show_results(self, results, job_title):
        for w in self.results_scroll.winfo_children():
            w.destroy()

        # Summary bar
        top_score = results[0]["score"] if results else 0
        short = sum(1 for r in results if r["score"] >= 60)

        sum_row = ctk.CTkFrame(self.results_scroll, fg_color="#0d0f1a", corner_radius=8)
        sum_row.pack(fill="x", pady=(0, 12))
        for label, val, color in [
            (f"{len(results)} Screened", f"{len(results)}", COLORS["teal"]),
            (f"Shortlisted (≥60%)", str(short), COLORS["success"]),
            ("Top Score", f"{top_score}%", COLORS["accent"]),
            ("Job Title", job_title[:16], COLORS["purple"]),
        ]:
            fr = ctk.CTkFrame(sum_row, fg_color="transparent")
            fr.pack(side="left", expand=True, pady=8)
            ctk.CTkLabel(fr, text=val,
                         font=ctk.CTkFont("Segoe UI", 18, "bold"),
                         text_color=color).pack()
            ctk.CTkLabel(fr, text=label,
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=COLORS["muted"]).pack()

        # Result cards
        for r in results:
            rank  = r["rank"]
            score = r["score"]
            color = (COLORS["success"] if score >= 70
                     else COLORS["warning"] if score >= 50
                     else COLORS["danger"])
            rank_color = (COLORS["accent"] if rank == 1
                          else COLORS["success"] if rank == 2
                          else COLORS["teal"])

            card = ctk.CTkFrame(self.results_scroll, fg_color=COLORS["card"],
                                corner_radius=10, border_width=1,
                                border_color="#2a2d40")
            card.pack(fill="x", pady=4)

            # Top row
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=16, pady=(12, 6))

            # Rank badge
            badge = ctk.CTkFrame(top, fg_color=rank_color, corner_radius=6, width=40)
            badge.pack(side="left", padx=(0, 10))
            ctk.CTkLabel(badge, text=f"#{rank}",
                         font=ctk.CTkFont("Segoe UI", 14, "bold"),
                         text_color="#0f1117").pack(padx=8, pady=4)

            name_col = ctk.CTkFrame(top, fg_color="transparent")
            name_col.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(name_col, text=r["name"],
                         font=ctk.CTkFont("Segoe UI", 13, "bold"),
                         text_color=COLORS["text"]).pack(anchor="w")
            ctk.CTkLabel(name_col, text=r["filename"],
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=COLORS["muted"]).pack(anchor="w")

            # Score badge
            score_badge = ctk.CTkFrame(top, fg_color="#0d0f1a", corner_radius=8)
            score_badge.pack(side="right")
            ctk.CTkLabel(score_badge, text=f"{score}%",
                         font=ctk.CTkFont("Segoe UI", 18, "bold"),
                         text_color=color).pack(padx=14, pady=8)

            # Score bar
            bar_row = ctk.CTkFrame(card, fg_color="transparent")
            bar_row.pack(fill="x", padx=16, pady=(0, 8))
            bar = ctk.CTkProgressBar(bar_row, height=8, corner_radius=4,
                                     progress_color=color, fg_color="#0d0f1a")
            bar.pack(fill="x")
            bar.set(score / 100)

            # Detail row
            detail = ctk.CTkFrame(card, fg_color="transparent")
            detail.pack(fill="x", padx=16, pady=(0, 8))
            for label, val in [("Skills", f"{r['skill_score']}%"),
                                ("Education", f"{r['edu_score']}%"),
                                ("Experience", r["experience"]),
                                ("Keywords", f"{r['kw_score']}%")]:
                col_f = ctk.CTkFrame(detail, fg_color="#0d0f1a", corner_radius=6)
                col_f.pack(side="left", padx=4, expand=True, fill="x")
                ctk.CTkLabel(col_f, text=val,
                             font=ctk.CTkFont("Segoe UI", 12, "bold"),
                             text_color=COLORS["accent"]).pack(pady=(6, 2))
                ctk.CTkLabel(col_f, text=label,
                             font=ctk.CTkFont("Segoe UI", 9),
                             text_color=COLORS["muted"]).pack(pady=(0, 6))

            # Skills tags
            if r["matched_skills"]:
                tags_row = ctk.CTkFrame(card, fg_color="transparent")
                tags_row.pack(fill="x", padx=16, pady=(0, 12))
                ctk.CTkLabel(tags_row, text="✅ Matched: ",
                             font=ctk.CTkFont("Segoe UI", 10),
                             text_color=COLORS["success"]).pack(side="left")
                for skill in r["matched_skills"][:8]:
                    tag = ctk.CTkFrame(tags_row, fg_color="#0d4020", corner_radius=4)
                    tag.pack(side="left", padx=3)
                    ctk.CTkLabel(tag, text=skill,
                                 font=ctk.CTkFont("Segoe UI", 10),
                                 text_color=COLORS["success"]).pack(padx=6, pady=2)

            # Save to DB
            save_screening(
                r["name"], r["filename"],
                ", ".join(r["matched_skills"]),
                r["education"], r["experience"],
                r["score"], r["rank"]
            )

        self.screen_btn.configure(state="normal", text="🔍  Screen & Rank Resumes")

    def _export_results(self):
        if not hasattr(self, "screening_results") or not self.screening_results:
            messagebox.showinfo("No Results", "Screen resumes first.")
            return
        import csv
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"screening_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Rank", "Name", "File", "Score%", "Skills%",
                             "Education", "Experience", "Keywords%"])
                for r in self.screening_results:
                    w.writerow([r["rank"], r["name"], r["filename"], r["score"],
                                r["skill_score"], r["education"],
                                r["experience"], r["kw_score"]])
            messagebox.showinfo("Exported", f"Results saved to:\n{path}")
