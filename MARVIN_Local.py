import pyttsx3
import requests
import json
from datetime import datetime
import speech_recognition as sr 
import os
import dotenv

# Load environment variables from .env.dev file
dotenv.load_dotenv(".env.dev")

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"  # The model we installed in the Docker container


class _TTS:
    def __init__(self):
        self.rate = 200
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

def time():
    now = datetime.now()
    current_time = now.strftime("%I:%M %p")
    return current_time

def date():
    year = datetime.now().year
    month = datetime.now().month
    day = datetime.now().day
    date = f"{day:02d}/{month:02d}/{year}"
    return date

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

def check_ollama_connection():
    """Check if Ollama is available"""
    try:
        url = f"{OLLAMA_BASE_URL}/api/tags"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return True
    except:
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

def monitor_audio_levels():
    """Monitor audio levels to help debug microphone issues"""
    import pyaudio
    
    try:
        p = pyaudio.PyAudio()
        
        # Get default input device
        default_device = p.get_default_input_device_info()
        print(f"Default microphone: {default_device['name']}")
        
        # Open stream
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            input=True,
            frames_per_buffer=1024
        )
        
        print("Monitoring audio levels for 5 seconds... Speak now!")
        print("Audio levels (higher numbers = louder):")
        
        for i in range(50):  # Monitor for ~5 seconds
            data = stream.read(1024)
            # Convert to integers and get max amplitude
            import struct
            audio_data = struct.unpack('1024h', data)
            max_amplitude = max(audio_data)
            
            # Simple level indicator
            level = min(50, max_amplitude // 500)  # Scale down
            bar = "█" * level + "░" * (50 - level)
            print(f"\r{bar} {max_amplitude:5d}", end="", flush=True)
            
        print("\nAudio monitoring complete.")
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
    except Exception as e:
        print(f"Audio monitoring failed: {e}")
        print("This is normal - just means we can't monitor levels")

def chat_with_ollama(prompt):
    """Send a prompt to Ollama and get a response"""
    try:
        url = f"{OLLAMA_BASE_URL}/api/generate"
        
        data = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "Sorry, I couldn't generate a response.")
        
    except requests.exceptions.ConnectionError:
        return "Sorry, I cannot connect to Ollama. Make sure the Docker containers are running."
    except requests.exceptions.Timeout:
        return "Sorry, the request timed out. The AI model might be processing."
    except Exception as e:
        return f"Sorry, there was an error: {str(e)}"

def main():
    # Check Ollama connection
    print("Checking Ollama connection...")
    if check_ollama_connection():
        tts.speak("Ollama AI is ready.")
        print("✓ Ollama is available")
    else:
        tts.speak("Warning: Cannot connect to Ollama. Make sure Docker containers are running.")
        print("✗ Ollama is not available")

    # Test microphone
    print("Testing microphone...")
    if test_microphone():
        print("✓ Microphone is working")
    else:
        print("✗ Microphone test failed - trying audio level monitoring...")
        monitor_audio_levels()

    tts.change_voice(1)  # Female voice (Zira) - do this first
    tts.change_rate(300)  # Then set the rate
    tts.speak("How can I assist you today?")
    # tts.speak(f"Current time is: {time()}")  # Speak current time for reference
    # tts.speak(f"Current date is: {date()}")  # Speak current date for reference
    tts.speak(greeting())  # Speak greeting based on the time of day
    
    while True:
        print("\nWaiting for voice input... (Press Ctrl+C to use text input)")
        user_input = takeCommandMic()
        
        # If voice input failed, offer text input as fallback
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
            
        user_input = user_input.lower()
        if "exit" in user_input or "quit" in user_input:
            tts.speak("Goodbye! Have a great day!")
            break
        else:
            response = chat_with_ollama(user_input)
            print(f"Ollama Response: {response}")
            tts.speak(response)

if __name__ == "__main__":
    main()
