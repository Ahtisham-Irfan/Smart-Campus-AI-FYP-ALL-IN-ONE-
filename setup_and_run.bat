@echo off
title Smart Campus AI v2 - Setup & Launch
color 0A
echo.
echo  ============================================================
echo   Smart Campus AI v2 - Auto Setup
echo   University of Agriculture Faisalabad
echo  ============================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Download Python 3.11 from python.org
    pause & exit /b 1
)
echo [OK] Python found.

if not exist "venv" (
    echo [1] Creating virtual environment...
    python -m venv venv
)
echo [2] Activating environment...
call venv\Scripts\activate.bat

echo [3] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo [4] Installing GUI + Vision packages...
pip install customtkinter Pillow opencv-python opencv-contrib-python numpy --quiet

echo [5] Installing AI/Emotion packages...
pip install deepface fer tf-keras --quiet

echo [6] Installing NLP packages...
pip install transformers torch pdfplumber PyMuPDF fpdf2 scikit-learn nltk spacy --quiet

echo [7] Downloading NLTK data...
python -c "import nltk; nltk.download('punkt',quiet=True); nltk.download('stopwords',quiet=True); nltk.download('averaged_perceptron_tagger',quiet=True)"

echo.
echo  ============================================================
echo   Setup complete! Launching Smart Campus AI v2...
echo  ============================================================
echo.
echo  Default logins:
echo    Admin:   admin   / admin123
echo    Teacher: teacher / teacher123
echo    Student: student / student123
echo.
python main.py
pause
