import os
import threading
import time
import webbrowser
import speech_recognition as sr
import sqlite3
import requests
import tkinter as tk
import pyperclip
import psutil
from dotenv import load_dotenv

APP_CACHE = {}

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

recognizer = sr.Recognizer()
microphone = sr.Microphone()
lock = threading.Lock()
say_lock = lock

root = None
status_label = None
subtitle_label = None

def update_gui(status, subtitle=None):
    if root is None or status_label is None:
        return
    def do_update():
        if status:
            status_label.config(text=status)
        if subtitle is not None:
            subtitle_label.config(text=subtitle)
    try:
        root.after(0, do_update)
    except:
        pass

def say(text):
    update_gui(status="Speaking...", subtitle=text)
    with say_lock:
        safe_text = str(text).replace('"', '\\"')
        os.system(f'say -r 189 "{safe_text}"')
    update_gui(status="Idle", subtitle="")

def init_db():
    conn = sqlite3.connect('jarvis_memory.db', check_same_thread=False)
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


def talk_with_deepseek(user_message):
    try:
        save_message("user", user_message)
        history = get_recent_history(limit=10)
        
        messages = [{"role": "system", "content": "You are Jarvis, a smart AI assistant."}]
        messages.extend(history)
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
                "Referer": "https://github.com/mriduljarvis",  # Optional but good
                "X-Title": "Mridul-Jarvis"
            },
            json={
                "model": "deepseek/deepseek-r1:free",
                "messages": messages
            }
        )

        data = response.json()

        # 🔍 Fix for 'choices' error:
        if 'choices' not in data:
            print(f"❌ Error from DeepSeek (status {response.status_code}):", data)
            say("Sorry, I couldn't understand the response from DeepSeek.")
            return

        reply = data['choices'][0]['message']['content'].strip()
        save_message("assistant", reply)
        
        print("🧠 Jarvis (AI):", reply)
        say(reply)

    except Exception as e:
        print("❌ Error talking to DeepSeek:", e)
        say("Sorry, I couldn't reach the AI brain.")


def takecommand():
    with microphone as source:
        recognizer.pause_threshold = 0.5
        recognizer.non_speaking_duration = 0.3
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.adjust_for_ambient_noise(source, duration=0.2)
        update_gui(status="Listening...", subtitle="")
        print("Listening...")
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        try:
            update_gui(status="Thinking...", subtitle="")
            query = recognizer.recognize_google(audio, language="en-in")
            print(f"User said: {query}")
            update_gui(status="Idle", subtitle=f"You said: {query}")
            return query
        except Exception:
            print("Sorry, could not understand. Please say again.")
            update_gui(status="Idle", subtitle="Could not understand.")
            time.sleep(0.1)
            return ""


def open_dynamic_target(target):
    import glob

    target = target.strip().lower()
    user_path = os.path.expanduser("~")

    # Search for any .app in /Applications and /System/Applications that matches
    app_dirs = ["/Applications", "/System/Applications"]
    matched_app = None

    if not APP_CACHE:
        for app_dir in app_dirs:
            for app_path in glob.glob(f"{app_dir}/*.app"):
                name = os.path.basename(app_path).replace(".app", "").lower()
                APP_CACHE[name] = app_path

    for name, path in APP_CACHE.items():
        if target in name:
            matched_app = path
            break

    if matched_app:
        say(f"Opening {os.path.basename(matched_app).replace('.app', '')}, sir...")
        os.system(f"open '{matched_app}'")
        return True

    # Check in ~/Documents
    doc_path = os.path.join(user_path, "Documents", target)
    if os.path.exists(doc_path):
        say(f"Opening {target} from Documents, sir...")
        os.system(f"open '{doc_path}'")
        return True

    say(f"Sorry, I couldn't find or open {target}.")
    return False


def open_website_auto(query):
    websites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "chatgpt": "https://chat.openai.com"
        
    }
    browsers = {
        "safari": "Safari",
        "chrome": "Google Chrome",
        "comet" : "Comet",
        "Atlas" : "ChatGPT Atlas"
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
        "Dock", "WindowServer", "Spotlight", current_app
    ]
    closed_any = False
    for app in app_list:
        if app not in essential_apps:
            print(f"Force quitting: {app}")
            os.system(f'osascript -e \'quit app "{app}"\'')
            closed_any = True
    if closed_any:
        say("All background applications have been safely closed, sir.")
    else:
        say("No apps to close, sir.")


# -------------------- MAIN --------------------

stop_flag = False
listening_enabled = True
last_command = ""


if __name__ == '__main__':
    def handle_command(query):
        global stop_flag, listening_enabled, last_command
        query = query.lower().strip()
        if query == "" or query == last_command:
            return
        last_command = query

        if "exit" in query:
            say("Goodbye, sir.")
            stop_flag = True

        elif "stop" in query:
            listening_enabled = False
            say("Jarvis is now silent. Say 'Jarvis' to wake me up.")

        elif "resume" in query or "wake up" in query:
            if not listening_enabled:
                say("Resuming voice assistant, sir.")
                listening_enabled = True

        elif query.startswith("quit "):
            target_app = query.replace("quit", "").strip().lower()
            running_apps = os.popen(
                'osascript -e \'tell application "System Events" to get name of (processes where background only is false)\''
            ).read().strip().split(", ")
            for app in running_apps:
                if target_app in app.lower():
                    os.system(f'osascript -e \'quit app "{app}"\'')
                    say(f"Quitting {app}, sir.")
                    return
            say(f"{target_app.capitalize()} is not currently running, sir.")


        elif "shutdown" in query:
            say("Shutting down your Mac, sir.")
            os.system("osascript -e 'tell app \"System Events\" to shut down'")

        elif "restart" in query:
            say("Restarting your Mac, sir.")
            os.system("osascript -e 'tell app \"System Events\" to restart'")

        elif "sleep" in query:
            say("Putting your Mac to sleep, sir.")
            os.system("pmset sleepnow")


        elif "lock screen" in query:
            say("Locking the screen, sir.")
            os.system(
                'osascript -e \'tell application "System Events" to keystroke "q" using {control down, command down}\'')


        elif open_website_auto(query):
            return


        elif "open" in query:
            item = query.replace("open", "").strip()
            if not open_dynamic_target(item):
                say("Sorry, I could not find that application or file.")

        elif "summarize my clipboard" in query or "read clipboard" in query:
            clipboard_text = pyperclip.paste()
            if not clipboard_text.strip():
                say("Your clipboard is empty, sir.")
            else:
                say("Reading clipboard and summarizing...")
                threading.Thread(
                    target=talk_with_deepseek,
                    args=(f"Please summarize this in 2 sentences: {clipboard_text}",),
                    daemon=True
                ).start()

        elif "system status" in query or "cpu usage" in query or "check battery" in query:
            battery = psutil.sensors_battery()
            cpu_usage = psutil.cpu_percent(interval=1)
            batt_percent = battery.percent if battery else "unknown"
            say(f"CPU usage is at {cpu_usage} percent, and battery is at {batt_percent} percent, sir.")


        elif "close background apps" in query or "force quit apps" in query:
            say("Closing background applications, sir...")
            force_quit_background_apps()

        elif "close" in query or "quit" in query:
            target_app = query.replace("close", "").replace("quit", "").strip().lower()
            if not target_app or target_app == "apps":
                return  # Prevent "close apps" or invalid
            try:
                running_apps = os.popen(
                    'osascript -e \'tell application "System Events" to get name of (processes where background only is false)\''
                ).read().strip().split(", ")
                for app in running_apps:
                    if target_app in app.lower():
                        os.system(f'osascript -e \'quit app "{app}"\'')
                        say(f"Closing {app}, sir.")
                        return
                say(f"{target_app.capitalize()} is not currently running, sir.")
            except Exception as e:
                print("❌ Error while trying to close app:", e)
                say("I couldn't close the application.")


        elif "new tab" in query:

            # Check if Safari or Chrome is running

            safari_check = os.popen('osascript -e \'application "Safari" is running\'').read().strip()

            chrome_check = os.popen('osascript -e \'application "Google Chrome" is running\'').read().strip()

            comet_check = os.popen('osascript -e \'application "Comet" is running\'').read().strip()

            if "chrome" in query:

                if chrome_check == "true":

                    os.system(
                        'osascript -e \'tell application "Google Chrome" to make new tab at end of tabs of front window\'')

                    say("New tab opened in Chrome, sir.")

                else:

                    say("Chrome is not running, sir.")


            elif "safari" in query:

                if safari_check == "true":

                    os.system('osascript -e \'tell application "Safari" to tell window 1 to make new tab\'')

                    say("New tab opened in Safari, sir.")

                else:

                    say("Safari is not running, sir.")


            elif "comet" in query:

                if comet_check == "true":

                    os.system('osascript -e \'tell application "Comet" to tell window 1 to make new tab\'')

                    say("New tab opened in Comet, sir.")

                else:

                    say("Comet is not running, sir.")


            else:

                # Auto-detect and open in running browser

                if chrome_check == "true":

                    os.system(
                        'osascript -e \'tell application "Google Chrome" to make new tab at end of tabs of front window\'')

                    say("New tab opened in Chrome, sir.")

                elif safari_check == "true":

                    os.system('osascript -e \'tell application "Safari" to tell window 1 to make new tab\'')

                    say("New tab opened in Safari, sir.")

                elif comet_check == "true":

                    os.system('osascript -e \'tell application "Comet" to tell window 1 to make new tab\'')

                    say("New tab opened in Comet, sir.")

                else:

                    say("No supported browser is currently running, sir.")


        elif "talk with me" in query or "talk to me" in query:
            say("What would you like to talk about?")
            try:
                if threading.current_thread().name == "MainThread":
                    user_message = takecommand()
                else:
                    user_message = input("🧠 Type your message to Jarvis: ")
                if user_message:
                    threading.Thread(
                        target=talk_with_deepseek,
                        args=(user_message,),
                        daemon=True
                    ).start()
            except Exception as e:
                print("⚠️ Mic access failed in thread:", e)
                user_message = input("🧠 Type your message to Jarvis: ")
                if user_message:
                    threading.Thread(
                        target=talk_with_deepseek,
                        args=(user_message,),
                        daemon=True
                    ).start()


def text_input_loop():
    global listening_enabled
    while not stop_flag:
        listening_enabled = False
        text_input = input("Type command (or press Enter to skip): ").strip()
        listening_enabled = True
        if text_input:
            handle_command(text_input)


def voice_listening_loop():
    global listening_enabled, stop_flag
    pause_announced = False
    while not stop_flag:
        if listening_enabled:
            pause_announced = False
            query = takecommand()
            if stop_flag:
                break
            handle_command(query)
        else:
            if not pause_announced:
                print("🔇 Listening paused. Say 'Jarvis' to reactivate.")
                update_gui(status="Sleeping", subtitle="Say 'Jarvis' to wake me")
                pause_announced = True
            try:
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    query = recognizer.recognize_google(audio, language="en-in").lower()
                    if "resume" in query or "wake up" in query or "jarvis" in query:
                        if not listening_enabled:
                            say("Resuming voice assistant, sir.")
                            listening_enabled = True
            except:
                pass

# Threading for inputs
threading.Thread(target=text_input_loop, daemon=True).start()
threading.Thread(target=voice_listening_loop, daemon=True).start()

# GUI Setup
root = tk.Tk()
root.title("Jarvis")
root.geometry("400x200")
root.attributes('-topmost', True)
root.configure(bg='black')
try:
    root.wm_attributes('-alpha', 0.8) # transparency
except:
    pass

status_label = tk.Label(root, text="Initializing...", font=("Helvetica", 16, "bold"), fg="#00ffcc", bg="black")
status_label.pack(pady=5)

subtitle_label = tk.Label(root, text="", font=("Helvetica", 12), fg="white", bg="black", wraplength=380)
subtitle_label.pack(pady=5)

def on_enter_pressed(event):
    cmd = command_entry.get()
    command_entry.delete(0, tk.END)
    if cmd.strip():
        threading.Thread(target=handle_command, args=(cmd,), daemon=True).start()

command_entry = tk.Entry(root, font=("Helvetica", 12), bg="#222222", fg="white", insertbackground="white", relief=tk.FLAT)
command_entry.pack(pady=10, fill=tk.X, padx=20)
command_entry.bind("<Return>", on_enter_pressed)

# Initial greeting in background thread so it doesn't block GUI creation
def initial_greeting():
    say("Hello, I am Jarvis A.I")
    update_gui("Idle", "Awaiting commands...")

root.after(500, lambda: threading.Thread(target=initial_greeting, daemon=True).start())

# Close cleanly
def on_closing():
    global stop_flag
    stop_flag = True
    root.destroy()
    os._exit(0)
    
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
