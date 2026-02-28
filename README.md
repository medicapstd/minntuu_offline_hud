# Jarvis AI Assistant

A functional, voice-controlled virtual assistant powered by Python. Features a minimalist Tkinter GUI, dynamic memory via SQLite, and local speech recognition using Vosk for zero-latency, private voice processing.

## 🌟 Features
- **Local Speech Recognition**: Uses Vosk to securely and instantly process audio entirely offline.
- **AI Brain**: Integrates DeepSeek for conversational logic.
- **Memory**: Tracks conversation context in a local SQLite database (`jarvis_memory.db`).
- **Interactive GUI**: A sleek, dark-themed Tkinter window for live status monitoring and text fallback.
- **Multithreading**: Core listening and GUI execution happen seamlessly in parallel.
- **System Utilities**: Integrates with `psutil` to check battery and CPU.
- **Clipboard Summarization**: Select text and have Jarvis instantly summarize it.
- **Dynamic App Control**: AppleScript integration to forcefully close running macOS apps.

## 🛠 Prerequisites
- macOS (as some commands use `osascript`).
- Python 3.10+
- A DeepSeek API Key.

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd PythonProject
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Download the Vosk Offline Speech Model:**
   - Download the model from [Vosk Models](https://alphacephei.com/vosk/models) (e.g., `vosk-model-small-en-us-0.15`)
   - Extract it.
   - Rename the extracted folder to exactly `model`.
   - Place the `model` folder directly in this project's root directory.

4. **Environment Variables:**
   - Create a `.env` file in the root directory.
   - Add your API key:
     ```env
     DEEPSEEK_API_KEY=your_actual_api_key_here
     ```

## 🎙 Running Jarvis

Simply run the main script inside the virtual environment:
```bash
python ai2.py
```
Jarvis will launch the visual GUI and begin listening.

## 📜 Voice Commands
Check out [`JARVIS_COMMANDS.md`](JARVIS_COMMANDS.md) for the full list of voice and text commands available.
