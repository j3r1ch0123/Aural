#!/usr/bin/env python3.11
import requests
import os
import time
import gtts
import pygame
import speech_recognition as sr
from pynput import keyboard
import threading

class Aural:
    def __init__(self):
        self.listening = True  # Controls whether hotword detection is active

    def send_message(self, url, message):
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "llama3.2",  # Change this if you want to interact with another model
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
            self.speak(text)
        else:
            print("Error:", response.text)

    def hotwords_detection(self, hotwords=["hey llama"], callback=None):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening for hotwords...")
            recognizer.adjust_for_ambient_noise(source)  # Adjust for background noise
            while self.listening:
                try:
                    audio = recognizer.listen(source, timeout=None, phrase_time_limit=5)
                    text = recognizer.recognize_google(audio).lower()
                    print(f"Heard: {text}")
                    for hotword in hotwords:
                        if hotword in text:
                            print("Hotword detected!")
                            self.listening = False  # Pause hotword detection
                            if callback:
                                callback()
                            self.listening = True  # Reactivate hotword detection after callback
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    print(f"Speech Recognition Error: {e}")
                    break

    def speak(self, text):
        tts = gtts.gTTS(text, lang="en")
        tts.save("output.mp3")
        pygame.init()
        pygame.mixer.music.load("output.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        os.remove("output.mp3")

    def talk(self):
        recognizer = sr.Recognizer()
        stop_listening = False

        def on_press(key):
            nonlocal stop_listening
            if key == keyboard.Key.enter:
                stop_listening = True
                return False  # Stop listener

        # Start a listener for the Enter key
        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        with sr.Microphone() as source:
            print("Listening... Press Enter to stop recording.")
            audio = recognizer.listen(source, phrase_time_limit=None)
            while not stop_listening:
                pass  # Wait for the Enter key press

        listener.join()  # Ensure listener ends cleanly

        try:
            user_input = recognizer.recognize_google(audio)
            print("You said:", user_input)
            return user_input
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except sr.RequestError as e:
            print("Could not request results;", e)
            return None

    def main(self):
        url = "http://localhost:11434/v1/chat/completions"  # Change this depending on the server IP

        def start_conversation():
            # Start recording and process the user's input
            message = self.talk()
            if message:
                self.send_message(url, message)

        # Run hotword detection in a separate thread
        hotword_thread = threading.Thread(target=self.hotwords_detection, args=(["hey llama"], start_conversation))
        hotword_thread.daemon = True
        hotword_thread.start()

        print("Hotword detection is running in the background...")
        try:
            while True:
                time.sleep(1)  # Keep the main thread alive
        except KeyboardInterrupt:
            print("\nExiting...")
            self.listening = False  # Stop hotword detection thread

if __name__ == "__main__":
    run = Aural()
    run.main()
