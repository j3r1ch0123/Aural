#!/usr/bin/env python3.11
import requests
import os
import time
import gtts
import pygame
import speech_recognition as speech
from pynput import keyboard

def send_message(url, message):
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "llama3.2", # Change this if you want to interact with another model
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
    os.remove("output.mp3")
        
def talk():
    recognizer = speech.Recognizer()
    stop_listening = False

    def on_press(key):
        nonlocal stop_listening
        if key == keyboard.Key.enter:
            stop_listening = True
            return False  # Stop listener

    # Start a listener for the Enter key
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    with speech.Microphone() as source:
        print("Listening... Press Enter to stop recording.")
        audio = recognizer.listen(source, phrase_time_limit=None)
        while not stop_listening:
            pass  # Wait for the Enter key press

    listener.join()  # Ensure listener ends cleanly

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
        # Check if the user has a microphone or not
        if not speech.Microphone.list_microphone_names():
            print("No microphone found. Please type your message:")
            message = input()
            send_message(url, message)
            continue
        else:
            print("Microphone found. Starting conversation...")
            message = talk()

        if message:  # Only proceed if user input was successfully recognized
            send_message(url, message)
        time.sleep(5)

if __name__ == "__main__":
    main()
