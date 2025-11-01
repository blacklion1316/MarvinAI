# Marvin v2 — Voice + Chat + Dynamic Local Commands (Windows/macOS/Linux)
# Requirements: pip install openai pyttsx3 sounddevice numpy scipy
# Optional (Linux): sudo apt-get install alsa-utils  (for audio)
import os
import sys
import json
import time
import glob
import shlex
import queue
import platform
import tempfile
import subprocess
from datetime import datetime

import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import pyttsx3

# -------- OpenAI client (compat w/ openai>=1.0 or legacy) --------
try:
    import openai
except ImportError:
    raise SystemExit("Please `pip install openai` first.")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("⚠️ No OPENAI_API_KEY in env. Set it for security. (export OPENAI_API_KEY=...)")
else:
    # Configure openai client with env key
    try:
        openai.api_key = OPENAI_API_KEY
    except Exception:
        pass
    # Optionally, you can uncomment the next line to hardcode the key (not recommended)
    # OPENAI_API_KEY = "your-api-key-here"
# ====== TTS ======
class TTS:
    def __init__(self, rate=200, volume=1.0):
        self.rate = rate
        self.volume = volume
        self.voice_index = 1  # Default voice index

    def _create_engine(self):
        """Create a fresh engine with current settings"""
        engine = pyttsx3.init()
        engine.setProperty('rate', self.rate)
        engine.setProperty('volume', self.volume)
        
        voices = engine.getProperty('voices')
        if self.voice_index < len(voices):
            engine.setProperty('voice', voices[self.voice_index].id)
        
        return engine

    def speak(self, text: str):
        """Convert text to speech with engine re-initialization for reliability"""
        # Use macOS native 'say' command if on macOS and pyttsx3 fails
        if platform.system() == "Darwin":
            try:
                subprocess.run(["say", text], check=True)
                return
            except Exception as e:
                print(f"macOS say command failed: {e}")
        
        # Try pyttsx3 for Windows/Linux or as fallback
        try:
            engine = self._create_engine()
            engine.say(text)
            engine.runAndWait()
            engine.stop()  # Properly stop the engine
        except Exception as e:
            print(f"TTS Error: {e}")
            # Fallback: try again with a new engine
            try:
                engine = self._create_engine()
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e2:
                print(f"TTS failed completely: {e2}")

    def change_voice(self, index: int):
        """Change voice index for future speech"""
        self.voice_index = index

# ====== Greeting ======
def greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning!"
    elif 12 <= hour < 17:
        return "Good afternoon!"
    elif 17 <= hour < 21:
        return "Good evening!"
    else:
        return "Good night!"

# ====== Audio Record + Whisper ======
def record_audio(duration=5, samplerate=44100):
    print("🎤 Listening...")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype=np.int16)
    sd.wait()
    print("✅ Recording complete.")
    return audio, samplerate

def transcribe_with_whisper(audio, samplerate):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
        wav.write(tmpfile.name, samplerate, audio)
        tmpfile_path = tmpfile.name
    try:
        with open(tmpfile_path, "rb") as f:
            # Works with openai>=1.0 style
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        return getattr(transcript, "text", None) or transcript.get("text")
    finally:
        try:
            os.unlink(tmpfile_path)
        except Exception:
            pass

# ====== Helpers: Context for GPT ======
def list_current_dir(max_items=500):
    try:
        items = os.listdir()
        items = items[:max_items]
        return items
    except Exception:
        return []

def list_path_executables(max_items=500):
    """Collect a lightweight list of executable names in PATH so GPT knows what exists."""
    seen = set()
    out = []
    path_dirs = os.getenv("PATH", "").split(os.pathsep)
    exts = []
    if os.name == "nt":
        # On Windows, PATHEXT defines executable suffixes.
        exts = os.getenv("PATHEXT", ".EXE;.BAT;.CMD;.COM").lower().split(";")
    for d in path_dirs:
        if not d or not os.path.isdir(d):
            continue
        try:
            for entry in os.listdir(d):
                full = os.path.join(d, entry)
                if os.name == "nt":
                    lower = entry.lower()
                    if any(lower.endswith(ext) for ext in exts):
                        base = lower
                        # strip extension for readability
                        for ext in exts:
                            if base.endswith(ext):
                                base = base[: -len(ext)]
                                break
                        if base not in seen:
                            seen.add(base)
                            out.append(base)
                else:
                    # Unix: executable bit
                    try:
                        st = os.stat(full)
                        if st.st_mode & 0o111 and os.path.isfile(full):
                            if entry not in seen:
                                seen.add(entry)
                                out.append(entry)
                    except Exception:
                        continue
                if len(out) >= max_items:
                    return out
        except Exception:
            continue
    return out

def canonical_os_info():
    sysname = platform.system()  # 'Windows', 'Darwin', 'Linux'
    release = platform.release()
    return f"{sysname} {release}"

# ====== Memory System (persistent JSON) ======
MEMORY_FILE = "marvin_memory.json"
CONVERSATION_HISTORY = []
MAX_HISTORY = 10

def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading memory: {e}")
    return {"facts": [], "preferences": {}, "notes": [], "created": datetime.now().isoformat()}

def save_memory(memory_data):
    try:
        memory_data["last_updated"] = datetime.now().isoformat()
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False

def add_to_conversation_history(role, content):
    global CONVERSATION_HISTORY
    CONVERSATION_HISTORY.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
    if len(CONVERSATION_HISTORY) > MAX_HISTORY * 2:
        CONVERSATION_HISTORY = CONVERSATION_HISTORY[-MAX_HISTORY * 2:]

def remember_fact(fact):
    memory = load_memory()
    fact_entry = {"content": fact, "timestamp": datetime.now().isoformat(), "source": "user_input"}
    memory["facts"].append(fact_entry)
    return save_memory(memory)

def remember_note(note):
    memory = load_memory()
    note_entry = {"content": note, "timestamp": datetime.now().isoformat()}
    memory["notes"].append(note_entry)
    return save_memory(memory)

def set_preference(key, value):
    memory = load_memory()
    memory["preferences"][key] = {"value": value, "timestamp": datetime.now().isoformat()}
    return save_memory(memory)

def recall_facts(limit=5):
    memory = load_memory()
    facts = memory.get("facts", [])
    return facts[-limit:] if facts else []

def recall_notes(limit=5):
    memory = load_memory()
    notes = memory.get("notes", [])
    return notes[-limit:] if notes else []

def get_memory_summary():
    memory = load_memory()
    summary = []
    facts = memory.get("facts", [])
    if facts:
        recent_facts = [f["content"] for f in facts[-3:]]
        summary.append(f"Recent facts: {'; '.join(recent_facts)}")
    prefs = memory.get("preferences", {})
    if prefs:
        pref_list = [f"{k}: {v['value']}" for k, v in prefs.items()]
        summary.append(f"User preferences: {'; '.join(pref_list)}")
    return " | ".join(summary) if summary else "No stored memories"

# ====== Command Execution (OS-aware shell) ======
def exec_shell(command: str) -> tuple[str, int]:
    """
    Execute a shell command cross-platform.
    Returns (combined_output, exit_code)
    """
    try:
        if os.name == "nt":
            # Use cmd so builtins like `start` work
            proc = subprocess.Popen(["cmd", "/c", command],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True)
        else:
            # Use bash -lc so login PATH and aliases are available (and allow things like `open` on mac)
            shell_path = "/bin/bash" if os.path.exists("/bin/bash") else "/bin/sh"
            proc = subprocess.Popen([shell_path, "-lc", command],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True)
        out, _ = proc.communicate()
        code = proc.returncode
        return (out or "").strip(), code
    except Exception as e:
        return f"[Executor error] {e}", 1

# ====== GPT Orchestrator ======
INTENT_SCHEMA = """
Return a single-line JSON ONLY, no prose, matching this schema:

{
  "mode": "run" | "chat",
  "command": "<string shell command to execute for THIS OS, if mode=='run'>",
  "say": "<assistant reply to speak/show if mode=='chat'>"
}

Rules:
- Consider the user's OS and available tools.
- If the user is asking to do an OS action (open an app, list services, show files, run a script),
  choose "run" and provide a concrete, OS-correct shell command.
- Otherwise choose "chat" and provide a helpful reply in the user's language.
- Do NOT include markdown, backticks, or extra keys. One compact JSON line only.
"""

def build_system_prompt():
    # Give GPT visibility of directory + available commands + OS
    dir_items = list_current_dir()
    path_bins = list_path_executables()

    sysname = platform.system()
    os_hint = {
        "Windows": (
            'Open Chrome: start chrome\n'
            'List directory: dir\n'
            'List all services: sc query type= service state= all\n'
            'Run Python script: python file.py'
        ),
        "Darwin": (  # macOS
            'Open Chrome: open -a "Google Chrome"\n'
            'List directory: ls -la\n'
            'List all services: launchctl list\n'
            'Homebrew services (if installed): brew services list\n'
            'Run Python script: python3 file.py'
        ),
        "Linux": (
            'Open Chrome: google-chrome || chromium || xdg-open "https://www.google.com"\n'
            'List directory: ls -la\n'
            'List all services: systemctl list-units --type=service --all\n'
            'Run Python script: python3 file.py'
        )
    }.get(sysname, "List directory: ls -la")
    memory_context = get_memory_summary()

    sys_prompt = f"""You are Marvin, a voice assistant that can either chat or run local shell commands.
OS: {canonical_os_info()}

You can see the current working directory files:
{os.getcwd()}
- {chr(10).join(dir_items)}

You can see a sample of executables available on PATH:
- {", ".join(path_bins[:100])}

Memory Context: {memory_context}

Guidance (choose appropriate commands for THIS OS):
{os_hint}

{INTENT_SCHEMA}
"""
    return sys_prompt

def gpt_decide(user_text: str) -> dict:
    """Ask GPT to either produce a run command or a chat reply (JSON-only contract)."""
    system_prompt = build_system_prompt()

    # Add to local conversation history for context
    add_to_conversation_history("user", user_text)

    # Build messages with recent conversation history
    messages = [{"role": "system", "content": system_prompt}]
    if CONVERSATION_HISTORY[:-1]:
        for msg in CONVERSATION_HISTORY[-8:]:
            if msg["role"] in ["user", "assistant"]:
                messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_text})

    # Use chat.completions for compatibility with user's original pattern
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=messages
    )
    content = resp.choices[0].message.content.strip()

    # Add assistant response to local history
    add_to_conversation_history("assistant", content)

    # Content must be JSON one-liner. Try to parse; if fail, fallback to chat.
    try:
        data = json.loads(content)
        # minimal sanity
        if not isinstance(data, dict): raise ValueError
        mode = data.get("mode")
        if mode == "run" and isinstance(data.get("command"), str) and data["command"].strip():
            return {"mode": "run", "command": data["command"].strip(), "say": ""}
        else:
            say = data.get("say") if isinstance(data.get("say"), str) else content
            return {"mode": "chat", "command": "", "say": say}
    except Exception:
        # If GPT ever violates, treat as chat
        return {"mode": "chat", "command": "", "say": content}

# ====== Main loop ======
def main():
    tts = TTS(rate=200)
    tts.change_voice(1)  # adjust as you like

    hello = f"Hello, I am Marvin. {greeting()} How can I assist you today?"
    print(f"🤖 {hello}")
    tts.speak(hello)

    while True:
        try:
            input("\n➡ Press Enter to speak...")
        except (EOFError, KeyboardInterrupt):
            break

        time.sleep(0.25)
        audio, sr = record_audio(duration=5)
        user_text = transcribe_with_whisper(audio, sr)

        if not user_text:
            print("😅 No speech detected.")
            continue

        print(f"🗣 You said: {user_text}")

        # Quick local exit
        if user_text.strip().lower() in {"exit", "quit", "bye"}:
            bye = "Goodbye! Have a great day!"
            print(f"🤖 {bye}")
            tts.speak(bye)
            break

        # Memory commands - handle before sending to GPT
        user_lower = user_text.lower()
        if user_lower.startswith("remember that") or user_lower.startswith("remember this"):
            fact = user_text[len("remember that"):].strip() if user_lower.startswith("remember that") else user_text[len("remember this"):].strip()
            if remember_fact(fact):
                response = "I've stored that in my memory."
                print(f"🤖 {response}")
                tts.speak(response)
            else:
                response = "Sorry, I had trouble saving that to memory."
                print(f"🤖 {response}")
                tts.speak(response)
            continue

        if user_lower.startswith("note that") or user_lower.startswith("take note"):
            note = user_text[len("note that"):].strip() if user_lower.startswith("note that") else user_text[len("take note"):].strip()
            if remember_note(note):
                response = "I've added that note."
                print(f"🤖 {response}")
                tts.speak(response)
            else:
                response = "Sorry, I couldn't save that note."
                print(f"🤖 {response}")
                tts.speak(response)
            continue

        if "what do you remember" in user_lower or "recall facts" in user_lower:
            facts = recall_facts()
            if facts:
                fact_list = [f["content"] for f in facts]
                response = f"Here's what I remember: {'; '.join(fact_list)}"
                print(f"🤖 {response}")
                tts.speak(response)
            else:
                response = "I don't have any facts stored in memory yet."
                print(f"🤖 {response}")
                tts.speak(response)
            continue

        if "show notes" in user_lower or "what notes" in user_lower:
            notes = recall_notes()
            if notes:
                note_list = [n["content"] for n in notes]
                response = f"Here are my notes: {'; '.join(note_list)}"
                print(f"🤖 {response}")
                tts.speak(response)
            else:
                response = "I don't have any notes stored."
                print(f"🤖 {response}")
                tts.speak(response)
            continue

        if user_lower.startswith("set preference") or user_lower.startswith("my preference"):
            if " is " in user_text:
                parts = user_text.split(" is ", 1)
                key = parts[0].replace("set preference", "").replace("my preference", "").strip()
                value = parts[1].strip()
            elif " to " in user_text:
                parts = user_text.split(" to ", 1)
                key = parts[0].replace("set preference", "").strip()
                value = parts[1].strip()
            else:
                response = "I need a preference in the format 'set preference [key] to [value]' or 'my preference is [value]'."
                print(f"🤖 {response}")
                tts.speak(response)
                continue
            if set_preference(key, value):
                response = f"I've saved your preference: {key} = {value}"
                print(f"🤖 {response}")
                tts.speak(response)
            else:
                response = "Sorry, I couldn't save that preference."
                print(f"🤖 {response}")
                tts.speak(response)
            continue

        # Ask GPT to decide
        decision = gpt_decide(user_text)

        if decision["mode"] == "run":
            cmd = decision["command"]
            print(f"⚙️ Executing: {cmd}")
            out, code = exec_shell(cmd)
            if out.strip():
                print(out)
            speak_msg = f"Done. Exit code {code}."
            tts.speak(speak_msg)
        else:
            # Plain chat
            reply = decision["say"]
            print(f"🤖 Marvin: {reply}")
            tts.speak(reply)

if __name__ == "__main__":
    main()