# 🛡️ Aegis - Personal AI Agent (100% Local & Private)

A comprehensive personal AI assistant designed to run completely offline on your Windows laptop using **Ollama**, featuring voice interaction, desktop & hardware telemetry, productivity management, local knowledge base (RAG), and optional Telegram bot connectivity.

---

## 🌟 Key Features

1. **🔒 100% Local & Private**: Powered by local LLMs via Ollama (`llama3.2:3b`, `qwen2.5:3b`, `llama3.2:1b`). Zero cloud reliance, zero subscription fees, complete privacy.
2. **🎙️ Voice Interaction**:
   - **Voice Input**: Integrated speech-to-text directly in the web dashboard (via HTML5 Web Speech API).
   - **Voice Output**: Offline Text-to-Speech (using Windows SAPI5 synthesizer).
3. **💻 Hardware & System Diagnostics**: Real-time telemetry monitoring for CPU usage, RAM utilization, battery health, and disk storage.
4. **📁 Local Tool Calling & File Operations**: The agent can inspect directory trees, read files, write documents, and run safe shell commands.
5. **📝 Personal Productivity**:
   - Built-in To-Do list planner (add, complete, filter tasks).
   - Quick Notes scratchpad with keyword search.
6. **📚 Personal Knowledge Base (RAG)**: Drag-and-drop notes and documents to allow the agent to answer questions from your private knowledge repository.
7. **📱 Mobile Remote Access (Telegram Bot)**: Optional connector to converse with your laptop agent directly from your phone.

---

## 🚀 Quick Start Guide

### 1. Install & Start Ollama
If Ollama is not yet installed on your laptop:
1. Download Ollama from: [https://ollama.com/download/windows](https://ollama.com/download/windows)
2. Run the installer and launch Ollama.
3. Open PowerShell or Command Prompt and download the recommended model for your 8GB laptop:
   ```powershell
   ollama pull llama3.2:3b
   ```

### 2. Launch Aegis Agent
Double-click `start.bat` in this folder, or run:
```powershell
.\.venv\Scripts\python.exe run.py
```
This will automatically launch the server and open your browser at `http://127.0.0.1:8000`.

---

## 📂 Project Architecture

```
personal-ai-agent/
│
├── core/
│   ├── config.py           # Configuration & system settings
│   ├── ollama_client.py    # Local Ollama HTTP REST wrapper
│   ├── tools.py            # System, File, Productivity, & Search tools
│   └── agent.py            # ReAct reasoning loop & tool dispatcher
│
├── web/
│   ├── app.py              # FastAPI server & REST API
│   └── static/
│       ├── index.html      # Responsive glassmorphism dashboard
│       ├── style.css       # Dark-mode high-tech styling
│       └── app.js          # Live streaming chat, voice, & telemetry
│
├── bot/
│   └── telegram_bot.py     # Optional smartphone connector via Telegram
│
├── voice/
│   └── tts.py              # Windows offline voice speech synthesis
│
├── data/                   # Local SQLite databases & knowledge store
│   ├── agent_memory.db     # Notes & To-dos
│   └── knowledge/          # Indexed documents
│
├── cli.py                  # Terminal REPL assistant
├── run.py                  # Server bootstrap & auto-browser launcher
├── start.bat               # Windows 1-click batch script
└── requirements.txt        # Python dependencies
```

---

## 💡 Recommended Models (For 8GB RAM Laptops)

| Model | Size | Best For |
|---|---|---|
| **llama3.2:3b** | ~2.0 GB | **Recommended Default**: Fast, highly capable reasoning & tool execution |
| **llama3.2:1b** | ~1.3 GB | Ultra-fast responses with minimal RAM footprint |
| **qwen2.5:3b** | ~2.0 GB | Exceptional code generation and structured reasoning |
