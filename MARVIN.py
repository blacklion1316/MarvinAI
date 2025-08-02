import pyttsx3
import openai
from datetime import datetime
import speech_recognition as sr 
import os
import dotenv

# Load environment variables from .env.dev file
dotenv.load_dotenv(".env.dev")

openai.api_key = os.getenv("OPENAI_API_KEY")


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
    with sr.Microphone() as source:
        print("Listening...")
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source)
    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-US')
        print(f"You said: {query}")
        return query
    except Exception as e:
        print("Sorry, I did not understand that.")
        return None



def chat_with_gpt(prompt):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",  # Updated model name
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def main():

    tts.change_voice(1)  # Female voice (Zira) - do this first
    # tts.change_rate(300)  # Then set the rate
    tts.speak("How can I assist you today?")
    # tts.speak(f"Current time is: {time()}")  # Speak current time for reference
    # tts.speak(f"Current date is: {date()}")  # Speak current date for reference
    tts.speak(greeting())  # Speak greeting based on the time of day
    while True:
        user_input = takeCommandMic()
        if user_input is None:
            continue
        user_input = user_input.lower()
        if "exit" in user_input or "quit" in user_input:
            tts.speak("Goodbye! Have a great day!")
            break
        else:
            response = chat_with_gpt(user_input)
            print(f"GPT-4 Response: {response}")
            tts.speak(response)

if __name__ == "__main__":
    main()