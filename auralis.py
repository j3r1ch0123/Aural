# Import necessary libraries
import requests
import time
import gtts
import pygame
import speech_recognition as speech

def send_message(url, message):
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "dolphin-mistral",
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
    }

    # Send the API request and get the response
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        # Get the text from the response
        text = response.json()["choices"][0]["message"]["content"]
        print("AI Response:", text)

        # Play the response audio
        speak(text)
    else:
        print("Error:", response.text)

def speak(text):
    tts = gtts.gTTS(text, lang="en")
    tts.save("output.mp3")
    pygame.init()
    pygame.mixer.music.load("output.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
        
def talk():
    recognizer = speech.Recognizer()
    with speech.Microphone() as source:
        print("Press Enter to start recording...")
        input()  # Wait for Enter key press to start recording
        print("Listening... Press Enter again to stop recording.")

        # Start recording
        audio = recognizer.listen(source, phrase_time_limit=None)  # No phrase time limit

    try:
        user_input = recognizer.recognize_google(audio)
        print("You said:", user_input)
        return user_input
    except speech.UnknownValueError:
        print("Could not understand audio")
        return None
    except speech.RequestError as e:
        print("Could not request results;", e)
        return None


def main():
    url = "http://localhost:11434/v1/chat/completions" # Change this depending on the server IP
    while True:
        message = talk()
        if message:  # Only proceed if user input was successfully recognized
            send_message(url, message)
        time.sleep(5)

if __name__ == "__main__":
    main()
