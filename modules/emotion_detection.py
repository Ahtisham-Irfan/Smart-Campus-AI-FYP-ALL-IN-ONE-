# ================================================================
# Smart Campus AI v3 — Module 3: Live Face Emotion Detection
# STANDALONE — Pure real-time emotion recognition only
# Engine chain: DeepFace → FER → OpenCV fallback
# Detects: Happy Sad Angry Excited Fear Disgust Neutral
# ================================================================
import customtkinter as ctk
from tkinter import messagebox
import threading, os, sys, time, uuid, csv
from datetime import datetime
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_helper import log_emotion

C = {
    "bg":"#0a0c14","card":"#12151f","card2":"#0e1018","border":"#1e2235",
    "amber":"#f59e0b","green":"#10b981","red":"#ef4444","teal":"#06b6d4",
    "text":"#f1f5f9","muted":"#64748b","muted2":"#94a3b8",
}

EMOTIONS = {
    "happy":    {"emoji":"😊","color":"#10b981","label":"Happy"},
    "sad":      {"emoji":"😔","color":"#60a5fa","label":"Sad"},
    "angry":    {"emoji":"😡","color":"#ef4444","label":"Angry"},
    "surprise": {"emoji":"🤩","color":"#f59e0b","label":"Excited"},
    "fear":     {"emoji":"😨","color":"#7c3aed","label":"Fear"},
    "disgust":  {"emoji":"🤢","color":"#84cc16","label":"Disgust"},
    "neutral":  {"emoji":"😐","color":"#94a3b8","label":"Neutral"},
}


class EmotionDetectionModule(ctk.CTkFrame):
    def __init__(self, parent, user):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.user        = user
        self.cap         = None
        self.running     = False
        self.session_id  = ""
        self.em_counts   = {e:0 for e in EMOTIONS}
        self.total_frames= 0
        self.history     = []
        self._det_type   = None
        self._detector   = None
        self._build_ui()
        self.after(300, lambda: threading.Thread(
            target=self._init_detector, daemon=True).start())

    # ─── UI BUILD ────────────────────────────────────────────
    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(sticky="ew", padx=24, pady=(16,8))
        ctk.CTkLabel(hdr, text="😊  Live Face Emotion Detection",
                     font=ctk.CTkFont("Segoe UI",20,"bold"),
                     text_color=C["amber"]).pack(side="left")
        self.eng_lbl = ctk.CTkLabel(hdr, text="⏳  Initializing engine…",
                                     font=ctk.CTkFont("Segoe UI",11),
                                     text_color=C["muted2"])
        self.eng_lbl.pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(sticky="nsew", padx=24, pady=(0,16))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        # ── LEFT: camera
        left = ctk.CTkFrame(body, fg_color=C["card"], corner_radius=12,
                            border_width=1, border_color=C["border"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(left, fg_color="transparent")
        ctrl.grid(sticky="ew", padx=14, pady=12)
        ctk.CTkLabel(ctrl, text="Session Label:",
                     font=ctk.CTkFont("Segoe UI",12),
                     text_color=C["muted2"]).pack(side="left", padx=(0,6))
        self.lbl_var = ctk.StringVar(value="Emotion Session")
        ctk.CTkEntry(ctrl, textvariable=self.lbl_var,
                     width=160, height=34,
                     font=ctk.CTkFont("Segoe UI",12),
                     fg_color=C["card2"], corner_radius=8,
                     border_color=C["border"]).pack(side="left", padx=(0,10))
        self.s_btn = ctk.CTkButton(ctrl, text="▶  Start",
                                   width=90, height=34, corner_radius=8,
                                   font=ctk.CTkFont("Segoe UI",12,"bold"),
                                   fg_color=C["green"], command=self._start)
        self.s_btn.pack(side="left", padx=(0,6))
        self.x_btn = ctk.CTkButton(ctrl, text="■  Stop",
                                   width=80, height=34, corner_radius=8,
                                   font=ctk.CTkFont("Segoe UI",12,"bold"),
                                   fg_color=C["red"], state="disabled",
                                   command=self._stop)
        self.x_btn.pack(side="left", padx=(0,6))
        ctk.CTkButton(ctrl, text="📥 Export",
                      width=80, height=34, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI",11),
                      fg_color=C["card2"], border_width=1, border_color=C["border"],
                      command=self._export).pack(side="left")

        self.cam_lbl = ctk.CTkLabel(left,
            text="📷  Camera Preview\n\nClick ▶ Start to begin\n\n"
                 "Detects 7 emotions in real-time:\n"
                 "😊 Happy  😔 Sad  😡 Angry\n"
                 "🤩 Excited  😨 Fear  🤢 Disgust  😐 Neutral",
            font=ctk.CTkFont("Segoe UI",13), text_color=C["muted2"], justify="center")
        self.cam_lbl.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0,8))

        self.stat_lbl = ctk.CTkLabel(left, text="Session inactive",
                                     font=ctk.CTkFont("Segoe UI",11),
                                     text_color=C["teal"])
        self.stat_lbl.grid(sticky="w", padx=14, pady=(0,10))

        # ── RIGHT: meters
        right = ctk.CTkFrame(body, fg_color=C["card"], corner_radius=12,
                             border_width=1, border_color=C["border"])
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(right, text="Emotion Meter",
                     font=ctk.CTkFont("Segoe UI",14,"bold"),
                     text_color=C["text"]).pack(padx=16, pady=(16,4), anchor="w")

        self.cur_lbl = ctk.CTkLabel(right, text="😐  Neutral",
                                    font=ctk.CTkFont("Segoe UI Emoji",30),
                                    text_color=C["muted2"])
        self.cur_lbl.pack(pady=(4,2))

        self.conf_bar = ctk.CTkProgressBar(right, height=12, corner_radius=6,
                                           progress_color=C["amber"],
                                           fg_color=C["card2"])
        self.conf_bar.pack(fill="x", padx=16, pady=(0,2))
        self.conf_bar.set(0)
        self.conf_lbl = ctk.CTkLabel(right, text="Confidence: 0%",
                                     font=ctk.CTkFont("Segoe UI",11),
                                     text_color=C["muted"])
        self.conf_lbl.pack(pady=(0,10))

        self.bars={};self.cnt_lbls={};self.pct_lbls={}
        for em, info in EMOTIONS.items():
            r = ctk.CTkFrame(right, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(r, text=f"{info['emoji']} {info['label']}",
                         width=88, anchor="w",
                         font=ctk.CTkFont("Segoe UI",12),
                         text_color=info["color"]).pack(side="left")
            bar = ctk.CTkProgressBar(r, height=14, corner_radius=7,
                                     progress_color=info["color"],
                                     fg_color=C["card2"])
            bar.pack(side="left", fill="x", expand=True, padx=(6,6))
            bar.set(0)
            c1 = ctk.CTkLabel(r, text="0", width=28,
                              font=ctk.CTkFont("Segoe UI",11),
                              text_color=C["muted2"])
            c1.pack(side="left")
            p1 = ctk.CTkLabel(r, text="0%", width=40,
                              font=ctk.CTkFont("Segoe UI",11,"bold"),
                              text_color=info["color"])
            p1.pack(side="left", padx=(4,0))
            self.bars[em]=bar; self.cnt_lbls[em]=c1; self.pct_lbls[em]=p1

        ctk.CTkFrame(right, height=1, fg_color=C["border"]).pack(fill="x",padx=16,pady=8)

        sf = ctk.CTkFrame(right, fg_color=C["card2"], corner_radius=8)
        sf.pack(fill="x", padx=16, pady=(0,8))
        self.frames_lbl = ctk.CTkLabel(sf, text="Frames: 0",
                                       font=ctk.CTkFont("Segoe UI",11),
                                       text_color=C["muted2"])
        self.frames_lbl.pack(padx=12, pady=(8,2), anchor="w")
        self.dom_lbl = ctk.CTkLabel(sf, text="Dominant: —",
                                    font=ctk.CTkFont("Segoe UI",11),
                                    text_color=C["amber"])
        self.dom_lbl.pack(padx=12, pady=(0,8), anchor="w")

        ctk.CTkLabel(right, text="Live Log",
                     font=ctk.CTkFont("Segoe UI",11,"bold"),
                     text_color=C["muted2"]).pack(padx=16, anchor="w")
        self.log_scroll = ctk.CTkScrollableFrame(right, fg_color="transparent", height=85)
        self.log_scroll.pack(fill="x", padx=16, pady=(4,14))

    # ─── Detector init ───────────────────────────────────────
    def _init_detector(self):
        try:
            from deepface import DeepFace
            import numpy as np
            dummy = np.zeros((100,100,3), dtype=np.uint8)
            DeepFace.analyze(dummy, actions=["emotion"],
                             enforce_detection=False, silent=True)
            self._det_type = "deepface"
            self.after(0, lambda: self.eng_lbl.configure(
                text="🟢  DeepFace — High Accuracy",
                text_color=C["green"]))
            return
        except Exception:
            pass
        try:
            from fer import FER
            self._detector = FER(mtcnn=False)
            self._det_type = "fer"
            self.after(0, lambda: self.eng_lbl.configure(
                text="🟡  FER — Good Accuracy",
                text_color=C["amber"]))
            return
        except Exception:
            pass
        self._det_type = "opencv"
        self.after(0, lambda: self.eng_lbl.configure(
            text="🔴  OpenCV Basic — Install deepface for best accuracy",
            text_color=C["red"]))

    # ─── Session ─────────────────────────────────────────────
    def _start(self):
        self.session_id  = str(uuid.uuid4())[:8]
        self.em_counts   = {e:0 for e in EMOTIONS}
        self.total_frames= 0
        self.history     = []
        for b in self.bars.values(): b.set(0)
        for l in self.cnt_lbls.values(): l.configure(text="0")
        for l in self.pct_lbls.values(): l.configure(text="0%")
        self.conf_bar.set(0)
        self.running = True
        self.s_btn.configure(state="disabled")
        self.x_btn.configure(state="normal")
        threading.Thread(target=self._cam_loop, daemon=True).start()

    def _stop(self):
        self.running = False
        self.s_btn.configure(state="normal")
        self.x_btn.configure(state="disabled")
        total = sum(self.em_counts.values())
        self.stat_lbl.configure(
            text=f"Session {self.session_id} ended — {total} frames analysed")

    # ─── Camera loop ─────────────────────────────────────────
    def _cam_loop(self):
        try:
            import cv2
        except ImportError:
            self.after(0, lambda: self.stat_lbl.configure(text="⚠ OpenCV not installed"))
            return

        fc = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.after(0, lambda: self.stat_lbl.configure(text="⚠ Camera not found!"))
            self.running = False
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        idx=0; last_em="neutral"; last_scores={e:0.0 for e in EMOTIONS}
        label = self.lbl_var.get()

        while self.running:
            ret, frame = self.cap.read()
            if not ret: break
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.1, 5, minSize=(60,60))

            if len(faces) > 0 and idx % 3 == 0:
                x,y,w,h    = faces[0]
                face_roi   = frame[y:y+h, x:x+w]
                dom, scores= self._analyse(face_roi, cv2)
                last_em    = dom
                last_scores= scores
                self.em_counts[dom] = self.em_counts.get(dom,0) + 1
                self.total_frames  += 1
                ts = datetime.now().strftime("%H:%M:%S")
                self.history.append((ts, dom, round(scores.get(dom,0),3)))
                log_emotion(self.session_id, dom, scores.get(dom,0.5), label)
                self.after(0, lambda d=dom, s=dict(scores): self._update_ui(d,s))

            for (x,y,w,h) in faces:
                info = EMOTIONS.get(last_em, EMOTIONS["neutral"])
                try:
                    col_h=info["color"]
                    bgr=(int(col_h[5:7],16),int(col_h[3:5],16),int(col_h[1:3],16))
                except Exception: bgr=(0,220,120)
                cv2.rectangle(frame,(x,y),(x+w,y+h),bgr,2)
                conf_pct=round(last_scores.get(last_em,0)*100)
                cv2.putText(frame,f"{info['label']}  {conf_pct}%",
                            (x,y-8),cv2.FONT_HERSHEY_SIMPLEX,0.65,bgr,2)

            total = sum(self.em_counts.values())
            msg=(f"ID:{self.session_id}  Analysed:{total}  "
                 f"Faces:{len(faces)}  Engine:{self._det_type or '...'}")
            cv2.putText(frame,msg,(8,24),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,220,200),1)

            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            img=Image.fromarray(rgb); img.thumbnail((500,380))
            ci=ctk.CTkImage(img,size=img.size)
            self.after(0, lambda i=ci,m=msg: (
                self.cam_lbl.configure(image=i,text=""),
                self.stat_lbl.configure(text=m),
            ))
            self.cam_lbl.image_ref=ci
            idx+=1; time.sleep(0.02)
        self.cap.release()

    # ─── Analyse face ────────────────────────────────────────
    def _analyse(self, face_roi, cv2):
        scores={e:0.0 for e in EMOTIONS}; dominant="neutral"
        if self._det_type=="deepface":
            try:
                from deepface import DeepFace
                res=DeepFace.analyze(face_roi,actions=["emotion"],
                                     enforce_detection=False,silent=True)
                if isinstance(res,list): res=res[0]
                raw=res.get("emotion",{})
                dominant=res.get("dominant_emotion","neutral").lower()
                total=sum(raw.values()) or 1
                for k,v in raw.items():
                    if k.lower() in scores: scores[k.lower()]=v/total
            except Exception: pass
        elif self._det_type=="fer":
            try:
                res=self._detector.detect_emotions(face_roi)
                if res:
                    raw=res[0]["emotions"]
                    dominant=max(raw,key=raw.get).lower()
                    total=sum(raw.values()) or 1
                    for k,v in raw.items():
                        if k.lower() in scores: scores[k.lower()]=v/total
            except Exception: pass
        else:
            gray=cv2.cvtColor(face_roi,cv2.COLOR_BGR2GRAY) \
                 if len(face_roi.shape)==3 else face_roi
            mean=float(gray.mean()); std=float(gray.std())
            h,w=gray.shape
            m_mean=float(gray[h*2//3:,:].mean())
            f_mean=float(gray[:h//4,:].mean())
            if m_mean>f_mean*1.05 and std>38:
                dominant="happy";    scores["happy"]=0.72
            elif mean<82:
                dominant="angry";    scores["angry"]=0.60
            elif std<24:
                dominant="neutral";  scores["neutral"]=0.65
            elif m_mean<f_mean*0.88:
                dominant="sad";      scores["sad"]=0.60
            else:
                dominant="neutral";  scores["neutral"]=0.55
        return dominant, scores

    # ─── UI update ───────────────────────────────────────────
    def _update_ui(self, dominant, scores):
        info=EMOTIONS.get(dominant,EMOTIONS["neutral"])
        self.cur_lbl.configure(text=f"{info['emoji']}  {info['label']}",
                               text_color=info["color"])
        conf=scores.get(dominant,0)
        self.conf_bar.configure(progress_color=info["color"])
        self.conf_bar.set(conf)
        self.conf_lbl.configure(text=f"Confidence: {round(conf*100)}%",
                                text_color=info["color"])
        total=sum(self.em_counts.values()) or 1
        for em,bar in self.bars.items():
            cnt=self.em_counts.get(em,0); frac=cnt/total
            bar.set(frac)
            self.cnt_lbls[em].configure(text=str(cnt))
            self.pct_lbls[em].configure(text=f"{round(frac*100)}%")
        dom=max(self.em_counts,key=self.em_counts.get)
        di=EMOTIONS.get(dom,EMOTIONS["neutral"])
        self.frames_lbl.configure(text=f"Frames: {total}")
        self.dom_lbl.configure(text=f"Dominant: {di['emoji']} {di['label']}",
                               text_color=di["color"])
        ts=datetime.now().strftime("%H:%M:%S")
        row=ctk.CTkLabel(self.log_scroll,
                         text=f"{ts}  {info['emoji']} {info['label']}  ({round(conf*100)}%)",
                         font=ctk.CTkFont("Segoe UI",10),
                         text_color=info["color"])
        row.pack(anchor="w")
        kids=self.log_scroll.winfo_children()
        if len(kids)>40: kids[0].destroy()

    # ─── Export ──────────────────────────────────────────────
    def _export(self):
        if not self.history:
            messagebox.showinfo("No Data","Run a session first."); return
        from tkinter import filedialog
        path=filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"emotion_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            filetypes=[("CSV","*.csv")])
        if path:
            with open(path,"w",newline="",encoding="utf-8") as f:
                w=csv.writer(f); w.writerow(["Timestamp","Emotion","Confidence"])
                w.writerows(self.history)
            messagebox.showinfo("Exported",f"Saved:\n{path}")

    def destroy(self):
        self.running=False
        if self.cap and self.cap.isOpened(): self.cap.release()
        super().destroy()
