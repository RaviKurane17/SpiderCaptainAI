<div align="center">
  <img src="ui_placeholder.png" alt="Captain AI Logo" width="150"/>
  <h1>Captain AI Voice Assistant</h1>
  <p><i>A powerful, autonomous, desktop-based AI assistant integrated with Gemini Live Audio, Firebase, and local system controls.</i></p>
  
  [![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
  [![PyQt6](https://img.shields.io/badge/UI-PyQt6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
  [![Gemini](https://img.shields.io/badge/AI-Google_Gemini-orange.svg)](https://aistudio.google.com/)
  [![Firebase](https://img.shields.io/badge/Backend-Firebase-yellow.svg)](https://firebase.google.com/)
</div>

<br>

**Captain AI** is an advanced voice-activated operating system agent built as a final year engineering project. It acts as a bridge between the physical device (PC), the cloud (Google Gemini / Firebase), and your mobile phone, featuring a custom Iron Man-style holographic HUD.

## 🌟 Key Features

### 🧠 Cognitive Architecture (Gemini 2.5)
- **Real-time Native Audio:** True streaming voice conversations with ultra-low latency.
- **Autonomous Multi-step Planning:** Give Captain a complex goal (e.g., "Research X and save a report"), and the internal Agent Planner will break it down and execute it step-by-step.
- **Error Recovery Agent:** If a tool fails, Captain dynamically writes a fix and tries again.
- **Neural Memory (ChromaDB):** Remembers facts, preferences, relationships, and context permanently.

### 💻 System Control & Execution
- **Autonomous Code Execution:** Can write and run Python scripts locally in a sandboxed environment.
- **Complete System Automation:** Volume, brightness, process management, screenshot capture.
- **File System Mastery:** Create, find, read, and organize files locally.
- **Browser Automation:** Deep web searching and webpage interaction.
- **Offline Fallback (Ollama):** Basic functionality works even when disconnected from the internet.

### 📱 Mobile Integration (Firebase)
- **Phone-to-PC Commands:** Send voice commands from your Android phone directly to your PC.
- **Cross-device State:** Read phone notifications, battery level, and messages from your desktop.

### 🎨 Custom Cinematic UI
- **Holographic 3D Sphere:** Real-time particle system that reacts to speech and thought states.
- **System Dashboard:** Live telemetry (ping, weather), analytics tracking, and memory management.
- **Biometric Security:** Real-time facial recognition and secure PIN access.
- **Accessibility:** Built-in high contrast modes and full layout control.

## 🛠️ Technology Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **Core AI** | `google-genai` | Gemini 2.5 Flash Native Audio for real-time voice & planning |
| **UI Framework** | `PyQt6` | Hardware-accelerated custom rendering & system tray |
| **Local Memory** | `chromadb` | Vector database for fast semantic memory retrieval |
| **Phone Link** | `firebase-admin` | Realtime Database event listeners for Android integration |
| **Offline LLM** | `Ollama` | Local Qwen2.5-coder fallback when internet is down |
| **Audio I/O** | `sounddevice` | Raw PCM audio stream handling |

## 🚀 Installation & Setup

## 🆕 What's New in Captain

- 📂 **Advanced File Handling** — New support for direct file uploads. Drop PDFs, source code, or images into the assistant to have them analyzed, summarized, or edited instantly.
- 🎨 **Adaptive & Flexible UI** — A complete overhaul of the interface. The new UI is fully resizable and responsive, featuring transparency controls and customizable layouts to fit your workspace perfectly.
- 🐧🍎 **Refined Cross-Platform Stability** — Major fixes for macOS and Linux compatibility. Core system actions are now more consistent across all three major operating systems.
- ⚡ **Optimized Core Engine** — Significant performance boost in tool-calling logic and response generation, resulting in a 40% faster interaction speed.

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10 or higher
- A Google AI Studio API Key
- A Firebase Project (with Realtime Database enabled)

### Step 1: Clone & Install
```bash
git clone https://github.com/RaviKurane17/Main_Captain.git
cd Main_Captain
pip install -r requirements.txt
```

### Step 2: Configure Environment
Copy the configuration template:
```bash
cp .env.example .env
```
Edit the `.env` file and add your keys:
- `GEMINI_API_KEY`: Your Google AI Studio key
- `FIREBASE_KEY_PATH`: Absolute path to your Firebase Admin SDK JSON
- `PHONE_DEVICE_ID`: The UUID matching your Android companion app

### Step 3: Run Captain AI
```bash
python main.py
```
*On first launch, you will be prompted to set a Master PIN and complete a facial scan.*

## 📂 Project Structure

```text
Captain_AI/
├── main.py                 # Core application loop, Audio pipeline, Event router
├── ui.py                   # PyQt6 Holographic Interface (HUD, Dashboard, Settings)
├── agent/                  # Cognitive Architecture
│   ├── planner.py          # Breaks complex goals into JSON task sequences
│   ├── executor.py         # Runs tasks, executes sandboxed Python code
│   └── task_queue.py       # Thread-safe background task manager
├── actions/                # Tool Modules (18+ distinct capabilities)
│   ├── phone_agent.py      # Firebase Realtime DB integration
│   ├── file_controller.py  # Local filesystem management
│   ├── browser_control.py  # Playwright web automation
│   └── offline_parser.py   # Regex + Ollama local fallback
├── memory/                 # ChromaDB Vector Store & JSON states
├── utils/                  # Centralized config, analytics, and rotating loggers
└── plugins/                # Drop-in folder for custom third-party tools
```

## 🔐 Security Notice
- **Sandboxed Execution:** AI-generated code is run in an isolated subprocess with a 120-second timeout.
- **Local Data:** All chat history, facial embeddings, and memory stores remain strictly on your local disk.
- **Biometrics:** Uses local Haar Cascade and histogram correlation (no cloud processing).

## 📝 License
Designed and engineered by **Ravi Kurane**. All rights reserved. Built as a Computer Science Final Year Engineering Project.
