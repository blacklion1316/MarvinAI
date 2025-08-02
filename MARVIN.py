import pyttsx3
import openai
from datetime import datetime
import speech_recognition as sr 
import os
import dotenv
# Load environment variables from .env file
dotenv.load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

class _TTS:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 200)  # Speed of speech
        self.engine.setProperty('volume', 1)  # Volume 0-1

    def speak(self, text):
        engine = pyttsx3.init()
        engine.setProperty('rate', self.engine.getProperty('rate'))
        engine.setProperty('volume', self.engine.getProperty('volume'))
        voices = engine.getProperty('voices')
        # Try to match the current voice
        current_voice = self.engine.getProperty('voice')
        for v in voices:
            if v.id == current_voice:
                engine.setProperty('voice', v.id)
                break
        engine.say(text)
        engine.runAndWait()

    

    def get_voices(self, voice_id=None):
        voices = self.engine.getProperty('voices')
        if voice_id == 1:
            self.engine.setProperty('voice', voices[0].id)
            self.speak("Hello This is Marvin")
        elif voice_id == 2:
            self.engine.setProperty('voice', voices[1].id)
            self.speak("Hello This is Farvin")

    def change_voice(self, voice_id):
        self.get_voices(voice_id)

    def change_rate(self, rate):
        self.engine.setProperty('rate', rate)

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

    # tts.change_rate(300)  # Default rate
    tts.change_voice(2)  # Default voice
    tts.speak("Hello, I am Marvin. How can I assist you today?")
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