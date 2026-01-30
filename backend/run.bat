@echo off
cd /d "%~dp0"
echo Starting backend from %CD%
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
  echo Using venv
)
pip install -r requirements.txt -q 2>nul
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
