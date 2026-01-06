import os
import time
import threading
import subprocess

import speech_recognition as sr
import pyttsx3
from dotenv import load_dotenv
from groq import Groq

# =========================================
# CONFIG
# =========================================
# Set this to False if you want to TYPE instead of speaking
USE_VOICE_INPUT = True

# =========================================
# 1. Load API key from .env
# =========================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY not found.\n"
        "Create a .env file in this folder with:\n\n"
        "GROQ_API_KEY=gsk_your_key_here\n"
    )

client = Groq(api_key=GROQ_API_KEY)

# =========================================
# 2. Initialize TTS (using Windows PowerShell)
# =========================================
print("[DEBUG] TTS using Windows PowerShell Speech Synthesis")


def speak(text: str):
    """Make TARS speak the given text and print it using Windows PowerShell."""
    print(f"TARS: {text}")
    
    # Escape double quotes in text
    text_escaped = text.replace('"', '`"')
    
    # Use Windows PowerShell to play audio with normal settings
    ps_command = f'''
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 1
$synth.Volume = 100
$voices = $synth.GetInstalledVoices()
foreach ($voice in $voices) {{
    if ($voice.VoiceInfo.Name -like "*male*" -or $voice.VoiceInfo.Name -like "*David*") {{
        $synth.SelectVoice($voice.VoiceInfo.Name)
        break
    }}
}}
$synth.Speak("{text_escaped}")
'''
    
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            timeout=30
        )
    except Exception as e:
        print(f"Voice error: {e}")


# =========================================
# 3. TARS brain (Groq API)
# =========================================
def TARS_respond(prompt: str) -> str:
    """Send the user's message to Groq and return TARS's reply."""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # ✅ current Groq model
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are TARS from the movie Interstellar. "
                        "You are helpful, clear, and slightly humorous, "
                        "but you always give straightforward answers."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        reply = response.choices[0].message.content
        return reply.strip()

    except Exception as e:
        print("TARS (Groq) error:", e)
        return "I'm having trouble reaching my processing core right now."


# =========================================
# 4. Speech recognition
# =========================================
recognizer = sr.Recognizer()
# Increase how long it waits for the service to respond (seconds)
recognizer.operation_timeout = 10  # or None for no timeout


def listen_to_user() -> str | None:
    """
    Listen to user through the microphone and return recognized text.
    Returns None if nothing understandable was heard or if network fails.
    """
    try:
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source)

        print("Recognizing...")
        try:
            # Use Indian English recognition
            text = recognizer.recognize_google(audio, language="en-IN")
            print(f"You said: {text}")
            return text

        except sr.UnknownValueError:
            print("Sorry, I could not understand what you said.")
            speak("Sorry, I didn't catch that. Could you repeat?")
            return None

        except sr.RequestError as e:
            # Problems contacting Google Speech service
            print(f"Speech service error: {e}")
            speak("I'm having trouble accessing the speech recognition service.")
            return None

        except TimeoutError as e:
            # Network timeout (like WinError 10060)
            print(f"Speech recognition timed out: {e}")
            speak("The speech service took too long to respond. Please try again.")
            return None

        except Exception as e:
            # Any other unexpected error
            print(f"Unexpected speech error: {e}")
            speak("Something went wrong while trying to understand you.")
            return None

    except OSError as e:
        # No microphone or audio device problem
        print(f"Microphone error: {e}")
        speak("I can't access the microphone right now.")
        return None


# =========================================
# 5. Keyboard fallback input
# =========================================
def listen_by_text() -> str:
    """Fallback: get user input from keyboard."""
    return input("You (type): ")


# =========================================
# 6. Main chat loop
# =========================================
if __name__ == "__main__":
    print("Hello! I'm TARS. How can I assist you today?")
    print("Say something or say 'exit' to end the session.")
    if not USE_VOICE_INPUT:
        print("Voice input is OFF. Type your messages instead.")

    speak("Hello! I'm TARS. How can I assist you today?")

    while True:
        if USE_VOICE_INPUT:
            user_input = listen_to_user()
            if user_input is None:
                # Nothing understood or there was an error – retry
                continue
        else:
            user_input = listen_by_text()

        # Exit commands
        if user_input.lower().strip() in ["exit", "quit", "bye", "goodbye", "stop", "terminate the session"]:
            speak("Goodbye. Shutting down my humor settings.")
            print("Session ended.")
            break

        # Get TARS response from Groq
        response = TARS_respond(user_input)

        # Speak the response
        speak(response)

        time.sleep(0.5)
