@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The project Python environment is missing. Follow the setup steps in README.md.
  pause
  exit /b 1
)
echo Opening the local research desk...
".venv\Scripts\python.exe" -m eventstudy open-desk --config configs/study.yaml
if errorlevel 1 pause
