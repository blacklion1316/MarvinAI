import pyttsx3
import requests
import json
from datetime import datetime
import speech_recognition as sr 
import os
import subprocess
import time
import dotenv
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables from .env.dev file
dotenv.load_dotenv(".env.dev")

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "gpt-oss:20b"  # The 20B parameter model we installed in the Docker container

# Gmail API configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.modify']


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

class GmailManager:
    def __init__(self):
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        token_path = 'token.json'
        credentials_path = 'credentials.json'
        
        # Load existing token
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # If there are no valid credentials, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    print("❌ Gmail credentials.json file not found!")
                    print("📋 Please follow these steps:")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Create a new project or select existing")
                    print("3. Enable Gmail API")
                    print("4. Create OAuth 2.0 credentials")
                    print("5. Download credentials.json to this folder")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception as e:
            print(f"❌ Failed to authenticate with Gmail: {e}")
            return False
    
    def get_recent_emails(self, count=5):
        """Get recent emails"""
        try:
            results = self.service.users().messages().list(
                userId='me', maxResults=count).execute()
            messages = results.get('messages', [])
            
            emails = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id']).execute()
                
                # Extract email details
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                # Extract body
                body = self._extract_body(msg['payload'])
                
                emails.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body[:500] + '...' if len(body) > 500 else body  # Truncate long emails
                })
            
            return emails
        except Exception as e:
            print(f"❌ Failed to get emails: {e}")
            return []
    
    def _extract_body(self, payload):
        """Extract email body from payload"""
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        elif payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        return body
    
    def send_email(self, to, subject, body, reply_to_id=None):
        """Send an email"""
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if reply_to_id:
                # Get original message for threading
                original = self.service.users().messages().get(
                    userId='me', id=reply_to_id).execute()
                headers = original['payload'].get('headers', [])
                message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), None)
                if message_id:
                    message['In-Reply-To'] = message_id
                    message['References'] = message_id
            
            message.attach(MIMEText(body, 'plain'))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = {'raw': raw_message}
            
            result = self.service.users().messages().send(
                userId='me', body=send_message).execute()
            
            return True, result['id']
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False, str(e)
    
    def search_emails(self, query):
        """Search emails by query"""
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=10).execute()
            messages = results.get('messages', [])
            
            emails = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id']).execute()
                
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                
                emails.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender
                })
            
            return emails
        except Exception as e:
            print(f"❌ Failed to search emails: {e}")
            return []

# Initialize Gmail manager
gmail = None
try:
    gmail = GmailManager()
    if gmail.service:
        print("✅ Gmail integration ready!")
    else:
        print("⚠️ Gmail integration not available")
except Exception as e:
    print(f"⚠️ Gmail initialization failed: {e}")

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
        
        response = requests.post(url, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "Sorry, I couldn't generate a response.")
        
    except requests.exceptions.ConnectionError:
        return "Sorry, I cannot connect to Ollama. Make sure the Docker containers are running."
    except requests.exceptions.Timeout:
        return "Sorry, the request timed out. The AI model might be processing."
    except Exception as e:
        return f"Sorry, there was an error: {str(e)}"

def handle_check_emails():
    """Handle checking recent emails"""
    if not gmail or not gmail.service:
        tts.speak("Gmail is not available. Please check your credentials.")
        return
    
    tts.speak("Checking your recent emails...")
    emails = gmail.get_recent_emails(5)
    
    if not emails:
        tts.speak("No recent emails found or unable to access Gmail.")
        return
    
    tts.speak(f"You have {len(emails)} recent emails.")
    
    for i, email in enumerate(emails, 1):
        print(f"\n📧 Email {i}:")
        print(f"From: {email['sender']}")
        print(f"Subject: {email['subject']}")
        print(f"Date: {email['date']}")
        print(f"Preview: {email['body'][:100]}...")
        
        # Speak the email details
        tts.speak(f"Email {i}. From {email['sender']}. Subject: {email['subject']}")
        
        # Ask if user wants to hear the content
        tts.speak("Would you like me to read this email? Say yes or no.")
        response = takeCommandMic()
        if response and ("yes" in response.lower() or "read" in response.lower()):
            # Use AI to summarize long emails
            if len(email['body']) > 200:
                summary_prompt = f"Summarize this email in 2-3 sentences: {email['body']}"
                summary = chat_with_ollama(summary_prompt)
                tts.speak(f"Email summary: {summary}")
            else:
                tts.speak(f"Email content: {email['body']}")
        
        if i < len(emails):
            tts.speak("Next email?")
            response = takeCommandMic()
            if response and ("no" in response.lower() or "stop" in response.lower()):
                break

def handle_send_email():
    """Handle sending emails"""
    if not gmail or not gmail.service:
        tts.speak("Gmail is not available. Please check your credentials.")
        return
    
    tts.speak("Who would you like to send an email to? Please say the email address.")
    to_email = takeCommandMic()
    
    if not to_email:
        tts.speak("I didn't catch the email address. Please try again.")
        return
    
    tts.speak("What is the subject of your email?")
    subject = takeCommandMic()
    
    if not subject:
        tts.speak("I didn't catch the subject. Please try again.")
        return
    
    tts.speak("Please dictate your email message. Say 'finish message' when you're done.")
    message_parts = []
    
    while True:
        message_part = takeCommandMic()
        if not message_part:
            continue
        
        if "finish message" in message_part.lower():
            break
        
        message_parts.append(message_part)
        tts.speak("Continue, or say 'finish message' when done.")
    
    full_message = " ".join(message_parts)
    
    # Confirm before sending
    tts.speak(f"Ready to send email to {to_email} with subject {subject}. Should I send it?")
    confirmation = takeCommandMic()
    
    if confirmation and ("yes" in confirmation.lower() or "send" in confirmation.lower()):
        success, result = gmail.send_email(to_email, subject, full_message)
        if success:
            tts.speak("Email sent successfully!")
        else:
            tts.speak(f"Failed to send email: {result}")
    else:
        tts.speak("Email cancelled.")

def handle_search_emails():
    """Handle searching emails"""
    if not gmail or not gmail.service:
        tts.speak("Gmail is not available. Please check your credentials.")
        return
    
    tts.speak("What would you like to search for in your emails?")
    search_query = takeCommandMic()
    
    if not search_query:
        tts.speak("I didn't catch your search query. Please try again.")
        return
    
    tts.speak(f"Searching for emails containing '{search_query}'...")
    emails = gmail.search_emails(search_query)
    
    if not emails:
        tts.speak("No emails found matching your search.")
        return
    
    tts.speak(f"Found {len(emails)} emails matching your search.")
    
    for i, email in enumerate(emails, 1):
        print(f"\n🔍 Search Result {i}:")
        print(f"From: {email['sender']}")
        print(f"Subject: {email['subject']}")
        
        tts.speak(f"Result {i}. From {email['sender']}. Subject: {email['subject']}")
        
        if i >= 5:  # Limit to first 5 results for voice
            tts.speak("Showing first 5 results. Check the screen for more.")
            break

def run_local_command(command):
    try:
        result = subprocess.check_output(command, shell=True, text=True)
        return result.strip()
    except Exception as e:
        return f"Error running command: {e}"




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
    tts.change_rate(200)  # Then set the rate
    tts.speak("How can I assist you today?")
    # tts.speak(f"Current time is: {get_current_time()}")  # Speak current time for reference
    # tts.speak(f"Current date is: {date()}")  # Speak current date for reference
    tts.speak(greeting())  # Speak greeting based on the time of day
    
    while True:
        input("\n➡ Press Enter to speak...")
        time.sleep(0.3)
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
        elif gmail and ("check email" in user_input or "read email" in user_input):
            handle_check_emails()
        elif gmail and ("send email" in user_input):
            handle_send_email()
        elif gmail and ("search email" in user_input):
            handle_search_emails()
        elif "run command" in user_input or "execute command" in user_input:
            command = user_input.split(" ", 2)[2]  # Get the command part
            result = run_local_command(command)
            print(f"Command Output: {result}")
            tts.speak(result)
        else:
            response = chat_with_ollama(user_input)
            print(f"Ollama Response: {response}")
            tts.speak(response)

if __name__ == "__main__":
    main()
