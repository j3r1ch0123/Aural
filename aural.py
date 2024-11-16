#!/usr/bin/env python3.11
import requests
import os
import time
import gtts
import pygame
import logging
import speech_recognition as speech
from pynput import keyboard

class Aural:
    def __init__(self):
        self.listening = True
        logging.basicConfig(
            filename='/tmp/aural.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Aural initialized.")

    def hotword_detection(self, hotwords=["hey llama"]):
        recognizer = speech.Recognizer()
        with speech.Microphone() as source:
            print("Listening for hotwords...")
            recognizer.adjust_for_ambient_noise(source)
            while self.listening:
                try:
                    audio = recognizer.listen(source, timeout=None, phrase_time_limit=5)
                    text = recognizer.recognize_google(audio).lower()
                    print(f"Heard: {text}")
                    if any(hotword in text for hotword in hotwords):
                        print("Hotword detected!")
                        self.talk()  # Trigger recording for the command
                except speech.UnknownValueError:
                    continue
                except speech.RequestError as e:
                    print(f"Speech Recognition Error: {e}")
                    break

    def send_message(self, url, message):
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "dolphin-mistral",
            "messages": [{"role": "user", "content": message}],
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            text = response.json()["choices"][0]["message"]["content"]
            print("AI Response:", text)
            logging.info(f"AI Response: {text}")
            self.speak(text)
        else:
            print("Error:", response.text)
            logging.error(f"API Error: {response.text}")

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
        recognizer = speech.Recognizer()

        with speech.Microphone() as source:
            print("Listening for a command...")
            recognizer.adjust_for_ambient_noise(source)  # Adjust for background noise
            try:
                # Stop listening automatically after 5 seconds of silence or a completed phrase
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                user_input = recognizer.recognize_google(audio)
                print("You said:", user_input)
                self.send_message("http://localhost:11434/v1/chat/completions", user_input)
            except speech.UnknownValueError:
                print("Could not understand audio")
                logging.warning("Could not understand audio.")
            except speech.WaitTimeoutError:
                print("No speech detected within the timeout period.")
                logging.info("No speech detected within timeout.")
            except speech.RequestError as e:
                print("Could not request results;", e)
                logging.error(f"Speech Request Error: {e}")

if __name__ == "__main__":
    run = Aural()
    run.hotword_detection()
    
