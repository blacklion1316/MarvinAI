import pyttsx3
import openai
from datetime import datetime
import speech_recognition as sr 
import os
import subprocess
import time
import dotenv
import json
import platform
import tempfile
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav

# Load environment variables from .env file
dotenv.load_dotenv(".env")

openai.api_key = os.getenv("OPENAI_API_KEY")


class _TTS:
    def __init__(self):
        self.rate = 150
        self.volume = 1
        self.voice_id = 0  # Default to male voice
        
    def _create_engine(self):
        """Create a fresh engine with current settings"""
        engine = pyttsx3.init()
        engine.setProperty('rate', self.rate)
        engine.setProperty('volume', self.volume)
        
        voices = engine.getProperty('voices')
        if self.voice_id < len(voices):
            engine.setProperty('voice', voices[self.voice_id].id)
        
        return engine

    def speak(self, text):
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
            except:
                print("TTS failed completely")

    def get_voices(self, voice_id=None):
        if voice_id == 0:  # Male voice (David)
            self.voice_id = 0
        elif voice_id == 1:  # Female voice (Zira)
            self.voice_id = 1

    def change_voice(self, voice_id):
        self.get_voices(voice_id)
        if voice_id == 0:
            self.speak("Hello, this is Marvin with male voice")
        elif voice_id == 1:
            self.speak("Hello, this is Marvin with female voice")

    def change_rate(self, rate):
        self.rate = rate

tts = _TTS()

# ====== Memory System ======
MEMORY_FILE = "marvin_memory.json"
CONVERSATION_HISTORY = []
MAX_HISTORY = 10  # Number of exchanges to remember in session

def load_memory():
    """Load persistent memory from JSON file"""
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading memory: {e}")
    return {
        "facts": [],
        "preferences": {},
        "notes": [],
        "created": datetime.now().isoformat()
    }

def save_memory(memory_data):
    """Save memory data to JSON file"""
    try:
        memory_data["last_updated"] = datetime.now().isoformat()
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False

def add_to_conversation_history(role, content):
    """Add message to conversation history"""
    global CONVERSATION_HISTORY
    CONVERSATION_HISTORY.append({
        "role": role, 
        "content": content, 
        "timestamp": datetime.now().isoformat()
    })
    # Keep only recent history
    if len(CONVERSATION_HISTORY) > MAX_HISTORY * 2:  # *2 because user+assistant pairs
        CONVERSATION_HISTORY = CONVERSATION_HISTORY[-MAX_HISTORY * 2:]

def remember_fact(fact):
    """Store a fact in long-term memory"""
    memory = load_memory()
    fact_entry = {
        "content": fact,
        "timestamp": datetime.now().isoformat(),
        "source": "user_input"
    }
    memory["facts"].append(fact_entry)
    return save_memory(memory)

def remember_note(note):
    """Store a note in long-term memory"""
    memory = load_memory()
    note_entry = {
        "content": note,
        "timestamp": datetime.now().isoformat()
    }
    memory["notes"].append(note_entry)
    return save_memory(memory)

def set_preference(key, value):
    """Store a user preference"""
    memory = load_memory()
    memory["preferences"][key] = {
        "value": value,
        "timestamp": datetime.now().isoformat()
    }
    return save_memory(memory)

def recall_facts(limit=5):
    """Retrieve recent facts from memory"""
    memory = load_memory()
    facts = memory.get("facts", [])
    return facts[-limit:] if facts else []

def recall_notes(limit=5):
    """Retrieve recent notes from memory"""
    memory = load_memory()
    notes = memory.get("notes", [])
    return notes[-limit:] if notes else []

def get_memory_summary():
    """Get a summary of stored memory for context"""
    memory = load_memory()
    summary = []
    
    # Recent facts
    facts = memory.get("facts", [])
    if facts:
        recent_facts = [f["content"] for f in facts[-3:]]
        summary.append(f"Recent facts: {'; '.join(recent_facts)}")
    
    # User preferences
    prefs = memory.get("preferences", {})
    if prefs:
        pref_list = [f"{k}: {v['value']}" for k, v in prefs.items()]
        summary.append(f"User preferences: {'; '.join(pref_list)}")
    
    return " | ".join(summary) if summary else "No stored memories"

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

def get_current_time():
    now = datetime.now()
    current_time = now.strftime("%I:%M %p")
    return current_time

def get_current_date():
    year = datetime.now().year
    month = datetime.now().month
    day = datetime.now().day
    date = f"{day:02d}/{month:02d}/{year}"
    return date

def test_microphone():
    """Test if microphone is working with detailed diagnostics"""
    try:
        r = sr.Recognizer()
        
        # List available microphones
        print("Available microphones:")
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"  Microphone {index}: {name}")
        
        # Test with default microphone
        with sr.Microphone() as source:
            print(f"\nUsing default microphone...")
            print("Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source, duration=1)
            
            # Set lower threshold for testing
            r.energy_threshold = 50  # Very sensitive for testing
            r.dynamic_energy_threshold = True
            
            print(f"Energy threshold: {r.energy_threshold}")
            print("Testing microphone... Say 'hello' now!")
            
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=3)
                print("✓ Microphone captured audio successfully!")
                
                # Try to recognize the audio
                try:
                    text = r.recognize_google(audio, language='en-US')
                    print(f"✓ Recognition successful: '{text}'")
                    return True
                except:
                    print("✓ Audio captured but couldn't recognize speech")
                    return True
                    
            except sr.WaitTimeoutError:
                print("✗ No audio detected - microphone may not be working")
                return False
                
    except Exception as e:
        print(f"✗ Microphone test failed: {e}")
        return False

def greeting():
    # if time is morning, afternoon, or evening
    now = datetime.now()
    current_hour = now.hour
    if 5 <= current_hour < 12:
        return "Good morning!"
    elif 12 <= current_hour < 17:
        return "Good afternoon!"
    elif 17 <= current_hour < 21:
        return "Good evening!"
    else:
        return "Good night!"
    
def takeCommandCMD():
    query = input("Please tell me how I can assist you: ")
    return query

def takeCommandMic():
    r = sr.Recognizer()
    
    # Try specific microphones that we know work
    microphone_candidates = [
        1,   # Microphone (Brio 101) - this worked in diagnostic
        7,   # Microphone (Yeti X) - backup option
        36,  # Microphone (Yeti X) - another instance
        79,  # Microphone (Yeti X) - yet another instance
        0    # Microsoft Sound Mapper - fallback
    ]
    
    for mic_index in microphone_candidates:
        try:
            print(f"Trying microphone index {mic_index}...")
            with sr.Microphone(device_index=mic_index) as source:
                print("Listening...")
                print("Adjusting for ambient noise...")
                r.adjust_for_ambient_noise(source, duration=1)
                
                # Very sensitive settings that worked in diagnostic
                r.energy_threshold = 50
                r.dynamic_energy_threshold = False
                r.pause_threshold = 0.8
                
                print(f"Energy threshold: {r.energy_threshold}")
                print("Say something now...")
                
                try:
                    audio = r.listen(source, timeout=10, phrase_time_limit=5)
                    print("Audio captured successfully!")
                    break  # Success, exit the loop
                except sr.WaitTimeoutError:
                    print(f"Timeout with microphone {mic_index}, trying next...")
                    continue
                    
        except Exception as e:
            print(f"Error with microphone {mic_index}: {e}")
            continue
    else:
        # If we get here, all microphones failed
        print("All microphones failed!")
        return None
    
    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-US')
        print(f"You said: {query}")
        return query
    except sr.UnknownValueError:
        print("Sorry, I couldn't understand what you said.")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None
    except Exception as e:
        print(f"Error during speech recognition: {e}")
        return None

def takeCommandWhisper():
    """Use Whisper for voice recognition instead of Google Speech Recognition"""
    try:
        audio, sr = record_audio(duration=5)
        user_text = transcribe_with_whisper(audio, sr)
        
        if not user_text:
            print("😅 No speech detected.")
            return None
            
        print(f"🗣 You said: {user_text}")
        return user_text
    except Exception as e:
        print(f"Error with Whisper recognition: {e}")
        return None

def check_openai_connection():
    """Check if OpenAI API is available"""
    try:
        # Simple test to check if API key is working
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        return True
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return False

def test_microphone():
    """Test if microphone is working with detailed diagnostics"""
    try:
        r = sr.Recognizer()
        
        # List available microphones
        print("Available microphones:")
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"  Microphone {index}: {name}")
        
        # Test with default microphone
        with sr.Microphone() as source:
            print(f"\nUsing default microphone...")
            print("Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source, duration=1)
            
            # Set lower threshold for testing
            r.energy_threshold = 50  # Very sensitive for testing
            r.dynamic_energy_threshold = True
            
            print(f"Energy threshold: {r.energy_threshold}")
            print("Testing microphone... Say 'hello' now!")
            
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=3)
                print("✓ Microphone captured audio successfully!")
                
                # Try to recognize the audio
                try:
                    text = r.recognize_google(audio, language='en-US')
                    print(f"✓ Recognition successful: '{text}'")
                    return True
                except:
                    print("✓ Audio captured but couldn't recognize speech")
                    return True
                    
            except sr.WaitTimeoutError:
                print("✗ No audio detected - microphone may not be working")
                return False
                
    except Exception as e:
        print(f"✗ Microphone test failed: {e}")
        return False

def run_local_command(command):
    """Execute local system commands with improved Windows handling"""
    try:
        if platform.system() == "Windows":
            # Special handling for Windows commands that may return exit code 1 but work correctly
            if "explorer" in command.lower():
                # explorer.exe often returns exit code 1 but works fine
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
                # For explorer, ignore exit code 1 as it's normal behavior
                if result.returncode == 1 and "explorer" in command.lower():
                    return f"Command executed: {command}"
                elif result.returncode != 0:
                    return f"Command failed with exit code {result.returncode}: {result.stderr}"
                else:
                    return f"Command Output: {result.stdout}" if result.stdout else f"Command executed: {command}"
            else:
                # Regular command handling
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    return f"Command failed: {result.stderr}"
                return f"Command Output: {result.stdout}" if result.stdout else f"Command executed: {command}"
        else:
            # Unix-like systems
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return f"Command failed: {result.stderr}"
            return f"Command Output: {result.stdout}" if result.stdout else f"Command executed: {command}"
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error running command: {e}"

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



def chat_with_gpt(prompt):
    """Send a prompt to OpenAI GPT and get a response"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Updated model name
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except openai.AuthenticationError:
        return "Sorry, there's an authentication error with OpenAI. Please check your API key."
    except openai.RateLimitError:
        return "Sorry, I've hit the rate limit. Please try again in a moment."
    except openai.APIConnectionError:
        return "Sorry, I cannot connect to OpenAI. Please check your internet connection."
    except Exception as e:
        return f"Sorry, there was an error: {str(e)}"

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
    memory_context = get_memory_summary()

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
    
    # Add user input to conversation history
    add_to_conversation_history("user", user_text)
    
    # Build messages with conversation history for context
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add recent conversation history (excluding current user input)
    if CONVERSATION_HISTORY[:-1]:  # All except the just-added user input
        for msg in CONVERSATION_HISTORY[-8:]:  # Last 8 messages for context
            if msg["role"] in ["user", "assistant"]:
                messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current user input
    messages.append({"role": "user", "content": user_text})

    # Use chat.completions for compatibility with user's original pattern
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=messages
    )
    content = resp.choices[0].message.content.strip()
    
    # Add assistant response to conversation history
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

def main():
    # Check OpenAI connection
    print("Checking OpenAI connection...")
    if check_openai_connection():
        tts.speak("OpenAI GPT is ready.")
        print("✓ OpenAI API is available")
    else:
        tts.speak("Warning: Cannot connect to OpenAI. Please check your API key.")
        print("✗ OpenAI API is not available")

    # Test microphone
    print("Testing microphone...")
    if test_microphone():
        print("✓ Microphone is working")
    else:
        print("✗ Microphone test failed")

    tts.change_voice(1)  # Female voice (Zira) - do this first
    tts.change_rate(200)  # Then set the rate
    
    hello = f"Hello, I am Marvin. {greeting()} How can I assist you today?"
    print(f"🤖 {hello}")
    tts.speak(hello)
    
    while True:
        try:
            input("\n➡ Press Enter to speak...")
        except (EOFError, KeyboardInterrupt):
            break
            
        time.sleep(0.25)
        
        # Try Whisper first, fallback to Google Speech Recognition
        print("\nUsing Whisper for voice recognition...")
        user_input = takeCommandWhisper()
        
        # If Whisper fails, try Google Speech Recognition
        if user_input is None:
            print("Whisper failed, trying Google Speech Recognition...")
            user_input = takeCommandMic()
        
        # If both voice methods fail, offer text input
        if user_input is None:
            print("Voice input failed. Would you like to type instead? (y/n)")
            try:
                choice = input().lower().strip()
                if choice == 'y' or choice == 'yes':
                    user_input = takeCommandCMD()
                else:
                    continue
            except KeyboardInterrupt:
                user_input = takeCommandCMD()
        
        if user_input is None:
            continue
            
        # Quick local exit - check BEFORE GPT processing
        # Clean input by removing punctuation and extra whitespace
        import string
        user_clean = user_input.strip().lower().translate(str.maketrans('', '', string.punctuation))
        if user_clean in {"exit", "quit", "bye", "goodbye", "stop"}:
            bye = "Goodbye! Have a great day!"
            print(f"🤖 {bye}")
            tts.speak(bye)
            break

        # Memory commands - check BEFORE GPT processing
        user_lower = user_input.lower()
        
        # Remember commands
        if user_lower.startswith("remember that") or user_lower.startswith("remember this"):
            fact = user_input[len("remember that"):].strip() if user_lower.startswith("remember that") else user_input[len("remember this"):].strip()
            if remember_fact(fact):
                response = "I've stored that in my memory."
                print(f"🤖 {response}")
                tts.speak(response)
            else:
                response = "Sorry, I had trouble saving that to memory."
                print(f"🤖 {response}")
                tts.speak(response)
            continue
            
        # Note commands
        if user_lower.startswith("note that") or user_lower.startswith("take note"):
            note = user_input[len("note that"):].strip() if user_lower.startswith("note that") else user_input[len("take note"):].strip()
            if remember_note(note):
                response = "I've added that note."
                print(f"🤖 {response}")
                tts.speak(response)
            else:
                response = "Sorry, I couldn't save that note."
                print(f"🤖 {response}")
                tts.speak(response)
            continue
            
        # Recall commands
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
            
        # Show notes
        if "show notes" in user_lower or "what notes" in user_lower:
            notes = recall_notes()
            if notes:
                note_list = [f["content"] for f in notes]
                response = f"Here are my notes: {'; '.join(note_list)}"
                print(f"🤖 {response}")
                tts.speak(response)
            else:
                response = "I don't have any notes stored."
                print(f"🤖 {response}")
                tts.speak(response)
            continue
            
        # Preference commands
        if user_lower.startswith("set preference") or user_lower.startswith("my preference"):
            # Simple parsing: "set preference theme to dark" or "my preference is coffee"
            if " is " in user_input:
                parts = user_input.split(" is ", 1)
                key = parts[0].replace("set preference", "").replace("my preference", "").strip()
                value = parts[1].strip()
            elif " to " in user_input:
                parts = user_input.split(" to ", 1)
                key = parts[0].replace("set preference", "").strip()
                value = parts[1].strip()
            else:
                response = "I need a preference in the format 'set preference [key] to [value]' or 'my preference is [value]'"
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

        # Use GPT to decide whether to run a command or chat
        decision = gpt_decide(user_input)

        if decision["mode"] == "run":
            cmd = decision["command"]
            print(f"⚙️ Executing: {cmd}")
            out, code = exec_shell(cmd)
            if out.strip():
                print(out)
            speak_msg = f"Done. Exit code {code}."
            print(f"🤖 {speak_msg}")
            tts.speak(speak_msg)
        else:
            # Plain chat
            reply = decision["say"]
            print(f"🤖 Marvin: {reply}")
            tts.speak(reply)

if __name__ == "__main__":
    main()