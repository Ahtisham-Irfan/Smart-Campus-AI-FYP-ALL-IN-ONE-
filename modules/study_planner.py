# ============================================================
# Smart Campus AI — Module 5: AI Study Planner
# File: modules/study_planner.py
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
import threading, os, sys, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_helper import save_study_plan, get_study_plans

COLORS = {
    "bg": "#0f1117", "card": "#1a1d2e", "card2": "#16192a",
    "accent": "#10b981", "success": "#10b981", "warning": "#f59e0b",
    "danger": "#ef4444", "text": "#f1f5f9", "muted": "#94a3b8",
    "teal": "#06b6d4", "purple": "#7c3aed",
}


class StudyPlannerModule(ctk.CTkFrame):
    def __init__(self, parent, user):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.user = user
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(16, 8))
        ctk.CTkLabel(hdr, text="📅  AI Study Planner",
                     font=ctk.CTkFont("Segoe UI", 20, "bold"),
                     text_color=COLORS["accent"]).pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=8)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        # ── Left: Input Form
        left = ctk.CTkScrollableFrame(body, fg_color=COLORS["card"],
                                      corner_radius=12, border_width=1,
                                      border_color="#2a2d40")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(left, text="Study Plan Setup",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=COLORS["text"]).pack(pady=(16, 8), padx=16, anchor="w")

        # Subjects
        ctk.CTkLabel(left, text="Subjects (one per line) *",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.subjects_box = ctk.CTkTextbox(left, height=90, corner_radius=8,
                                           font=ctk.CTkFont("Segoe UI", 12),
                                           fg_color="#0d0f1a", border_width=1,
                                           border_color="#2a2d40")
        self.subjects_box.pack(padx=16, pady=(4, 10), fill="x")
        self.subjects_box.insert("end", "Data Structures\nAlgorithms\nDatabase Systems\nOOP")

        # Topics
        ctk.CTkLabel(left, text="Key Topics / Chapters *",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.topics_box = ctk.CTkTextbox(left, height=80, corner_radius=8,
                                         font=ctk.CTkFont("Segoe UI", 12),
                                         fg_color="#0d0f1a", border_width=1,
                                         border_color="#2a2d40")
        self.topics_box.pack(padx=16, pady=(4, 10), fill="x")
        self.topics_box.insert("end", "Trees, Graphs, Sorting\nDP, Greedy Algorithms\nSQL, Normalization\nInheritance, Polymorphism")

        # Study hours per day
        ctk.CTkLabel(left, text="Study Hours / Day",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.hours_var = ctk.IntVar(value=4)
        hours_row = ctk.CTkFrame(left, fg_color="transparent")
        hours_row.pack(padx=16, fill="x", pady=(4, 10))
        ctk.CTkSlider(hours_row, from_=1, to=12, variable=self.hours_var,
                      command=lambda v: self.hours_lbl.configure(text=f"{int(v)} hrs"),
                      button_color=COLORS["accent"]).pack(side="left", fill="x", expand=True)
        self.hours_lbl = ctk.CTkLabel(hours_row, text="4 hrs", width=50,
                                      font=ctk.CTkFont("Segoe UI", 12),
                                      text_color=COLORS["accent"])
        self.hours_lbl.pack(side="left", padx=(8, 0))

        # Difficulty
        ctk.CTkLabel(left, text="Difficulty Level",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.diff_var = ctk.StringVar(value="Medium")
        ctk.CTkSegmentedButton(left,
                               values=["Easy", "Medium", "Hard"],
                               variable=self.diff_var,
                               selected_color=COLORS["accent"],
                               font=ctk.CTkFont("Segoe UI", 12)).pack(padx=16, pady=(4, 10), fill="x")

        # Deadline
        ctk.CTkLabel(left, text="Exam Deadline (days from today)",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.days_var = ctk.IntVar(value=14)
        days_row = ctk.CTkFrame(left, fg_color="transparent")
        days_row.pack(padx=16, fill="x", pady=(4, 10))
        ctk.CTkSlider(days_row, from_=3, to=60, variable=self.days_var,
                      command=lambda v: self.days_lbl.configure(text=f"{int(v)} days"),
                      button_color=COLORS["warning"]).pack(side="left", fill="x", expand=True)
        self.days_lbl = ctk.CTkLabel(days_row, text="14 days", width=60,
                                     font=ctk.CTkFont("Segoe UI", 12),
                                     text_color=COLORS["warning"])
        self.days_lbl.pack(side="left", padx=(8, 0))

        # Goals
        ctk.CTkLabel(left, text="Learning Goals (optional)",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(padx=16, anchor="w")
        self.goals_var = ctk.StringVar(value="Score 90%+ in final exams")
        ctk.CTkEntry(left, textvariable=self.goals_var, height=34,
                     font=ctk.CTkFont("Segoe UI", 12),
                     fg_color="#0d0f1a", corner_radius=8).pack(padx=16, pady=(4, 16), fill="x")

        # Generate button
        self.gen_btn = ctk.CTkButton(left, text="🤖  Generate AI Study Plan",
                                     height=42, corner_radius=10,
                                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                                     fg_color=COLORS["accent"],
                                     command=self._generate)
        self.gen_btn.pack(padx=16, pady=(0, 8), fill="x")

        self.status_lbl = ctk.CTkLabel(left, text="",
                                       font=ctk.CTkFont("Segoe UI", 11),
                                       text_color=COLORS["muted"],
                                       wraplength=260)
        self.status_lbl.pack(padx=16, pady=(0, 16))

        # ── Right: Output
        right = ctk.CTkFrame(body, fg_color=COLORS["card"],
                             corner_radius=12, border_width=1,
                             border_color="#2a2d40")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        out_hdr = ctk.CTkFrame(right, fg_color="transparent")
        out_hdr.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(out_hdr, text="Generated Study Plan",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=COLORS["text"]).pack(side="left")
        ctk.CTkButton(out_hdr, text="💾  Save",
                      width=80, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color=COLORS["teal"],
                      command=self._save_plan).pack(side="right", padx=(0, 8))
        ctk.CTkButton(out_hdr, text="📥  Export TXT",
                      width=100, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color="#2a2d40",
                      command=self._export_txt).pack(side="right")

        self.output_box = ctk.CTkTextbox(right, font=ctk.CTkFont("Consolas", 12),
                                         fg_color="#0d0f1a", border_width=1,
                                         border_color="#2a2d40", wrap="word")
        self.output_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.output_box.insert("end", "📅  Your AI-generated study plan will appear here.\n\n"
                               "Fill in the form on the left and click\n'Generate AI Study Plan'.")
        self.output_box.configure(state="disabled")

    # ── Logic ────────────────────────────────────────────────
    def _generate(self):
        subjects = self.subjects_box.get("1.0", "end").strip()
        topics   = self.topics_box.get("1.0", "end").strip()
        if not subjects:
            messagebox.showwarning("Input Required", "Please enter at least one subject.")
            return

        self.gen_btn.configure(state="disabled", text="⏳  Generating…")
        self.status_lbl.configure(text="AI is building your plan…", text_color=COLORS["warning"])
        threading.Thread(target=self._do_generate, args=(subjects, topics), daemon=True).start()

    def _do_generate(self, subjects_raw, topics_raw):
        subjects = [s.strip() for s in subjects_raw.split("\n") if s.strip()]
        topics   = [t.strip() for t in topics_raw.split("\n") if t.strip()]
        days     = int(self.days_var.get())
        hours    = int(self.hours_var.get())
        diff     = self.diff_var.get()
        goals    = self.goals_var.get().strip()
        deadline = (datetime.now() + timedelta(days=days)).strftime("%B %d, %Y")

        plan = self._build_plan(subjects, topics, days, hours, diff, goals, deadline)
        self.current_plan = plan

        self.after(0, lambda: self._show_plan(plan))

    def _build_plan(self, subjects, topics, days, hours, diff, goals, deadline):
        lines = []
        lines.append("=" * 60)
        lines.append("       SMART CAMPUS AI — PERSONALIZED STUDY PLAN")
        lines.append("=" * 60)
        lines.append(f"  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"  Deadline  : {deadline}  ({days} days)")
        lines.append(f"  Daily hrs : {hours} hrs/day    Difficulty: {diff}")
        lines.append(f"  Goal      : {goals}")
        lines.append("=" * 60)
        lines.append("")

        # Distribute topics across subjects
        topic_map = {}
        for i, subj in enumerate(subjects):
            topic_map[subj] = topics[i] if i < len(topics) else "Core concepts"

        # Effort multiplier
        effort = {"Easy": 0.7, "Medium": 1.0, "Hard": 1.4}.get(diff, 1.0)

        # ── Week-by-week plan
        week = 1
        day  = 1
        subj_idx = 0

        lines.append("  📚  WEEK-BY-WEEK STUDY SCHEDULE")
        lines.append("-" * 60)

        while day <= days:
            lines.append(f"\n  📅  Week {week} (Days {day}–{min(day+6, days)})")
            for d in range(7):
                if day > days:
                    break
                date_str = (datetime.now() + timedelta(days=day-1)).strftime("%a %b %d")
                subj = subjects[subj_idx % len(subjects)]
                topic= topic_map.get(subj, "Revision")

                # Session breakdown
                session_hrs = round(hours * effort, 1)
                session1    = round(session_hrs * 0.6, 1)
                session2    = round(session_hrs * 0.4, 1)

                lines.append(f"\n  Day {day:>2} │ {date_str}")
                lines.append(f"         ├── Subject : {subj}")
                lines.append(f"         ├── Topic   : {topic}")
                lines.append(f"         ├── Morning : {session1} hrs — Study new concepts")
                lines.append(f"         ├── Evening : {session2} hrs — Practice & exercises")
                lines.append(f"         └── Review  : Flash cards + previous notes (20 min)")

                subj_idx += 1
                day      += 1
            week += 1

        # ── Study tips
        lines.append("\n\n" + "=" * 60)
        lines.append("  🧠  STUDY TECHNIQUES (Tailored for " + diff + " level)")
        lines.append("-" * 60)

        techniques = {
            "Easy":   ["Active Recall: re-read and summarize in own words",
                       "Spaced Repetition: review every 3 days",
                       "Mind maps for concept connections",
                       "Practice problems after each topic"],
            "Medium": ["Pomodoro: 25 min study + 5 min break",
                       "Feynman Technique: explain topics simply",
                       "Cornell Notes method",
                       "2 full past papers per week"],
            "Hard":   ["Deep Work: 90-min uninterrupted sessions",
                       "Interleaved practice across subjects",
                       "Teaching others to solidify concepts",
                       "Error analysis on all wrong answers"],
        }
        for tip in techniques.get(diff, techniques["Medium"]):
            lines.append(f"  • {tip}")

        # ── Revision plan
        lines.append("\n\n  📝  FINAL REVISION STRATEGY")
        lines.append("-" * 60)
        rev_days = max(2, days // 5)
        lines.append(f"  • Last {rev_days} days before exam: Full revision mode")
        lines.append(f"  • Day -3 : Mock exam under timed conditions")
        lines.append(f"  • Day -2 : Focus on weak areas only")
        lines.append(f"  • Day -1 : Light review + rest (no all-nighters!)")
        lines.append(f"  • Exam day: Arrive early, stay calm, trust your prep")

        # ── Summary
        total_hours = days * hours
        lines.append("\n\n" + "=" * 60)
        lines.append("  📊  PLAN SUMMARY")
        lines.append("-" * 60)
        lines.append(f"  Total subjects : {len(subjects)}")
        lines.append(f"  Total days     : {days}")
        lines.append(f"  Total hours    : {total_hours} hrs")
        lines.append(f"  Hours/subject  : {round(total_hours / max(len(subjects),1), 1)} hrs")
        lines.append(f"  Difficulty     : {diff}")
        lines.append(f"  Goal           : {goals}")
        lines.append("=" * 60)
        lines.append("\n  ✅  Plan generated by Smart Campus AI")
        lines.append(f"     University of Agriculture, Faisalabad | {datetime.now().strftime('%Y')}")

        return "\n".join(lines)

    def _show_plan(self, plan):
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", plan)
        self.output_box.configure(state="disabled")
        self.gen_btn.configure(state="normal", text="🤖  Generate AI Study Plan")
        self.status_lbl.configure(text="✅  Plan generated!", text_color=COLORS["success"])

    def _save_plan(self):
        if not hasattr(self, "current_plan"):
            messagebox.showinfo("No Plan", "Generate a plan first.")
            return
        subjects = self.subjects_box.get("1.0", "end").strip()[:200]
        deadline = str((datetime.now() + timedelta(days=int(self.days_var.get()))).date())
        save_study_plan(self.user.get("username", "student"),
                        f"Study Plan {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        subjects, deadline, self.current_plan)
        messagebox.showinfo("Saved", "Study plan saved to database!")

    def _export_txt(self):
        if not hasattr(self, "current_plan"):
            messagebox.showinfo("No Plan", "Generate a plan first.")
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"study_plan_{datetime.now().strftime('%Y%m%d')}.txt",
            filetypes=[("Text files", "*.txt")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.current_plan)
            messagebox.showinfo("Exported", f"Study plan saved to:\n{path}")
