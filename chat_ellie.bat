@echo off
color 0D
echo ========================================
echo          STARTING ELLIE CHAT            
echo ========================================
echo.

ollama list >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama serve...
    start /b ollama serve
    timeout /t 5 >nul
)

call D:\Ellie\venv\Scripts\activate
python chat_ellie.py
if %errorlevel% neq 0 pause
