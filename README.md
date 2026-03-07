# 🤖 Jarvis AI Assistant

Welcome to the **Jarvis AI Assistant** project! Jarvis is a functional, voice-controlled virtual assistant powered by Python. It features a minimalist Tkinter GUI, dynamic memory via SQLite, and local speech recognition using Vosk for zero-latency, private voice processing.

This project bridge the gap between high-level AI reasoning and low-level macOS system control. Simply put: you talk, Jarvis thinks locally, and your Mac obeys! 🚀

---

## 🌟 The Big Picture: Why Jarvis?

Modern computer workflows are complex, and standard desktop assistants (like Siri or Alexa) are either too limited or too invasive. They send constant audio recordings to the cloud, risking your privacy. Furthermore, they often forget what you just said, making follow-up questions frustrating.

**Jarvis solves these problems by:**
1. **Prioritizing Privacy:** All speech processing and listening happen 100% locally on your machine. No audio is ever sent to the cloud. 🛑☁️
2. **Contextual Memory:** Jarvis remembers your recent conversations so you can ask smart follow-up questions. 🧠
3. **Powerful System Control:** From force-closing lagging apps to reading your clipboard, Jarvis physically interacts with macOS. 💻

---

## ✨ Core Features

Here is exactly what Jarvis can do for you:

### 🎙️ 1. Zero-Latency Offline Listening
- Uses the **Vosk offline speech model** to instantly convert your voice into text.
- Say "**stop**" to put Jarvis to sleep (pausing the microphone).
- Say "**resume**" or "**Jarvis**" to instantly wake him back up.

### 🧠 2. Intelligent AI Brain
- Conversational logic is powered by the incredibly smart `deepseek/deepseek-r1:free` AI model.
- Jarvis stores your recent conversations in a local database (`data/jarvis_memory.db`) so he never loses context during a long chat.

### 🖥️ 3. Ultimate macOS Desktop Automation
- **App Control:** Jarvis dynamically searches your Mac and opens applications, websites, or specific documents for you.
- **Browser Control:** He knows if you are using Safari, Chrome, or Comet, and can open new tabs automatically. 🌐
- **System Defense:** Mac slowing down? Say "close background apps" and Jarvis will safely force quit unnecessary background processes without touching essential macOS apps like Finder. 🧹
- **Clipboard Summarizer:** Highlight and copy text (like a long email or code block), ask Jarvis to "summarize my clipboard," and he will mentally process the text and read a 2-sentence summary out loud. 📋
- **System Vitals:** Ask him to "check battery" or check "CPU usage" to get live diagnostic feedback on your machine. 🔋

### 📺 4. The Live Subtitle Dashboard (HUD)
- A sleek, floating, dark-themed Tkinter window stays on top of your work.
- It displays a live status ("Listening...", "Thinking...") so you always know what Jarvis is doing.
- Features **Live Subtitles** so you can read what you said and what Jarvis replied—perfect for when your speakers are muted. 🔕
- Feel like typing? Use the text input box at the bottom of the HUD to send silent commands. ⌨️

---

## 🏗️ Project Architecture & Tech Stack

The project is neatly organized into `src/`, `docs/`, and `data/` directories to keep the codebase clean. 

- **Frontend:** Python `Tkinter` (Minimalist Dark Mode).
- **Backend:** Python 3.10+, `SpeechRecognition`, `Vosk`, and OpenRouter (`deepseek-r1:free`).
- **Memory API:** `SQLite3` (Local Database).
- **System Hooks:** `osascript` (AppleScript for macOS control), `psutil` (hardware vitals), `pyperclip` (clipboard reading).

---

## 🛠 Prerequisites

Before installing, make sure you have the following ready:
- **macOS** *(Required, as many commands leverage native `osascript`)* 🍏
- **Python 3.10+** 🐍
- A **DeepSeek API Key** (via OpenRouter or direct). 🔑

---

## 🚀 Installation & Setup Guide

### 1. Clone the repository
```bash
git clone https://github.com/Mridul-SOl/jarvis-AI.git
cd jarvis-AI
```

### 2. Create a virtual environment & install packages
*It's highly recommended to use a virtual environment so you don't mess up your global Python packages!*
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Setup the Offline Voice Brain (Vosk)
Jarvis needs a language model locally downloaded to understand your voice:
1. Go to [Vosk Models](https://alphacephei.com/vosk/models).
2. Download a small English model (e.g., `vosk-model-small-en-us-0.15`).
3. Extract the downloaded ZIP file.
4. Rename that extracted folder to exactly **`model`**.
5. Move the **`model`** folder into the root directory of this project.

### 4. Setup Your Secret API Key
1. Create a file named `.env` in the root directory.
2. Inside that file, paste your API key like this:
```env
DEEPSEEK_API_KEY=your_actual_api_key_here
```

---

## 🕹️ Running Jarvis

Ready to start the assistant? Make sure your virtual environment is active, and run the following command from the root folder:

```bash
python src/main.py
```

The graphical HUD will appear, and Jarvis will greet you and start listening immediately! 🎧

---

## � Looking for Commands?

Jarvis can understand a huge variety of conversational commands. 

👉 **Check out the [`docs/JARVIS_COMMANDS.md`](docs/JARVIS_COMMANDS.md) document to see a full cheat code list of everything you can say to him!**

👉 **Curious about the nitty-gritty rules? Review the [`docs/TRD.md`](docs/TRD.md) and [`docs/PRD.md`](docs/PRD.md)!**

Enjoy having your own personal digital butler! 🎩
