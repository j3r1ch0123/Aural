#!/usr/bin/env python3.11
import requests
import os
import time
import gtts
import pygame
import tempfile
import logging
import speech_recognition as speech
from googletrans import Translator

class Aural:
    def __init__(self):
        self.listening = True
        logging.basicConfig(
            filename='./aural.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Aural initialized.")

    def hotword_detection(self, hotwords=["llama", "hey llama", "llama are you there", "hey llama are you there", "dolphin", "hey dolphin", "dolphin are you there", "home", "hey home", "home are you there"], target_language="es"):
        recognizer = speech.Recognizer()
        translated_hotwords = self.translate_hotwords(hotwords, target_language)

        all_hotwords = hotwords + translated_hotwords  # Combine original and translated hotwords
        model = None  # Initialize model to ensure it's always defined

        with speech.Microphone() as source:
            print("Listening for hotwords...")
            recognizer.adjust_for_ambient_noise(source)

            while self.listening:
                try:
                    audio = recognizer.listen(source, timeout=None, phrase_time_limit=5)
                    text = recognizer.recognize_google(audio).lower()
                    print(f"Heard: {text}")

                    # Check if any hotword is present in the recognized text
                    if any(hotword in text for hotword in all_hotwords):
                        print("Hotword detected!")
                        if "hey llama" in text or "llama are you there" in text or "llama" in text:
                            model = "llama3.2"
                        elif "hey dolphin" in text or "dolphin are you there" in text or "dolphin" in text:
                            model = "dolphin-mistral"
                        elif "home" in text:
                            model = "fixt/home-3b-v3"
                            self.process_home_command_with_ai(model)  # Send command to the home AI model
                        
                        if model:  # Only call talk if model is assigned
                            self.talk(model)  # Trigger recording for the command

                except speech.UnknownValueError:
                    continue  # Ignore unintelligible speech
                except speech.RequestError as e:
                    print(f"Speech Recognition Error: {e}")
                    break

    def translate_hotwords(self, hotwords, target_languages=["es", "fr"]):
        translator = Translator()
        translated_hotwords = []
        
        for lang in target_languages:
            if lang not in ['es', 'fr']:  # Add validation for language codes
                print(f"Invalid language code: {lang}")
                logging.warning(f"Invalid language code: {lang}")
                continue  # Skip unsupported languages
            
            for hotword in hotwords:
                try:
                    translation = translator.translate(hotword, dest=lang)
                    translated_hotwords.append(translation.text)
                    print(f"Translated '{hotword}' to {lang}: {translation.text}")
                except Exception as e:
                    print(f"Error translating hotword '{hotword}': {e}")
                    logging.error(f"Error translating hotword '{hotword}': {e}")
                    translated_hotwords.append(hotword)  # Fallback to original hotword if translation fails
        
        return translated_hotwords

    def send_message(self, url, message, model):
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            # Extract the AI's response
            text = response.json()["choices"][0]["message"]["content"]
            print("AI Response:", text)
            logging.info(f"AI Response: {text}")

            self.speak(text)  # Provide verbal feedback to the user

            # Now filter and process the response for Home Assistant commands
            self.process_home_command(text)  # Check if response is an automation command

        except requests.exceptions.RequestException as e:
            print("Error:", e)
            logging.error(f"API Error: {e}")

    def speak(self, text):
        tts = gtts.gTTS(text, lang="en")
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            tts.write_to_fp(temp_file)
        temp_file.close()

        # Play the generated audio
        pygame.init()
        pygame.mixer.music.load(temp_file.name)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        os.remove(temp_file.name)

    def talk(self, model):
        recognizer = speech.Recognizer()

        with speech.Microphone() as source:
            print("Listening for a command...")
            recognizer.adjust_for_ambient_noise(source)  # Adjust for background noise
            try:
                # Stop listening automatically after 5 seconds of silence or a completed phrase
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)  # Increased time limits
                user_input = recognizer.recognize_google(audio)
                print("You said:", user_input)
                self.send_message("http://localhost:11434/v1/chat/completions", user_input, model)
            except speech.UnknownValueError:
                print("Could not understand audio")
                logging.warning("Could not understand audio.")
            except speech.WaitTimeoutError:
                print("No speech detected within the timeout period.")
                logging.info("No speech detected within timeout.")
            except speech.RequestError as e:
                print("Could not request results;", e)
                logging.error(f"Speech Request Error: {e}")
    
    def home_assistant_control(self, entity_id, action="toggle"):
        url = f"http://localhost:8123/api/services/light/{action}"
        token = os.getenv("HOME_ASSISTANT_TOKEN")
        if not token:
            print("Home Assistant token not found. Please set the HOME_ASSISTANT_TOKEN environment variable.")
            logging.error("Home Assistant token not found. Please set the HOME_ASSISTANT_TOKEN environment variable.")
            return
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {"entity_id": entity_id}
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print(f"{action.capitalize()} {entity_id} successfully.")
            logging.info(f"{action.capitalize()} {entity_id} successfully.")
        except requests.exceptions.RequestException as e:
            print(f"Error controlling {entity_id}: {e}")
            logging.error(f"Error controlling {entity_id}: {e}")
    
    def process_home_command(self, command):
        command = command.lower()

        # Check if the response contains a command for Home Assistant automation
        if "turn on" in command or "turn off" in command or "toggle" in command:
            entity_id = self.extract_entity_id(command)
            if entity_id:
                if "turn on" in command:
                    self.home_assistant_control(entity_id, "turn_on")
                elif "turn off" in command:
                    self.home_assistant_control(entity_id, "turn_off")
                else:
                    self.home_assistant_control(entity_id, "toggle")
                    
        else:
            print(f"Unknown home automation command: {command}")
            logging.warning(f"Unknown home command: {command}")

    def process_home_command_with_ai(self, model):
        print("Activating home automation...")
        self.send_message("http://localhost:11434/v1/chat/completions", "Activate home automation", model)

    def extract_entity_id(self, command, action=None):
        entity_map = {
            "light": "light.living_room",
            "fan": "fan.ceiling_fan",
            "thermostat": "climate.thermostat",
            "tv": "media_player.tv",
            "speaker": "media_player.kitchen_speaker",
            "weather": "sensor.weather",
        }
        for key, entity_id in entity_map.items():
            if key in command:
                return entity_id
        print(f"Entity ID not found for command: {command}")
        logging.warning(f"Entity ID not found for {action} in command: {command}")
        return None
