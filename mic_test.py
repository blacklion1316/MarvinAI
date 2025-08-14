import speech_recognition as sr
import pyaudio

def test_pyaudio():
    """Test if PyAudio can access microphones"""
    try:
        p = pyaudio.PyAudio()
        print("PyAudio initialized successfully")
        
        # List all audio devices
        print("\nAudio Devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:  # Input devices only
                print(f"  Device {i}: {info['name']} (Inputs: {info['maxInputChannels']})")
        
        # Get default input
        default_input = p.get_default_input_device_info()
        print(f"\nDefault input device: {default_input['name']}")
        
        p.terminate()
        return True
    except Exception as e:
        print(f"PyAudio test failed: {e}")
        return False

def test_speech_recognition():
    """Test basic speech recognition setup"""
    try:
        r = sr.Recognizer()
        print("\nSpeech Recognition initialized successfully")
        
        # List microphones
        mics = sr.Microphone.list_microphone_names()
        print(f"\nSpeechRecognition found {len(mics)} microphones:")
        for i, name in enumerate(mics):
            print(f"  Mic {i}: {name}")
        
        return True
    except Exception as e:
        print(f"Speech Recognition test failed: {e}")
        return False

def test_microphone_basic():
    """Basic microphone test with very low threshold"""
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("\nBasic microphone test...")
            print("Adjusting for ambient noise (1 second)...")
            r.adjust_for_ambient_noise(source, duration=1)
            
            # Very sensitive settings
            r.energy_threshold = 50
            r.pause_threshold = 0.5
            r.dynamic_energy_threshold = False  # Disable dynamic adjustment
            
            print(f"Energy threshold: {r.energy_threshold}")
            print("Listening for 3 seconds... make ANY sound:")
            
            audio = r.listen(source, timeout=3, phrase_time_limit=2)
            print("✓ Audio detected!")
            return True
            
    except sr.WaitTimeoutError:
        print("✗ No audio detected")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("=== Microphone Diagnostic Tool ===\n")
    
    print("1. Testing PyAudio...")
    if test_pyaudio():
        print("✓ PyAudio working")
    else:
        print("✗ PyAudio failed")
        return
    
    print("\n2. Testing Speech Recognition...")
    if test_speech_recognition():
        print("✓ Speech Recognition working")
    else:
        print("✗ Speech Recognition failed")
        return
    
    print("\n3. Testing microphone capture...")
    if test_microphone_basic():
        print("✓ Microphone is working!")
    else:
        print("✗ Microphone not working")
        
        print("\nTroubleshooting tips:")
        print("- Check Windows microphone permissions")
        print("- Check if microphone is muted")
        print("- Try using a different microphone")
        print("- Check microphone volume in Windows Sound settings")

if __name__ == "__main__":
    main()
