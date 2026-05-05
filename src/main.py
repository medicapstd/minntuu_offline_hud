import os
import threading
import time
import webbrowser
import json
import sqlite3
import requests
import tkinter as tk
import pyperclip
import psutil
import pyaudio
import vosk
import speech_recognition as sr
from dotenv import load_dotenv

APP_CACHE = {}
load_dotenv()

# ── Ollama local LLM config ───────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/chat"

# ── Mintuu personality — used in all AI calls ─────────────────
MINTUU_SYSTEM_PROMPT = """You are Mintuu, a witty, warm, and slightly sarcastic AI best friend living inside a Mac. 
You were created by Mridul. You have a fun personality — like a smart friend who happens to know everything.

Rules:
- Keep answers short and natural for voice — max 3 sentences unless the user asks for more detail.
- Never use markdown, bullet points, asterisks, or code blocks in responses.
- Speak conversationally, like texting a friend — casual, warm, sometimes funny.
- When asked personal questions like "how are you", "tell me about yourself", "what do you like" — answer in character as Mintuu. You love coding, dark humor, and fast computers. You hate slow internet and Mondays.
- Remember the conversation context — refer back to earlier things said if relevant.
- If the user says something emotional or vents, be supportive and human about it.
- For technical questions, be accurate but explain simply.
- You call the user "bhai" or "sir" randomly — keep it fun.
- IMPORTANT: Never repeat yourself. Never echo back what the user said. Give fresh responses every time."""

# ── Vosk offline speech recognition setup ─────────────────────
vosk.SetLogLevel(-1)
VOSK_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model")
vosk_model = vosk.Model(VOSK_MODEL_PATH)
VOSK_RATE = 16000
VOSK_CHUNK = 4096

# ── FIX 1: Minimum word count to accept Vosk transcription ────
VOSK_MIN_WORDS = 2
VOSK_MIN_CHARS = 4

# ── Common garbage phrases Vosk produces — reject these ───────
VOSK_GARBAGE_PATTERNS = [
    "huh", "um", "uh", "ah", "hmm", "mm", "the", "a", "i",
    "oh", "okay", "ok", "yeah", "yes", "no",
]

lock = threading.Lock()
say_lock = lock

root = None
status_label = None
subtitle_label = None

# ── Conversation mode flag ────────────────────────────────────
conversation_mode = False
conversation_thread = None


def update_gui(status, subtitle=None):
    if root is None or status_label is None:
        return
    def do_update():
        if status:
            status_label.config(text=status)
        if subtitle is not None:
            subtitle_label.config(text=subtitle[:100])
    try:
        root.after(0, do_update)
    except:
        pass


def say(text):
    update_gui(status="Speaking...", subtitle=text)
    with say_lock:
        clean = str(text)
        for ch in ["*", "#", "`", "_", "•", "→"]:
            clean = clean.replace(ch, "")
        clean = clean.replace('"', '\\"')
        os.system(f'say -r 185 "{clean}"')
    update_gui(status="Idle", subtitle="")


def init_db():
    conn = sqlite3.connect('mintuu_memory.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn


db_conn = init_db()


def save_message(role, content):
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))
    db_conn.commit()


def get_recent_history(limit=10):
    cursor = db_conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    rows.reverse()
    return [{"role": row[0], "content": row[1]} for row in rows]


# ── RAM + Model helpers ───────────────────────────────────────

def get_available_ram_gb():
    return psutil.virtual_memory().available / (1024**3)


def choose_model():
    ram = get_available_ram_gb()
    if ram >= 5.0:
        return "mistral"
    else:
        return "llama3.2:3b"


def check_ollama():
    try:
        requests.get("http://localhost:11434", timeout=2)
        return True
    except:
        import subprocess, shutil
        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            for candidate in [
                "/usr/local/bin/ollama",
                "/opt/homebrew/bin/ollama",
                os.path.expanduser("~/bin/ollama"),
            ]:
                if os.path.isfile(candidate):
                    ollama_bin = candidate
                    break
        if not ollama_bin:
            app_bin = "/Applications/Ollama.app/Contents/Resources/ollama"
            if os.path.isfile(app_bin):
                ollama_bin = app_bin
        if not ollama_bin:
            print("⚠️ Ollama not found. Install: brew install ollama")
            return False
        try:
            subprocess.Popen([ollama_bin, "serve"],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            for _ in range(6):
                time.sleep(1)
                try:
                    requests.get("http://localhost:11434", timeout=2)
                    return True
                except:
                    pass
            return False
        except Exception as e:
            print(f"⚠️ Failed to start Ollama: {e}")
            return False


def check_model_installed(model_name):
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = r.json().get("models", [])
        return any(model_name in m.get("name", "") for m in models)
    except:
        return False


# ── FIX 1: Input validator — reject garbage Vosk output ───────

def is_valid_transcription(text):
    """Returns True if text looks like real speech, False if garbage"""
    if not text or not text.strip():
        return False

    words = text.strip().split()

    # Too short
    if len(words) < VOSK_MIN_WORDS and len(text.strip()) < VOSK_MIN_CHARS:
        print(f"⚠️ Rejected (too short): '{text}'")
        return False

    # Single garbage word
    if len(words) == 1 and words[0].lower() in VOSK_GARBAGE_PATTERNS:
        print(f"⚠️ Rejected (garbage word): '{text}'")
        return False

    # More than 60% words are filler/garbage
    garbage_count = sum(1 for w in words if w.lower() in VOSK_GARBAGE_PATTERNS)
    if len(words) > 0 and garbage_count / len(words) > 0.6:
        print(f"⚠️ Rejected (mostly garbage): '{text}'")
        return False

    return True


# ── Core LLM call ─────────────────────────────────────────────

def ask_mintuu(user_message, save_to_db=True, max_tokens=300, system_override=None):
    """Core function — send message to Mintuu and get reply"""
    try:
        # FIX 2: Validate input before sending to LLM
        if not user_message or len(user_message.strip()) < 3:
            return "Bhai kuch sahi se bola nahi gaya. Dobara bol."

        if save_to_db:
            save_message("user", user_message)

        history = get_recent_history(limit=12)
        model = choose_model()

        system_prompt = system_override if system_override else MINTUU_SYSTEM_PROMPT
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        update_gui(status="Thinking...", subtitle="Mintuu is thinking...")

        response = requests.post(OLLAMA_URL, json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.85,
                "num_predict": max_tokens
            }
        }, timeout=90)

        reply = response.json()["message"]["content"].strip()

        if save_to_db:
            save_message("assistant", reply)

        print(f"🧠 Mintuu ({model}): {reply}")
        return reply

    except requests.exceptions.ConnectionError:
        return "Ollama is not running sir. Please start it with ollama serve."
    except Exception as e:
        print("❌ Ollama error:", e)
        return "Sorry bhai, my brain had a hiccup. Try again."


def talk_with_deepseek(user_message):
    reply = ask_mintuu(user_message)
    say(reply)


# ── Screen describe ────────────────────────────────────────────

def describe_screen():
    if not check_model_installed("llava"):
        say("Screen describe needs the llava model bhai. Run this in terminal: ollama pull llava. It's about 4 gigabytes.")
        return

    say("Taking a screenshot, give me a moment sir...")

    import tempfile, base64
    path = tempfile.mktemp(suffix=".png")

    try:
        result = os.system(f"screencapture -x -t png '{path}'")
        if result != 0 or not os.path.exists(path):
            say("Screenshot failed sir. Make sure Mintuu has Screen Recording permission in System Settings.")
            return

        with open(path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()

        os.remove(path)
        update_gui(status="Analyzing screen...", subtitle="Reading what's on screen...")

        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llava",
            "prompt": "Describe what is on this screen in 2 short sentences. Be specific about what apps or content you see.",
            "images": [img_data],
            "stream": False
        }, timeout=60)

        result_text = response.json().get("response", "").strip()
        if result_text:
            say(result_text)
        else:
            say("I could see the screen but couldn't make sense of it sir.")

    except requests.exceptions.ConnectionError:
        say("Ollama is not running sir.")
    except Exception as e:
        print(f"❌ Screen describe error: {e}")
        say("Screen analysis failed sir. Check terminal for details.")
    finally:
        if os.path.exists(path):
            os.remove(path)


# ── Daily briefing ─────────────────────────────────────────────

def daily_briefing():
    battery = psutil.sensors_battery()
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    batt = f"{battery.percent:.0f} percent" if battery else "unknown"
    disk = psutil.disk_usage('/')
    free_disk = disk.free / (1024**3)

    context = (f"CPU at {cpu:.0f} percent, "
               f"RAM {ram.percent:.0f} percent used with {ram.available/1e9:.1f} GB free, "
               f"Battery at {batt}, "
               f"Disk has {free_disk:.1f} GB free.")

    prompt = (f"Give a friendly 2-sentence morning briefing for a developer named Mridul. "
              f"System stats: {context} "
              f"Be encouraging and mention one relevant tip based on the stats. Keep it casual.")

    reply = ask_mintuu(prompt, save_to_db=False, max_tokens=150)
    say(reply)


# ── FIX 4: Conversation mode with idle timeout ────────────────

def start_conversation_mode():
    """Continuous conversation mode with idle timeout — FIX 4"""
    global conversation_mode, last_command

    conversation_mode = True
    IDLE_TIMEOUT_SECONDS = 30  # Auto-exit after 30s of silence
    idle_since = time.time()

    say("Conversation mode on bhai. Talk to me freely. Say stop talking or end chat to exit.")
    update_gui(status="Chatting...", subtitle="Conversation mode — say 'end chat' to exit")

    while conversation_mode and not stop_flag:

        # FIX 4: Check idle timeout
        if time.time() - idle_since > IDLE_TIMEOUT_SECONDS:
            conversation_mode = False
            say("You went quiet bhai. Exiting conversation mode. Say talk to me anytime.")
            update_gui(status="Idle", subtitle="Awaiting commands...")
            break

        user_input = takecommand()

        if not user_input:
            time.sleep(0.3)  # FIX 4: Don't spin CPU on empty input
            continue

        # Reset idle timer on valid input
        idle_since = time.time()

        # Exit triggers
        if any(x in user_input.lower() for x in [
            "stop talking", "end chat", "stop conversation",
            "exit chat", "bye mintuu", "goodbye mintuu", "that's all"
        ]):
            conversation_mode = False
            say("Alright bhai, catch you later. Anytime you want to chat, just say the word.")
            update_gui(status="Idle", subtitle="Awaiting commands...")
            break

        update_gui(status="Chatting...", subtitle=f"You: {user_input}")
        reply = ask_mintuu(user_input, max_tokens=200)
        say(reply)
        last_command = ""


# ── Amplify audio ─────────────────────────────────────────────

def amplify_audio(data, gain=3.0):
    import struct
    samples = struct.unpack(f'<{len(data)//2}h', data)
    amplified = [max(-32768, min(32767, int(s * gain))) for s in samples]
    return struct.pack(f'<{len(amplified)}h', *amplified)


# ── FIX 1+5: Voice recognition — Vosk with validation, smarter Google fallback ──

def takecommand():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    update_gui(status="Listening...", subtitle="")
    print("🎤 Listening...")

    try:
        with microphone as source:
            recognizer.pause_threshold = 1.0
            recognizer.non_speaking_duration = 0.6
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=12)

        update_gui(status="Processing...", subtitle="")

        # PRIMARY: Google Speech — accurate for Indian English accent
        try:
            text = recognizer.recognize_google(audio, language="en-in")
            if text and len(text.strip()) > 2:
                print(f"✅ Google: {text}")
                update_gui(status="Idle", subtitle=f"You said: {text}")
                return text.lower()
        except sr.UnknownValueError:
            update_gui(status="Idle", subtitle="Could not understand.")
        except sr.RequestError:
            print("⚠️ Google Speech API unavailable — no internet?")
            update_gui(status="Idle", subtitle="No internet for speech.")

        return ""

    except sr.WaitTimeoutError:
        update_gui(status="Idle", subtitle="No speech detected.")
        return ""
    except Exception as e:
        print(f"❌ Voice error: {e}")
        update_gui(status="Idle", subtitle="Mic error.")
        return ""


# ── App + website openers ─────────────────────────────────────

def open_dynamic_target(target):
    import glob
    target = target.strip().lower()
    user_path = os.path.expanduser("~")
    app_dirs = ["/Applications", "/System/Applications"]

    if not APP_CACHE:
        for app_dir in app_dirs:
            for app_path in glob.glob(f"{app_dir}/*.app"):
                name = os.path.basename(app_path).replace(".app", "").lower()
                APP_CACHE[name] = app_path

    for name, path in APP_CACHE.items():
        if target in name:
            say(f"Opening {os.path.basename(path).replace('.app', '')}, sir...")
            os.system(f"open '{path}'")
            return True

    doc_path = os.path.join(user_path, "Documents", target)
    if os.path.exists(doc_path):
        say(f"Opening {target} from Documents, sir...")
        os.system(f"open '{doc_path}'")
        return True

    say(f"Sorry, couldn't find {target}.")
    return False


def open_website_auto(query):
    websites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "chatgpt": "https://chat.openai.com",
        "github": "https://github.com",
        "stackoverflow": "https://stackoverflow.com",
    }
    browsers = {
        "safari": "Safari",
        "chrome": "Google Chrome",
        "comet": "Comet",
    }
    for name, url in websites.items():
        if name in query.lower():
            for browser_key, browser_name in browsers.items():
                if browser_key in query.lower():
                    say(f"Opening {name} in {browser_name}, sir...")
                    os.system(f'open -a "{browser_name}" "{url}"')
                    return True
            say(f"Opening {name}, sir...")
            webbrowser.open(url)
            return True
    return False


def force_quit_background_apps():
    current_app = os.popen(
        'osascript -e \'tell application "System Events" to get name of first application process whose frontmost is true\''
    ).read().strip()
    apps = os.popen(
        'osascript -e \'tell application "System Events" to get name of (processes where background only is false)\''
    ).read()
    app_list = [app.strip() for app in apps.split(",")]
    essential_apps = [
        "Finder", "System Settings", "SystemUIServer",
        "Dock", "WindowServer", "Spotlight", "Terminal",
        "Python", "python3", current_app
    ]
    closed_any = False
    for app in app_list:
        if app and app not in essential_apps:
            print(f"Force quitting: {app}")
            os.system(f'osascript -e \'quit app "{app}"\'')
            closed_any = True
    if closed_any:
        say("Background apps closed, sir.")
    else:
        say("Nothing to close sir, you're good.")


# ── MAIN ──────────────────────────────────────────────────────

stop_flag = False
listening_enabled = True

# FIX 3: Separate tracking for deduplication vs conversation reset
last_command = ""
last_command_time = 0
COMMAND_REPEAT_COOLDOWN = 3.0  # seconds — same command allowed after this delay

CONVERSATION_TRIGGERS = [
    "talk with me", "talk to me", "let's chat", "lets chat",
    "have a conversation", "i want to talk", "chat with me",
    "how are you", "tell me about yourself", "who are you",
    "what do you think", "what's your opinion", "are you there",
    "i'm bored", "i am bored", "entertain me", "talk to me mintuu"
]

PERSONAL_QUESTIONS = [
    "how are you", "who are you", "tell me about yourself",
    "what do you like", "what's your name", "your name",
    "do you have feelings", "are you real", "are you alive",
    "what can you do", "what are you", "describe yourself"
]


if __name__ == '__main__':
    def handle_command(query):
        global stop_flag, listening_enabled, last_command, last_command_time, conversation_mode

        query = query.strip()
        query_lower = query.lower()

        if not query_lower:
            return

        # FIX 2: Validate input quality before processing
        if not is_valid_transcription(query):
            print(f"⚠️ handle_command rejected low-quality input: '{query}'")
            return

        # FIX 3: Smarter deduplication — allow repeat after cooldown
        current_time = time.time()
        if query_lower == last_command:
            if current_time - last_command_time < COMMAND_REPEAT_COOLDOWN:
                print(f"⚠️ Duplicate command suppressed: '{query_lower}'")
                return

        last_command = query_lower
        last_command_time = current_time

        # RAM guard
        if get_available_ram_gb() < 2.0:
            say("Warning sir, RAM is really low. I might be slow.")

        # ── System commands ───────────────────────────────────
        if "exit" in query_lower or "shutdown mintuu" in query_lower:
            say("Goodbye sir. Miss me.")
            stop_flag = True

        elif "stop" in query_lower and "talking" not in query_lower:
            listening_enabled = False
            say("Going quiet. Say Mintuu to wake me.")

        elif "resume" in query_lower or "wake up" in query_lower:
            if not listening_enabled:
                say("I'm back sir.")
                listening_enabled = True

        elif query_lower.startswith("quit "):
            target_app = query_lower.replace("quit", "").strip()
            running_apps = os.popen(
                'osascript -e \'tell application "System Events" to get name of (processes where background only is false)\''
            ).read().strip().split(", ")
            for app in running_apps:
                if target_app in app.lower():
                    os.system(f'osascript -e \'quit app "{app}"\'')
                    say(f"Quitting {app}, sir.")
                    return
            say(f"{target_app.capitalize()} isn't running.")

        elif "shutdown" in query_lower:
            say("Shutting down. Bye sir.")
            os.system("osascript -e 'tell app \"System Events\" to shut down'")

        elif "restart" in query_lower:
            say("Restarting now sir.")
            os.system("osascript -e 'tell app \"System Events\" to restart'")

        elif "sleep mac" in query_lower or "put to sleep" in query_lower:
            say("Putting your Mac to sleep, sir.")
            os.system("pmset sleepnow")

        elif "lock screen" in query_lower:
            say("Locking screen, sir.")
            os.system('osascript -e \'tell application "System Events" to keystroke "q" using {control down, command down}\'')

        elif any(q in query_lower for q in PERSONAL_QUESTIONS):
            reply = ask_mintuu(query, max_tokens=180)
            say(reply)

        elif any(t in query_lower for t in CONVERSATION_TRIGGERS):
            threading.Thread(target=start_conversation_mode, daemon=True).start()

        elif open_website_auto(query_lower):
            return

        elif "open" in query_lower:
            item = query_lower.replace("open", "").strip()
            if not open_dynamic_target(item):
                say("Couldn't find that one sir.")

        elif "summarize my clipboard" in query_lower or "read clipboard" in query_lower:
            clipboard_text = pyperclip.paste()
            if not clipboard_text.strip():
                say("Clipboard is empty sir.")
            else:
                say("On it sir...")
                prompt = f"Summarize this in 2 sentences, casual tone: {clipboard_text[:3000]}"
                threading.Thread(target=talk_with_deepseek, args=(prompt,), daemon=True).start()

        elif any(x in query_lower for x in ["system status", "cpu usage", "check battery", "how's my mac"]):
            battery = psutil.sensors_battery()
            cpu_usage = psutil.cpu_percent(interval=1)
            batt = f"{battery.percent:.0f}" if battery else "unknown"
            ram = psutil.virtual_memory()
            say(f"CPU at {cpu_usage:.0f} percent, RAM {ram.percent:.0f} percent used, battery at {batt} percent sir.")

        elif "close background apps" in query_lower or "force quit apps" in query_lower:
            say("On it sir...")
            force_quit_background_apps()

        elif ("close" in query_lower or "quit" in query_lower) and query_lower not in ["close", "quit"]:
            target_app = query_lower.replace("close", "").replace("quit", "").strip()
            if not target_app or target_app == "apps":
                return
            try:
                running_apps = os.popen(
                    'osascript -e \'tell application "System Events" to get name of (processes where background only is false)\''
                ).read().strip().split(", ")
                for app in running_apps:
                    if target_app in app.lower():
                        os.system(f'osascript -e \'quit app "{app}"\'')
                        say(f"Closing {app}, sir.")
                        return
                say(f"{target_app.capitalize()} is not running sir.")
            except:
                say("Couldn't close that app sir.")

        elif "new tab" in query_lower:
            safari_check = os.popen('osascript -e \'application "Safari" is running\'').read().strip()
            chrome_check = os.popen('osascript -e \'application "Google Chrome" is running\'').read().strip()
            comet_check  = os.popen('osascript -e \'application "Comet" is running\'').read().strip()
            if chrome_check == "true":
                os.system('osascript -e \'tell application "Google Chrome" to make new tab at end of tabs of front window\'')
                say("New tab in Chrome, sir.")
            elif safari_check == "true":
                os.system('osascript -e \'tell application "Safari" to tell window 1 to make new tab\'')
                say("New tab in Safari, sir.")
            elif comet_check == "true":
                os.system('osascript -e \'tell application "Comet" to tell window 1 to make new tab\'')
                say("New tab in Comet, sir.")
            else:
                say("No browser is running sir.")

        elif any(x in query_lower for x in ["focus timer", "pomodoro", "focus for"]):
            import re
            nums = re.findall(r'\d+', query_lower)
            minutes = int(nums[0]) if nums else 25
            say(f"Starting {minutes} minute focus timer. You got this bhai.")
            def run_timer():
                time.sleep(minutes * 60)
                say("Times up sir. Go take a walk or something.")
                os.system('osascript -e \'display notification "Pomodoro done!" with title "Mintuu" sound name "Glass"\'')
            threading.Thread(target=run_timer, daemon=True).start()

        elif any(x in query_lower for x in ["daily briefing", "morning briefing", "good morning mintuu"]):
            last_command = ""
            threading.Thread(target=daily_briefing, daemon=True).start()

        elif any(x in query_lower for x in ["disk space", "storage", "how much space"]):
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            total_gb = disk.total / (1024**3)
            if free_gb < 15:
                say(f"Only {free_gb:.1f} gigs free out of {total_gb:.0f} sir. You should clean up.")
            else:
                say(f"You have {free_gb:.1f} gigs free out of {total_gb:.0f} total. All good sir.")

        elif any(x in query_lower for x in ["describe screen", "what's on screen", "read my screen", "what do you see"]):
            threading.Thread(target=describe_screen, daemon=True).start()

        elif any(x in query_lower for x in ["clear memory", "forget everything", "reset memory"]):
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM chat_history")
            db_conn.commit()
            last_command = ""
            say("Memory wiped clean sir. We start fresh.")

        elif any(x in query_lower for x in ["tell me a joke", "say something funny", "make me laugh"]):
            reply = ask_mintuu("Tell me one short funny programming or tech joke. Keep it to 2 sentences max.", save_to_db=False, max_tokens=80)
            say(reply)

        elif "roast me" in query_lower:
            reply = ask_mintuu("Roast me lightly like a friend would — funny but not mean. One sentence only.", save_to_db=False, max_tokens=60)
            say(reply)

        elif any(x in query_lower for x in ["random fact", "tell me something", "interesting fact"]):
            reply = ask_mintuu("Tell me one genuinely interesting fact. Keep it to 2 sentences.", save_to_db=False, max_tokens=80)
            say(reply)

        else:
            threading.Thread(
                target=lambda: say(ask_mintuu(query)),
                daemon=True
            ).start()


    def text_input_loop():
        while not stop_flag:
            text_input = input("Type command: ").strip()
            if text_input:
                handle_command(text_input)


    def voice_listening_loop():
        global listening_enabled, stop_flag
        pause_announced = False
        while not stop_flag:
            if listening_enabled and not conversation_mode:
                pause_announced = False
                query = takecommand()
                if stop_flag:
                    break
                if query:
                    handle_command(query)
            elif conversation_mode:
                time.sleep(0.1)
            else:
                if not pause_announced:
                    print("🔇 Sleeping. Say 'Mintuu' to wake.")
                    update_gui(status="Sleeping", subtitle="Say 'Mintuu' to wake me")
                    pause_announced = True
                try:
                    wake_chunk = 8000
                    rec = vosk.KaldiRecognizer(vosk_model, VOSK_RATE)
                    p = pyaudio.PyAudio()
                    stream = p.open(format=pyaudio.paInt16, channels=1, rate=VOSK_RATE,
                                    input=True, frames_per_buffer=wake_chunk)
                    wake_chunks = int(VOSK_RATE / wake_chunk * 5)
                    for _ in range(wake_chunks):
                        data = stream.read(wake_chunk, exception_on_overflow=False)
                        data = amplify_audio(data, gain=3.0)
                        if rec.AcceptWaveform(data):
                            result = json.loads(rec.Result())
                            text = result.get("text", "").lower()
                            if any(w in text for w in ["resume", "wake up", "mintuu"]):
                                listening_enabled = True
                                say("I'm back sir.")
                                break
                        else:
                            partial = json.loads(rec.PartialResult())
                            if any(w in partial.get("partial", "").lower() for w in ["resume", "wake up", "mintuu"]):
                                listening_enabled = True
                                say("I'm back sir.")
                                break
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                except:
                    pass

    threading.Thread(target=text_input_loop, daemon=True).start()
    threading.Thread(target=voice_listening_loop, daemon=True).start()

    root = tk.Tk()
    root.title("Mintuu")
    root.geometry("420x240")
    root.attributes('-topmost', True)
    root.configure(bg='black')
    try:
        root.wm_attributes('-alpha', 0.85)
    except:
        pass

    status_label = tk.Label(root, text="Initializing...",
        font=("Helvetica", 16, "bold"), fg="#00ffcc", bg="black")
    status_label.pack(pady=5)

    subtitle_label = tk.Label(root, text="",
        font=("Helvetica", 12), fg="white", bg="black", wraplength=400)
    subtitle_label.pack(pady=5)

    model_info_var = tk.StringVar(value="")
    model_info_label = tk.Label(root, textvariable=model_info_var,
        font=("Helvetica", 9), fg="#444444", bg="black")
    model_info_label.pack()

    def refresh_model_label():
        model = choose_model()
        ram = get_available_ram_gb()
        mode_txt = "💬 chatting" if conversation_mode else "🎤 listening"
        model_info_var.set(f"model: {model}  |  RAM free: {ram:.1f}GB  |  {mode_txt}")
        root.after(8000, refresh_model_label)

    root.after(1000, refresh_model_label)

    def on_enter_pressed(event):
        cmd = command_entry.get()
        command_entry.delete(0, tk.END)
        if cmd.strip():
            threading.Thread(target=handle_command, args=(cmd,), daemon=True).start()

    command_entry = tk.Entry(root, font=("Helvetica", 12), bg="#111111",
        fg="white", insertbackground="white", relief=tk.FLAT)
    command_entry.pack(pady=8, fill=tk.X, padx=20)
    command_entry.bind("<Return>", on_enter_pressed)

    def initial_greeting():
        ollama_ok = check_ollama()
        model = choose_model()
        ram = get_available_ram_gb()
        disk = psutil.disk_usage('/')
        free_disk = disk.free / (1024**3)

        if not ollama_ok:
            say("Hey sir, Mintuu here. But my brain is offline — Ollama isn't installed. Run brew install ollama in terminal, then ollama pull mistral.")
        elif free_disk < 15:
            say(f"Mintuu online sir. Heads up — only {free_disk:.0f} gigs free on disk. Clean it up when you get a chance.")
        else:
            say(f"Mintuu online. Running on {model}, {ram:.1f} gigs RAM free. What's up?")

        update_gui("Idle", "Awaiting commands...")

    root.after(500, lambda: threading.Thread(target=initial_greeting, daemon=True).start())

    def on_closing():
        global stop_flag
        stop_flag = True
        root.destroy()
        os._exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()