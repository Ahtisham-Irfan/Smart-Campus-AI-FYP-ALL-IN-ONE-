# 🎓 Smart Campus AI
## Emotion-Aware Intelligent Campus Automation System


---

## 📁 Project Structure

```
smart_campus_ai/
├── main.py                          # Entry point (Login + Dashboard)
├── requirements.txt                 # All dependencies
├── setup_and_run.bat               # Windows auto-setup script
├── README.md
│
├── modules/
│   ├── face_recognition_module.py  # Module 1: Face Enrollment
│   ├── face_attendance.py          # Module 2: AI Face Attendance
│   ├── emotion_detection.py        # Module 3: Live Emotion Detection
│   ├── neuromirror.py              # Module 4: NeuroMirror AI Analytics
│   ├── study_planner.py            # Module 5: AI Study Planner
│   ├── doc_summarizer.py           # Module 6: Document Summarizer
│   └── resume_screener.py          # Module 7: Resume Screener
│
├── database/
│   ├── db_setup.py                 # DB schema + initialization
│   └── db_helper.py                # CRUD helper functions
│
└── assets/
    ├── dataset/                    # Student face datasets
    └── captures/                   # Captured screenshots
```

---

## 🚀 Quick Start (Windows)

**Option A — Auto Setup:**
```
Double-click setup_and_run.bat
```

**Option B — Manual:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 🔑 Default Login Credentials

| Role    | Username | Password    |
|---------|----------|-------------|
| Admin   | admin    | admin123    |
| Teacher | teacher  | teacher123  |
| Student | student  | student123  |

---

## 📦 Key Dependencies

| Package           | Purpose                     |
|-------------------|-----------------------------|
| customtkinter     | Modern responsive UI        |
| opencv-python     | Camera & face detection     |
| face-recognition  | Face recognition (LBPH)     |
| deepface          | Emotion detection           |
| transformers      | NLP summarization (BART)    |
| pdfplumber        | PDF text extraction         |
| spacy / nltk      | NLP processing              |
| pandas            | Data & CSV exports          |
| sqlite3           | Built-in database           |

---

## ⚠️ Notes

- **face-recognition** requires cmake + Visual C++ Build Tools on Windows
- **deepface** auto-downloads models on first run (~300MB)
- **transformers BART** model downloads on first use (~1.5GB, optional)
- Camera modules require a working webcam

---

*Smart Campus AI | FYP Report 2022-AG-9158 | Supervised by Mr. Faheem Tariq*
