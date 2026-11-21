@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" -m eventstudy close-desk --config configs/study.yaml
if errorlevel 1 pause
