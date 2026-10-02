@echo off
color 0B
echo ========================================
echo              STARTING NOVA              
echo ========================================
echo.

ollama list >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama serve...
    start /b ollama serve
    timeout /t 5 >nul
)

call D:\Ellie\venv\Scripts\activate
python -m ellie.main
if %errorlevel% neq 0 pause
