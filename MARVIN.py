import pyttsx3


class _TTS:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 200)  # Speed of speech
        self.engine.setProperty('volume', 1)  # Volume 0-1

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    

    def getVoices(self, voice_id=None):
        voices = self.engine.getProperty('voices')
        if voice_id == 1:
            self.engine.setProperty('voice', voices[0].id)
        elif voice_id == 2:
            self.engine.setProperty('voice', voices[1].id)


    def changeVoice(self, voice_id):
        self.getVoices(voice_id)

    def changeRate(self, rate):
        self.engine.setProperty('rate', rate)

tts = _TTS()

def time():
    from datetime import datetime
    now = datetime.now()
    current_time = now.strftime("%I:%M %p")
    return current_time



def main():

    tts.changeRate(200)  # Default rate
    tts.changeVoice(1)  # Default voice
    tts.speak("Hello, I am JARVIS. How can I assist you today?")
    tts.speak(f"Current time is: {time()}")  # Speak current time for reference

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "stop"]:
            tts.speak("Goodbye! Have a great day!")
            break
        else:
            tts.speak(f"You said: {user_input}")


if __name__ == "__main__":
    main()
    