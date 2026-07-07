# ============================================================
# Smart Campus AI — Module 6: Document Summarizer
# File: modules/doc_summarizer.py
# ============================================================

import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading, os, sys, re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_helper import save_summary, get_summaries

COLORS = {
    "bg": "#0f1117", "card": "#1a1d2e", "card2": "#16192a",
    "accent": "#ec4899", "success": "#10b981", "warning": "#f59e0b",
    "danger": "#ef4444", "text": "#f1f5f9", "muted": "#94a3b8",
    "teal": "#06b6d4",
}


class DocSummarizerModule(ctk.CTkFrame):
    def __init__(self, parent, user):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.user = user
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(16, 8))
        ctk.CTkLabel(hdr, text="📄  Document Summarizer — NLP Powered",
                     font=ctk.CTkFont("Segoe UI", 20, "bold"),
                     text_color=COLORS["accent"]).pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=8)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # ── Left: Input
        left = ctk.CTkFrame(body, fg_color=COLORS["card"],
                            corner_radius=12, border_width=1,
                            border_color="#2a2d40")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(2, weight=1)
        left.columnconfigure(0, weight=1)

        # Controls
        ctrl = ctk.CTkFrame(left, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=16, pady=12)

        ctk.CTkLabel(ctrl, text="Input Document",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=COLORS["text"]).pack(side="left")

        ctk.CTkButton(ctrl, text="📂  Load PDF",
                      width=100, height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color="#2a2d40",
                      command=self._load_pdf).pack(side="right", padx=(4, 0))
        ctk.CTkButton(ctrl, text="📄  Load TXT",
                      width=100, height=32, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color="#2a2d40",
                      command=self._load_txt).pack(side="right", padx=(4, 0))

        # Settings bar
        sbar = ctk.CTkFrame(left, fg_color="transparent")
        sbar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        ctk.CTkLabel(sbar, text="Method:",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(side="left", padx=(0, 6))
        self.method_var = ctk.StringVar(value="Extractive (Fast)")
        ctk.CTkOptionMenu(sbar,
                          values=["Extractive (Fast)", "Abstractive (AI)", "Bullet Points", "Key Phrases"],
                          variable=self.method_var,
                          width=170, height=30,
                          font=ctk.CTkFont("Segoe UI", 11),
                          fg_color="#0d0f1a",
                          button_color=COLORS["accent"]).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(sbar, text="Length:",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["muted"]).pack(side="left", padx=(0, 6))
        self.length_var = ctk.StringVar(value="Medium")
        ctk.CTkSegmentedButton(sbar, values=["Short", "Medium", "Long"],
                               variable=self.length_var,
                               selected_color=COLORS["accent"],
                               font=ctk.CTkFont("Segoe UI", 11)).pack(side="left")

        # Input textbox
        self.input_box = ctk.CTkTextbox(left, font=ctk.CTkFont("Segoe UI", 12),
                                        fg_color="#0d0f1a", border_width=1,
                                        border_color="#2a2d40", wrap="word")
        self.input_box.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self.input_box.insert("end",
                              "Paste your document text here, or use the Load PDF / Load TXT buttons above.\n\n"
                              "The AI will extract key points, main ideas, and important information from your document.")

        # Word count
        self.wc_var = ctk.StringVar(value="Words: 0")
        wc_row = ctk.CTkFrame(left, fg_color="transparent")
        wc_row.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 4))
        ctk.CTkLabel(wc_row, textvariable=self.wc_var,
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=COLORS["muted"]).pack(side="left")

        # Summarize button
        self.sum_btn = ctk.CTkButton(left, text="⚡  Summarize Document",
                                     height=42, corner_radius=10,
                                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                                     fg_color=COLORS["accent"],
                                     command=self._summarize)
        self.sum_btn.grid(row=4, column=0, padx=16, pady=(0, 16), sticky="ew")
        self.input_box.bind("<KeyRelease>", self._update_wc)

        # ── Right: Output
        right = ctk.CTkFrame(body, fg_color=COLORS["card"],
                             corner_radius=12, border_width=1,
                             border_color="#2a2d40")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        out_hdr = ctk.CTkFrame(right, fg_color="transparent")
        out_hdr.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(out_hdr, text="Summary Output",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=COLORS["text"]).pack(side="left")
        ctk.CTkButton(out_hdr, text="💾  Save",
                      width=70, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color=COLORS["teal"],
                      command=self._save_sum).pack(side="right", padx=(4, 0))
        ctk.CTkButton(out_hdr, text="📋  Copy",
                      width=70, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color="#2a2d40",
                      command=self._copy_sum).pack(side="right", padx=(4, 0))
        ctk.CTkButton(out_hdr, text="📥  TXT",
                      width=70, height=30, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color="#2a2d40",
                      command=self._export_sum).pack(side="right")

        # Stats row
        self.stats_row = ctk.CTkFrame(right, fg_color="#0d0f1a", corner_radius=8)
        self.stats_row.pack(fill="x", padx=16, pady=(0, 8))
        self.orig_wc_lbl  = self._mini_stat(self.stats_row, "0", "Original Words")
        self.sum_wc_lbl   = self._mini_stat(self.stats_row, "0", "Summary Words")
        self.ratio_lbl    = self._mini_stat(self.stats_row, "—",  "Compression")
        self.method_lbl   = self._mini_stat(self.stats_row, "—",  "Method")

        self.output_box = ctk.CTkTextbox(right, font=ctk.CTkFont("Segoe UI", 13),
                                         fg_color="#0d0f1a", border_width=1,
                                         border_color="#2a2d40", wrap="word")
        self.output_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.output_box.insert("end", "📝  Your document summary will appear here.")
        self.output_box.configure(state="disabled")

    def _mini_stat(self, parent, value, label):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", expand=True, padx=8, pady=8)
        lbl = ctk.CTkLabel(frame, text=value,
                           font=ctk.CTkFont("Segoe UI", 16, "bold"),
                           text_color=COLORS["accent"])
        lbl.pack()
        ctk.CTkLabel(frame, text=label,
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=COLORS["muted"]).pack()
        return lbl

    def _update_wc(self, event=None):
        text = self.input_box.get("1.0", "end").strip()
        wc   = len(text.split())
        self.wc_var.set(f"Words: {wc}")

    def _load_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        threading.Thread(target=self._read_pdf, args=(path,), daemon=True).start()

    def _read_pdf(self, path):
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
            self.after(0, lambda: self._set_input(text))
        except ImportError:
            try:
                import fitz  # PyMuPDF
                doc  = fitz.open(path)
                text = "\n".join(page.get_text() for page in doc)
                self.after(0, lambda: self._set_input(text))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"PDF error: {e}"))

    def _load_txt(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            with open(path, encoding="utf-8", errors="ignore") as f:
                self._set_input(f.read())

    def _set_input(self, text):
        self.input_box.delete("1.0", "end")
        self.input_box.insert("end", text.strip())
        self._update_wc()

    # ── Summarize ─────────────────────────────────────────────
    def _summarize(self):
        text = self.input_box.get("1.0", "end").strip()
        if len(text.split()) < 30:
            messagebox.showwarning("Too Short",
                                   "Please enter at least 30 words to summarize.")
            return
        self.sum_btn.configure(state="disabled", text="⏳  Summarizing…")
        threading.Thread(target=self._do_summarize, args=(text,), daemon=True).start()

    def _do_summarize(self, text):
        method  = self.method_var.get()
        length  = self.length_var.get()
        orig_wc = len(text.split())

        ratio_map = {"Short": 0.15, "Medium": 0.30, "Long": 0.45}
        target_ratio = ratio_map.get(length, 0.25)

        summary = ""

        if "Abstractive" in method:
            summary = self._abstractive_summarize(text, target_ratio)
        elif "Bullet" in method:
            summary = self._bullet_summarize(text, target_ratio)
        elif "Key Phrases" in method:
            summary = self._keyphrase_summarize(text)
        else:
            summary = self._extractive_summarize(text, target_ratio)

        sum_wc   = len(summary.split())
        ratio    = f"{round((1 - sum_wc/max(orig_wc,1))*100)}% compressed"
        self.current_summary = summary

        self.after(0, lambda: self._show_summary(summary, orig_wc, sum_wc, ratio, method))

    def _extractive_summarize(self, text, ratio):
        """TF-IDF based extractive summarization."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= 3:
            return text

        words = re.findall(r'\b\w+\b', text.lower())
        # Stop words
        stops = {"the","a","an","in","of","for","to","and","is","was","are",
                 "were","be","been","this","that","with","from","by","at","on"}
        freq = {}
        for w in words:
            if w not in stops and len(w) > 2:
                freq[w] = freq.get(w, 0) + 1

        # Score sentences
        scores = {}
        for sent in sentences:
            words_s = re.findall(r'\b\w+\b', sent.lower())
            scores[sent] = sum(freq.get(w, 0) for w in words_s if w not in stops)

        n = max(3, int(len(sentences) * ratio))
        top = sorted(scores, key=scores.get, reverse=True)[:n]
        # Keep original order
        ordered = [s for s in sentences if s in top]
        return " ".join(ordered)

    def _abstractive_summarize(self, text, ratio):
        """Use HuggingFace BART if available, else fallback."""
        try:
            from transformers import pipeline
            max_len = max(50, int(len(text.split()) * ratio))
            min_len = max(20, int(max_len * 0.5))
            summarizer = pipeline("summarization",
                                  model="facebook/bart-large-cnn",
                                  max_length=max_len, min_length=min_len)
            # Chunk if long
            words = text.split()
            if len(words) > 800:
                chunks = [" ".join(words[i:i+800]) for i in range(0, len(words), 800)]
                parts  = [summarizer(c)[0]["summary_text"] for c in chunks[:3]]
                return " ".join(parts)
            return summarizer(text)[0]["summary_text"]
        except Exception:
            return self._extractive_summarize(text, ratio)

    def _bullet_summarize(self, text, ratio):
        """Extract key sentences as bullet points."""
        base     = self._extractive_summarize(text, ratio)
        sentences= re.split(r'(?<=[.!?])\s+', base)
        bullets  = [f"• {s.strip()}" for s in sentences if s.strip()]
        return "\n".join(bullets)

    def _keyphrase_summarize(self, text):
        """Extract key noun phrases using NLTK."""
        try:
            import nltk
            from nltk.tokenize import word_tokenize
            from nltk.tag import pos_tag
            for res in ["punkt", "averaged_perceptron_tagger", "stopwords"]:
                try: nltk.download(res, quiet=True)
                except: pass
            tokens = word_tokenize(text[:3000])
            tagged = pos_tag(tokens)
            from nltk.corpus import stopwords
            stops  = set(stopwords.words("english"))
            phrases= []
            buffer = []
            for word, tag in tagged:
                if tag.startswith("NN") or tag.startswith("JJ"):
                    buffer.append(word)
                else:
                    if len(buffer) >= 2:
                        phrase = " ".join(buffer)
                        if phrase.lower() not in stops:
                            phrases.append(phrase)
                    buffer = []
            top = list(dict.fromkeys(phrases))[:30]
            result = "🔑  KEY PHRASES EXTRACTED:\n\n"
            result += "\n".join(f"  • {p}" for p in top)
            result += f"\n\n📊  Total key phrases: {len(top)}"
            return result
        except:
            return self._extractive_summarize(text, 0.25)

    def _show_summary(self, summary, orig, summ, ratio, method):
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", summary)
        self.output_box.configure(state="disabled")
        self.orig_wc_lbl.configure(text=str(orig))
        self.sum_wc_lbl.configure(text=str(summ))
        self.ratio_lbl.configure(text=ratio)
        self.method_lbl.configure(text=method.split("(")[0].strip())
        self.sum_btn.configure(state="normal", text="⚡  Summarize Document")

    def _save_sum(self):
        if not hasattr(self, "current_summary"):
            messagebox.showinfo("No Summary", "Summarize a document first.")
            return
        orig  = self.input_box.get("1.0", "end").strip()
        title = f"Summary {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        save_summary(title, orig[:1000], self.current_summary, len(self.current_summary.split()))
        messagebox.showinfo("Saved", "Summary saved to database!")

    def _copy_sum(self):
        if hasattr(self, "current_summary"):
            self.clipboard_clear()
            self.clipboard_append(self.current_summary)
            messagebox.showinfo("Copied", "Summary copied to clipboard!")

    def _export_sum(self):
        if not hasattr(self, "current_summary"):
            messagebox.showinfo("No Summary", "Summarize a document first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"summary_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            filetypes=[("Text files", "*.txt")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.current_summary)
            messagebox.showinfo("Exported", f"Summary saved to:\n{path}")
