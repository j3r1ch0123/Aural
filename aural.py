#!/usr/bin/env python3.11
import requests
import os
import sys
import time
import gtts
import tempfile
import logging
import pygame
import threading
import tkinter as tk
import speech_recognition as sr
from googletrans import Translator

class Aural:
    def __init__(self):
        self.listening = True
        self.lock = threading.Lock()
        self.home_assistant_token = None
        self.home_assistant_url = None
        pygame.mixer.init()
        logging.basicConfig(
            filename='./aural.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Aural initialized.")

    def hotword_detection(self, hotwords):
        recognizer = sr.Recognizer()
        print("Starting hotword detection...")

        try:
            with sr.Microphone() as source:
                print("Adjusting for ambient noise...")
                recognizer.adjust_for_ambient_noise(source)
                print("Listening for hotwords...")

                while self.listening:
                    with self.lock:
                        try:
                            # Listen for audio input
                            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
                            text = recognizer.recognize_google(audio).lower()
                            print(f"Heard: {text}")

                            # Check for hotwords
                            if any(hotword in text for hotword in hotwords):  # Use `hotwords` parameter
                                print("Hotword detected!")

                                if "hey llama" in text or "llama are you there" in text or "llama" in text:
                                    model = "llama3.2"
                                    self.talk(model)

                                elif "hey dolphin" in text or "dolphin are you there" in text or "dolphin" in text:
                                    model = "dolphin-mistral"
                                    self.talk(model)

                                elif "exit" in text:
                                    print("Exiting hotword detection.")
                                    self.listening = False
                                    break  # Exit the loop

                                else:
                                    print("No matching hotword. Forwarding to API.")
                                    model = "default-model"  # Default fallback model
                                    self.talk(model)

                        except sr.WaitTimeoutError:
                            print("Listening timed out, no speech detected.")
                        except sr.UnknownValueError:
                            print("Could not understand the audio.")
                        except Exception as e:
                            print(f"Error during hotword detection: {e}")
                            logging.error(f"Hotword detection error: {e}")
                            time.sleep(0.1)  # Small delay to prevent blocking
        except Exception as e:
            print(f"Error with microphone: {e}")
            logging.error(f"Microphone error: {e}")

    def translate_hotwords(self, hotwords, target_languages=["es", "fr"]):
        translator = Translator()
        translated_cache = {}
        translated_hotwords = []

        for lang in target_languages:
            if lang in translated_cache:
                # Use cached translations
                translated_hotwords.extend(translated_cache[lang])
                continue

            lang_translations = []
            for hotword in hotwords:
                try:
                    translation = translator.translate(hotword, dest=lang)
                    lang_translations.append(translation.text)
                    print(f"Translated '{hotword}' to {lang}: {translation.text}")
                except Exception as e:
                    print(f"Error translating hotword '{hotword}': {e}")
                    logging.error(f"Error translating hotword '{hotword}': {e}")
                    lang_translations.append(hotword)

            # Cache translations for this language
            translated_cache[lang] = lang_translations
            translated_hotwords.extend(lang_translations)

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
        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            print("Listening for a command...")
            recognizer.adjust_for_ambient_noise(source)  # Adjust for background noise
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)  # Increased time limits
                user_input = recognizer.recognize_google(audio)
                print("You said:", user_input)
                self.send_message("http://localhost:11434/v1/chat/completions", user_input, model)
            except sr.UnknownValueError:
                print("Could not understand audio")
                logging.warning("Could not understand audio.")
            except sr.WaitTimeoutError:
                print("No speech detected within the timeout period.")
                logging.info("No speech detected within timeout.")
            except sr.RequestError as e:
                print("Could not request results;", e)
                logging.error(f"Speech Request Error: {e}")
    
    def home_assistant_control(self, entity_id, action="toggle"):
        url = f"http://localhost:8123/api/services/light/{action}"
        if not self.token:
            print("Home Assistant token not found. Please set the HOME_ASSISTANT_TOKEN environment variable.")
            logging.error("Home Assistant token not found. Please set the HOME_ASSISTANT_TOKEN environment variable.")
            return
        
        headers = {
            "Authorization": f"Bearer {self.token}",
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
        elif "weather" in command:
            self.handle_weather_query(command)
        else:
            logging.warning(f"Unknown home command: {command}")

    def handle_weather_query(self, command):
        """Handles weather queries by fetching data from Home Assistant."""
        weather_entity = "sensor.weather"  # Change this to your actual weather entity

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(f"{self.home_assistant_url}/{weather_entity}", headers=headers)
            response.raise_for_status()

            weather_data = response.json()
            if "state" not in weather_data:
                raise ValueError("Weather entity is missing state information.")

            # Extract relevant data
            temperature = weather_data["state"]
            attributes = weather_data.get("attributes", {})
            condition = attributes.get("condition", "not available")
            humidity = attributes.get("humidity", "not available")

            weather_report = (
                f"The current temperature is {temperature}°F with {condition}. "
                f"Humidity is {humidity}%."
            )
            print(weather_report)
            logging.info(weather_report)
            self.speak(weather_report)

        except (requests.exceptions.RequestException, ValueError) as e:
            error_message = f"Error fetching weather: {e}"
            print(error_message)
            logging.error(error_message)
            self.speak("Sorry, I couldn't fetch the weather.")

    def process_home_command_with_ai(self, model):
        print("Activating home automation...")
        logging.info("Activating home automation...")
        # Use previous methods to control Home Assistant
        self.home_assistant_control("light.living_room", "turn_on")
        self.home_assistant_control("fan.ceiling_fan", "turn_on")
        # Listen for a command
        self.talk(model)

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

class AuralThread:

    def __init__(self, hotwords, token, home_assistant_url):
        super().__init__()
        self.hotwords = hotwords
        self.token = token
        self.home_assistant_url = home_assistant_url

    def run(self):
        aural = Aural()
        aural.home_assistant_token = self.token
        aural.home_assistant_url = self.home_assistant_url
        self.log_signal.emit("Initializing Aural...")
        # Make sure the hotword detection loop is active
        aural.hotword_detection(hotwords=self.hotwords)
        self.log_signal.emit("Hotword detection stopped.")

class ConsoleStream:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        # Use the `after` method to update the text widget from the main thread
        self.text_widget.after(0, self._insert_text, text)

    def _insert_text(self, text):
        self.text_widget.insert(tk.END, text + "\n")
        self.text_widget.see(tk.END)  # Auto-scroll to the bottom

    def flush(self):
        pass

    def close(self):
        pass

class AuralInterface:
    def __init__(self):
        # Create the main window
        self.window = tk.Tk()
        self.window.title("Aural Interface")

        # Create a label for the title
        title_label = tk.Label(self.window, text="Aural Interface", font=("Arial", 16))
        title_label.pack(pady=10)

        # Create a button to start Aural
        start_button = tk.Button(self.window, text="Start Aural", command=self.start_aural)
        start_button.pack(pady=10)

        # Create a button to stop Aural
        stop_button = tk.Button(self.window, text="Stop Aural", command=self.stop_aural)
        stop_button.pack(pady=10)

        # Text widget for logs
        self.text_widget = tk.Text(self.window, wrap=tk.WORD, state=tk.NORMAL)
        self.text_widget.pack(expand=True, fill=tk.BOTH)
        
        # Console redirection
        sys.stdout = ConsoleStream(self.text_widget)

        # Start Aural in a separate thread
        self.aural = Aural()
        self.hotwords = ["hey llama", "llama"]
        threading.Thread(
            target=self.aural.hotword_detection,
            args=(self.hotwords,),
            daemon=True
        ).start()

    def start_aural(self):
        print("Starting Aural...")
        threading.Thread(
            target=self.aural.hotword_detection,
            args=(self.hotwords,),
            daemon=True
        ).start()

    def stop_aural(self):
        print("Stopping Aural...")
        self.aural.listening = False  # Stop the hotword detection loop
        # Stop the Aural thread
        exit()

    def run(self):
        self.window.mainloop()

# Create and run the GUI
aural_interface = AuralInterface()
aural_interface.run()
