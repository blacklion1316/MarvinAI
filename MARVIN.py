import pyttsx3
from datetime import datetime
import speech_recognition as sr 


class _TTS:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 200)  # Speed of speech
        self.engine.setProperty('volume', 1)  # Volume 0-1

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    

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

def main():

    # tts.change_rate(300)  # Default rate
    tts.change_voice(2)  # Default voice
    tts.speak("Hello, I am Marvin. How can I assist you today?")
    # tts.speak(f"Current time is: {time()}")  # Speak current time for reference
    # tts.speak(f"Current date is: {date()}")  # Speak current date for reference
    tts.speak(greeting())  # Speak greeting based on the time of day
    while True:
        user_input = takeCommandMic()
        if user_input and user_input.lower() in ["exit", "quit", "stop"]:
            tts.speak(greeting() + "and ")  # Speak greeting based on the time of day
            tts.speak("Goodbye! Have a great day!")
            break
        elif user_input and user_input.lower() in ["time", "current time"]:
            current_time = time()
            tts.speak(f"The current time is {current_time}.")
        elif user_input and user_input.lower() in ["date", "current date"]:
            current_date = date()
            tts.speak(f"The current date is {current_date}.")
        elif user_input and user_input.lower() in ["greeting", "hello"]:
            tts.speak(greeting())
        elif user_input and user_input.lower() in ["change voice", "voice change"]:
            tts.change_voice(1)
            tts.speak("Hello This is Marvin.")
        elif user_input and user_input.lower() in ["change voice 2", "voice change 2"]:
            tts.change_voice(2)
            tts.speak("Hello This is Farvin.")

        else:
            tts.speak(f"You said: {user_input}")
            # You can add more commands here to handle specific user inputs
            # For example, you could add commands for weather, news, etc.

if __name__ == "__main__":
    main()
    