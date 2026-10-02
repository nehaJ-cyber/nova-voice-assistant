# Ellie Voice Assistant

```text
  ______  _      _      _____  ______ 
 |  ____|| |    | |    |_   _||  ____|
 | |__   | |    | |      | |  | |__   
 |  __|  | |    | |      | |  |  __|  
 | |____ | |____| |____ _| |_ | |____ 
 |______||______|______|_____||______|
```

Ellie is a lightweight, offline-first voice assistant designed for standard hardware (i3 CPU, 8GB RAM). 
Powered by local models (Vosk for STT, Kokoro for TTS, and Ollama for LLMs), she offers excellent privacy while maintaining full functionality.

## Features
- **Offline Intelligence**: Uses Ollama with SmolLM2 (orchestration) and Qwen2.5 (execution).
- **Fast Wake & Speech**: OpenWakeWord and Vosk integration.
- **Natural Voice**: High-quality local TTS using Kokoro ONNX.
- **Windows Automation**: Controls apps, system functions, and volume.
- **Safety First**: C: drive protections and manual confirmations for sensitive actions.

## System Requirements
- OS: Windows 10/11
- CPU: Intel i3 or better
- RAM: 8GB minimum
- Audio: Microphone required

## Quick Start
1. Run `setup_ellie.bat` to install dependencies and download models.
2. Run `run_ellie.bat` (or `run_ellie.pyw` for a silent background run).
3. Say "Hey Ellie" followed by your command!

## Architecture Flow
When you say a command:
1. **OpenWakeWord** detects "Hey Ellie".
2. **Vosk** converts your speech to text.
3. The **SmolLM2 Orchestrator** interprets the intent and extracts entities.
4. The **Qwen2.5 Executor** breaks down the plan into tool steps.
5. The automation layer (pywinauto/pyautogui) runs the steps.
6. The assistant speaks back the outcome via **Kokoro TTS**.

## Configuration
Edit `config/config.yaml` to modify:
- Wake words
- Model versions and Ollama host
- Safety rules (blocked drives, blocked actions)
- UI preferences

## Available Commands
- **App Control**: "Open Notepad", "Close Calculator"
- **Web**: "Search Google for weather", "Open YouTube"
- **System**: "What time is it?", "Mute volume", "Increase volume"
- **Files**: "Read the file at D:\notes.txt" (C: drive is blocked)
- **General**: "What is the capital of France?"

## Safety Rules
- C: Drive access is strictly blocked to prevent accidental system changes.
- Destructive actions (like `delete_file`, `send_message`, `close_app`) require explicit voice confirmation.

## Troubleshooting
- **Ollama not running**: Ensure the Ollama app is installed and running in the background.
- **Mic issues**: Check Windows Privacy Settings to ensure apps have access to your microphone.

## License
MIT License
