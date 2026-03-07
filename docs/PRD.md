# Product Requirements Document (PRD): Jarvis AI Assistant

## 1. Project Overview

### 1.1 What is Jarvis?
**Product Name:** Jarvis AI Assistant  
**Project Type:** A voice-controlled desktop virtual assistant.  
**Main Goal:** Jarvis is a smart, privacy-first desktop application designed to act as a personal assistant on macOS. It uses completely offline speech recognition to listen to the user and an advanced AI brain to execute computer commands, answer questions, and summarize information with zero audio latency.

### 1.2 Our Big Picture Vision
The goal is to provide users with a powerful, hands-free way to manage their workflows without giving up their privacy. Right now, most voice assistants (like Siri or Alexa) send continuous audio recordings to the cloud. By processing voice locally and only using text to communicate with the AI brain, Jarvis gives users blazing-fast, secure automation—saving time and keeping conversations private.

---

## 2. The Problem We Are Solving

**Why is this software needed?**
Modern computer workflows are complex, and standard desktop assistants are either too limited or too invasive. We face a few main challenges:
- **Privacy Risks:** Users are uncomfortable having their constant audio streams sent over the internet to big tech servers just to process simple commands.
- **Context Loss:** Most basic scripts forget what you just said. If you ask a follow-up question, they fail.
- **Complicated System Management:** When apps freeze or the background gets cluttered, power users have to manually track down and force-quit processes through Activity Monitor, which breaks their focus.

**The Main Issue:**
There is no fluid, local-first bridge between high-level AI reasoning and low-level macOS system control. People need an assistant that operates entirely inside their specific desktop environment.

---

## 3. Who Will Use This Software?

### 3.1 Power Users & Developers (Primary Users)
- **Who they are:** People working heavily on macOS who have a lot of apps running at once.
- **What they want:** They want to hit a shortcut or speak a command to instantly clean up their computer, summarize a copied block of code, or open specific project apps without moving their hands from the keyboard.

### 3.2 Privacy-Conscious Individuals (Secondary Users)
- **Who they are:** Everyday users worried about corporate surveillance.
- **What they want:** They want the convenience of an AI assistant (like ChatGPT) but demand that the microphone's audio is processed purely on their local machine.

---

## 4. Key Features (What the Software Actually Does)

### 4.1 Step 1: Voice Input & Local Recognition
- **Zero-Latency Listening:** Jarvis uses an offline Vosk model to listen and instantly convert spoken words into text. This means no audio is ever sent to the cloud, making it instantaneous and incredibly secure.
- **Smart Wake & Sleep:** Users can tell Jarvis to "stop" and go to sleep, pausing continuous listening until they use a wake word ("resume" or "Jarvis").

### 4.2 Step 2: The Intelligent Brain & Memory
- **DeepSeek Integration:** For conversational questions and complex requests, the text is securely passed to a DeepSeek AI model via the OpenRouter API. 
- **Conversational Memory:** Jarvis uses a local SQLite database (`jarvis_memory.db`) to remember the last 10 interactions. If you ask a follow-up question, Jarvis actually remembers what you were just talking about.

### 4.3 Step 3: Powerful System Automation
Jarvis isn't just a chatbot; it physically controls the Mac.
- **App & Tab Control:** Jarvis can dynamically search for and open applications, specific documents, or websites. It can seamlessly open a "new tab" in Safari, Chrome, or Comet depending on what is actively running.
- **System Defense (Force Quitting):** If the Mac slows down, asking Jarvis to "close background apps" triggers an AppleScript routine that automatically hunts down non-essential background processes and safely kills them. 
- **Clipboard Summarization:** A user can highlight long text, copy it, and tell Jarvis to "summarize my clipboard." The AI instantly reads it and speaks a two-sentence summary out loud.

### 4.4 The Live Subtitle Dashboard (GUI)
When Jarvis is running, it doesn't just work in the shadows.
- **Minimalist HUD:** A sleek, transparent, dark-themed window hovers on the screen. 
- **Live Status:** It clearly shows if Jarvis is "Listening...", "Thinking...", or "Idle" so the user always knows what the system is doing.
- **Live Subtitles:** Whatever the user says, or whatever Jarvis replies, gets typed out on the screen like movie subtitles—perfect for when the user's speakers are muted.

---

## 5. Behind-the-Scenes Rules (NFRs)
- **Multithreading for Smoothness:** The GUI, the microphone listening loop, and the text input box all run on separate "threads" simultaneously. This guarantees that the GUI window never crashes or freezes while waiting for the AI to think.
- **Beautiful & Unobtrusive UI:** It leverages Tkinter with transparency and 'topmost' configurations to float elegantly over other work without getting in the way.
- **Ironclad Privacy:** All speech-to-text happens offline. To protect user access, API keys are hidden in a `.env` file and never hard-coded. 

---

## 6. What Tech are We Building With?

- **Frontend (The Visual Dashboard):**
  - **Framework:** Python `Tkinter` with customized dark mode elements.
  - **Interaction:** A text entry field for keyboard users and a live-updating subtitle label.
  
- **Backend (The Core Engine):**
  - **Language:** Python 3.10+
  - **Speech Processing:** `SpeechRecognition` combined with the `Vosk` offline model.
  - **The AI Brain:** OpenRouter API connecting to `deepseek/deepseek-r1:free`.
  - **System Control:** `osascript` (AppleScript) for native macOS hooks, `psutil` to check battery and CPU vitals, and `pyperclip` for clipboard reading.
  
- **Database (The Memory Vault):**
  - **Database:** Local `SQLite3` (in `jarvis_memory.db`) to instantly save and retrieve user/assistant chat history.

---

## 7. Future Blueprint (What We Add Next Year)
- **Fully Offline LLM:** Upgrading the DeepSeek API to a fully local model (like Llama 3 via Ollama) so the *entire* brain runs completely off the grid without any Wi-Fi.
- **Custom Voice Clones:** Moving away from standard macOS "say" dictation to high-quality, emotionally expressive local AI voices (like Piper TTS or Coqui).
- **Proactive Insights:** Real-time screen reading where Jarvis can "see" the screen contents and proactively suggest help based on what the user is looking at.
