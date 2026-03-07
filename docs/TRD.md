# 🛠️ Technical Requirements Document (TRD): Jarvis AI Assistant 🤖

## 1. 🌟 System Overview
**Jarvis AI Assistant** is a desktop-based voice assistant built for macOS. It acts as a bridge between the user's voice, cutting-edge AI reasoning, and low-level computer controls. 

The goal is to keep things **fast, private, and local** whenever possible! 🔒

---

## 2. 🏗️ High-Level Architecture
Jarvis operates using three main "engines" working together at the same time:

1. **🎤 The Listening Engine (Ears):** Always listening for commands using the microphone.
2. **🧠 The Thinking Engine (Brain):** Processing what you said and figuring out what to do.
3. **💻 The Action Engine (Hands):** Actually clicking things, opening apps, or typing on your Mac.

These engines run simultaneously using **Multithreading** 🧵 so the system never freezes!

---

## 3. 🧩 Core Tech Stack (The Building Blocks)

Here is exactly what we are using to build Jarvis underneath the hood:

### 🖥️ Frontend (What the User Sees)
*   **Language & Library:** Python using `Tkinter` 🐍
*   **Look & Feel:** A floating, transparent dark-mode window (HUD) that stays on top of other apps (`-topmost`).
*   **Features:** Live subtitles of what you say and what Jarvis replies, plus a text input box if you prefer typing instead of talking. ⌨️

### ⚙️ Backend (The Core Logic)
*   **Main Language:** Python 3.10+
*   **Speech-to-Text (Local):** `SpeechRecognition` library paired with the **Vosk** offline model. 🚫☁️ (No cloud needed for listening!)
*   **AI Brain (Cloud API):** OpenRouter API connecting to the `deepseek/deepseek-r1:free` model for smart reasoning. 🧠
*   **System Controls (macOS Magic):** 
    *   `osascript` (AppleScript) to open/close apps, manage tabs, and control the Mac natively. 🍏
    *   `psutil` to check computer health (CPU usage, battery levels). 🔋
    *   `pyperclip` to read and summarize whatever text you have copied to your clipboard. 📋

### 🗄️ Database (The Memory)
*   **Technology:** `SQLite3` (A lightweight, local database saved as `jarvis_memory.db`). 💾
*   **Purpose:** To remember the last 10 things you talked about so Jarvis understands the *context* of your conversation. 🗣️

---

## 4. 📋 Detailed Feature Requirements

### 🗣️ Voice & Listening Features
1.  **Offline Recognition:** Must process speech completely on the local computer without sending audio over the internet.
2.  **Wake/Sleep Modes:** Must stop listening when told "stop" and wake up when told "resume" or "Jarvis".
3.  **Auto-Adjust:** Must adjust to background noise automatically so it can hear you clearly. 🎧

### 🧠 Intelligence & Memory
1.  **Contextual Memory:** Must save conversation history to `jarvis_memory.db` and send the recent history to the DeepSeek AI so it remembers your previous questions. 📖
2.  **Text Fallback:** Must allow users to type commands if their microphone is broken or if they are in a quiet room.

### 💻 macOS System Control
1.  **App Management:** 
    *   Find and open applications dynamically even if the user says the name slightly wrong. 📂
    *   Force quit non-essential background apps to free up computer speed. 🚀
2.  **Browser Control:** Detect if Safari, Chrome, or Comet is running and open new tabs or specific websites automatically. 🌐
3.  **Hardware Commands:** Ability to shut down, restart, sleep, or lock the Mac screen using voice. 🔒
4.  **Clipboard Summary:** Read copied text and use the AI to generate a 2-sentence summary out loud. 📝

---

## 5. 🛡️ Security & Privacy Rules
*   **Local Processing:** 100% of the microphone data **must** stay on the user's computer. 🛑🎤
*   **Secret Keys:** The API key for DeepSeek must be hidden inside a `.env` file. It should **never** be written directly into the code. 🔑
*   **Safe Closing:** When force-quitting apps, the system must **never** close essential macOS services like Finder or the Dock. 🛡️

---

## 6. 🚀 Performance (Non-Functional Requirements)
*   **Zero-Crash GUI:** The visual window must never freeze while the AI is thinking. (Hence, the use of Threading). 🧵
*   **Fast Response:** The local speech-to-text should happen with near-zero latency. ⚡
*   **File Organization:** The project must be neatly organized into `src/` (code), `data/` (database), and `docs/` (documentation) folders. 📁

---

## 7. 🔮 Future Upgrades (Version 2.0)
*   **100% Offline AI:** Replacing DeepSeek with a fully local model (like Llama 3) so Jarvis doesn't even need Wi-Fi for complex answers! 🌍
*   **Better Voices:** Upgrading the standard Mac robot voice to a highly realistic, human-sounding AI voice (like Piper TTS). 🗣️🎙️
*   **Screen Vision:** Giving Jarvis the ability to "see" what is on your screen to help you proactively. 👀
