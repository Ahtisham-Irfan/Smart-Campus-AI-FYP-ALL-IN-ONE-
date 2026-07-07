# 🎓 Smart Campus AI

**Emotion-Aware Intelligent Campus Automation System**

Smart Campus AI is a Final Year Project (FYP) that leverages Artificial Intelligence, Computer Vision, and Natural Language Processing to automate various campus activities. The system provides intelligent solutions for attendance management, emotion analysis, academic assistance, document summarization, and resume screening through a modern desktop application.

---

## Features

- AI-based Face Enrollment
- Automated Face Recognition Attendance
- Real-Time Emotion Detection
- NeuroMirror AI Analytics Dashboard
- AI Study Planner
- Document Summarizer
- AI Resume Screener
- Secure Role-Based Login System
- SQLite Database Integration
- Modern CustomTkinter User Interface

---

## Project Structure

```text
smart_campus_ai/
├── main.py
├── requirements.txt
├── setup_and_run.bat
├── README.md
│
├── modules/
│   ├── face_recognition_module.py
│   ├── face_attendance.py
│   ├── emotion_detection.py
│   ├── neuromirror.py
│   ├── study_planner.py
│   ├── doc_summarizer.py
│   └── resume_screener.py
│
├── database/
│   ├── db_setup.py
│   └── db_helper.py
│
└── assets/
    ├── dataset/
    └── captures/
```

---

## Installation

### Automatic Setup (Windows)

Run the following file:

```text
setup_and_run.bat
```

### Manual Setup

```bash
python -m venv venv
```

Activate the virtual environment:

```bash
venv\Scripts\activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python main.py
```

---

## Default Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Teacher | teacher | teacher123 |
| Student | student | student123 |

---

## Technologies Used

- Python
- CustomTkinter
- OpenCV
- Face Recognition
- DeepFace
- Transformers (BART)
- spaCy
- NLTK
- PDFPlumber
- Pandas
- SQLite

---

## Dependencies

| Package | Purpose |
|----------|---------|
| customtkinter | Modern desktop UI |
| opencv-python | Camera and image processing |
| face-recognition | Face recognition |
| deepface | Emotion detection |
| transformers | AI text summarization |
| pdfplumber | PDF text extraction |
| spacy | Natural language processing |
| nltk | Text preprocessing |
| pandas | Data handling |
| sqlite3 | Local database |

---

## Notes

- A webcam is required for face recognition and emotion detection.
- The DeepFace model is downloaded automatically during the first execution (~300 MB).
- Transformer models are downloaded on first use (~1.5 GB).
- Windows users may need CMake and Visual C++ Build Tools to install the `face-recognition` package successfully.

---

## Future Improvements

- Cloud Database Integration
- Student Performance Prediction
- AI Chat Assistant
- Mobile Application
- Online Attendance Portal
- Multi-Campus Support
- REST API Integration

---

## License

This project is licensed under the MIT License.

---

## Author

**Muhammad Ahtisham Irfan**

Bachelor of Science in Computer Science

University of Agriculture Faisalabad – Depalpur Campus

Final Year Project (2022–2026)

---

If you found this project useful, consider giving it a **Star** on GitHub.
