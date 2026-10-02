@echo off
color 0A
echo ========================================
echo               ELLIE SETUP               
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python 3.10+ is not installed or not in PATH.
    pause
    exit /b
)

echo Creating virtual environment...
python -m venv D:\Ellie\venv
call D:\Ellie\venv\Scripts\activate

echo Installing requirements...
pip install -r D:\Ellie\requirements.txt

echo Downloading models...
mkdir D:\Ellie\models >nul 2>&1
curl -L -o D:\Ellie\models\vosk-model.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
tar -xf D:\Ellie\models\vosk-model.zip -C D:\Ellie\models\

curl -L -o D:\Ellie\models\kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx
curl -L -o D:\Ellie\models\voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin

echo Checking Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama is not installed. Please download from https://ollama.com/
) else (
    echo Pulling models...
    ollama pull smollm2:360m
    ollama pull qwen2.5:1.5b
)

echo Checking espeak-ng...
espeak-ng --version >nul 2>&1
if %errorlevel% neq 0 (
    echo espeak-ng is not installed. Please download from https://github.com/espeak-ng/espeak-ng
)

echo Setup Complete!
pause
