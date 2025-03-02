#!/usr/bin/env python3.11
import requests
import asyncio
import re
import os
import sys
import time
import json
import gtts
import tempfile
import logging
import pygame
import threading
import geocoder
import python_weather
import tkinter as tk
import speech_recognition as sr
from geopy.geocoders import Nominatim
from datetime import datetime
from deep_translator import GoogleTranslator
from ollama_python.endpoints import GenerateAPI, ModelManagementAPI

from typing import Optional, List, Dict, Any
from dataclasses import dataclass

class Config:
    def __init__(self):
        self.SPEECH_TIMEOUT = 5  # Timeout for speech detection
        self.PHRASE_TIME_LIMIT = 10  # Maximum phrase duration
        self.HOTWORDS = {
            'llama': ['hey llama', 'llama', 'llama are you there'],
            'dolphin': ['hey dolphin', 'dolphin', 'dolphin are you there'],
            'deepseek': ['hey deepseek', 'deepseek', 'deepseek are you there', 'deep']
        }
        self.SUPPORTED_MODELS = {
            'llama': type('Model', (), {'name': 'llama'}),
            'dolphin': type('Model', (), {'name': 'dolphin'}),
            'deepseek': type('Model', (), {'name': 'deepseek'})
        }

config = Config()

@dataclass
class AIResponse:
    """Data class to hold AI response information"""
    text: str
    status_code: int

class Aural:
    """Main class for the Aural AI assistant.
    
    Handles voice recognition, AI model interaction, and home automation control.
    Supports multiple AI models and provides both voice and text interfaces.
    """
    
    def __init__(self) -> None:
        """Initialize the Aural assistant with necessary components and configurations."""
        self.listening: bool = True
        self.lock: threading.Lock = threading.Lock()
        self.home_assistant_token: Optional[str] = None
        self.home_assistant_url: Optional[str] = None
        pygame.mixer.init()

        # Configure logging
        self._setup_logging()

        # Hotword detection configuration
        self.config = config

        self.home_assistant_control = HomeAssistantControl()
        
    def _setup_logging(self) -> None:
        """Configure logging settings for the application."""
        logging.basicConfig(
            filename='./aural.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Aural initialized.")

    def hotword_detection(self, hotwords: List[str]) -> None:
        """Listen for hotwords and trigger appropriate model responses.
        
        Args:
            hotwords: List of wake words to listen for
        """
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
                            audio = recognizer.listen(
                                source, 
                                timeout=config.SPEECH_TIMEOUT, 
                                phrase_time_limit=config.PHRASE_TIME_LIMIT
                            )
                            text = recognizer.recognize_google(audio).lower()

                            # Check for hotwords
                            if any(hotword in text for hotword in hotwords):
                                print("Hotword detected!")
                                
                                # Find matching model from config
                                selected_model = None
                                for model_name, wake_words in config.HOTWORDS.items():
                                    if any(word in text for word in wake_words):
                                        selected_model = config.SUPPORTED_MODELS[model_name].name
                                        break
                                
                                if "exit" in text:
                                    print("Exiting hotword detection.")
                                    self.listening = False
                                    break

                                # Use default model if no specific match found
                                if not selected_model:
                                    print("No matching hotword. Using default model.")
                                    selected_model = config.SUPPORTED_MODELS["llama"].name
                                
                                self.talk(selected_model)

                        except sr.WaitTimeoutError:
                            print("Listening timed out, no speech detected.")
                        except sr.UnknownValueError:
                            print("Could not understand the audio.")
                        except sr.RequestError as e:
                            print(f"Error during speech recognition: {e}")
                            logging.error(f"Speech recognition error: {e}")
                        except Exception as e:
                            print(f"Error during hotword detection: {e}")
                            logging.error(f"Hotword detection error: {e}")
                            time.sleep(0.1)  # Small delay to prevent blocking

        except Exception as e:
            print(f"Error with microphone: {e}")
            logging.error(f"Microphone error: {e}")

    def translate_hotwords(self, hotwords: List[str], target_languages: List[str] = None) -> List[str]:
        """Translate hotwords into specified target languages.
        
        Args:
            hotwords: List of wake words to translate
            target_languages: List of language codes to translate to. Defaults to ['es', 'fr']
            
        Returns:
            List[str]: List of translated hotwords
        """
        if target_languages is None:
            target_languages = ["es", "fr"]
            
        translator = GoogleTranslator()
        translated_cache: Dict[str, List[str]] = {}
        translated_hotwords: List[str] = []

        for lang in target_languages:
            if lang in translated_cache:
                # Use cached translations
                translated_hotwords.extend(translated_cache[lang])
                continue

            lang_translations: List[str] = []
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

    def send_message(self, url: str, message: str, model: str) -> Optional[int]:
        """Send a message to the AI model and handle the streaming response.
        
        Args:
            url: The API endpoint URL
            message: The user's message to send to the AI
            model: The name of the AI model to use
            
        Returns:
            Optional[int]: The HTTP status code if successful, None if an error occurred
        """
        try:
            response = self._make_api_request(url, message, model)
            response_text = self._process_streaming_response(response, model)
            self._handle_response_actions(response_text)
            return response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            print(f"Error: {e}")
            return None
            
    def _make_api_request(self, url: str, message: str, model: str) -> requests.Response:
        """Make the API request to the AI model.
        
        Args:
            url: The API endpoint URL
            message: The user's message
            model: The AI model name
            
        Returns:
            requests.Response: The response object from the API
        """
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "stream": True
        }
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        return response
    
    def _process_streaming_response(self, response: requests.Response, model: str) -> str:
        """Process the streaming response from the AI model.
        
        Args:
            response: The streaming response from the API
            model: The AI model name
            
        Returns:
            str: The accumulated response text
        """
        accumulated_text = ""
        
        for line in response.iter_lines():
            if not line:
                continue
                
            try:
                chunk = self._parse_response_chunk(line)
                if chunk.get('done'):
                    break
                    
                if 'response' in chunk:
                    text_chunk = chunk['response']
                    accumulated_text += text_chunk
                    self._display_chunk(text_chunk)
            except json.JSONDecodeError:
                continue
                
        return self._clean_response_text(accumulated_text, model)
    
    def _parse_response_chunk(self, line: bytes) -> Dict[str, Any]:
        """Parse a single chunk of the streaming response.
        
        Args:
            line: A single line from the streaming response
            
        Returns:
            Dict[str, Any]: The parsed JSON chunk
        """
        json_str = line.decode('utf-8').removeprefix('data: ').strip()
        return json.loads(json_str) if json_str else {}
    
    def _display_chunk(self, text_chunk: str) -> None:
        """Display and log a chunk of text from the AI response.
        
        Args:
            text_chunk: The text chunk to display
        """
        print(text_chunk, end='', flush=True)
        logging.info(f"AI Response chunk: {text_chunk}")
    
    def _clean_response_text(self, text: str, model: str) -> str:
        """Clean the response text based on the model type.
        
        Args:
            text: The text to clean
            model: The AI model name
            
        Returns:
            str: The cleaned text
        """
        if model == "deepseek-r1:14b":
            return re.sub(r"<think>(.*?)</think>", "", text)
        return text
    
    def _handle_response_actions(self, text: str) -> None:
        """Handle various actions based on the AI response.
        
        Args:
            text: The complete AI response text
        """
        print()  # New line after streaming
        self.speak(text)
        
        home_command = HomeAssistantControl()
        home_command.process_home_command(text)

    def speak(self, text: str) -> None:
        """Convert text to speech and play it.
        
        Uses Google Text-to-Speech (gTTS) to convert the text to audio
        and pygame to play the audio. The audio file is temporarily stored
        and automatically cleaned up after playback.
        
        Args:
            text: The text to convert to speech
        """
        try:
            # Convert text to speech
            tts = gtts.gTTS(text, lang="en")
            
            # Create and use a temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                tts.write_to_fp(temp_file)
                temp_path = temp_file.name
            
            # Play the generated audio
            try:
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                
                # Wait for playback to finish
                clock = pygame.time.Clock()
                while pygame.mixer.music.get_busy():
                    clock.tick(10)
            finally:
                # Ensure temp file is always cleaned up
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logging.error(f"Error in speech synthesis: {e}")
            print(f"Failed to speak text: {e}")

    def create_api_url(self, model):
        supported_models = ["llama3.2", "dolphin-mistral", "deepseek-r1:14b"]
        if model not in supported_models:
            raise ValueError(f"Unsupported model: {model}. Supported models: {supported_models}")
        else:
            print(f"Selected model: {model}")
            # Pull the selected model
            api = ModelManagementAPI(base_url="http://localhost:8000")
            api.pull(model)
        api_url = GenerateAPI(base_url="http://localhost:8000", model=model)
        return api_url

    def talk(self, model):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening for a command...")
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)
                user_input = recognizer.recognize_google(audio)
                print("You said:", user_input)

                # Try the Ollama API first
                text, response = self.send_message("http://localhost:11434/v1/chat/completions", user_input, model)
                if response != 200:
                    logging.warning(f"Ollama API failed with status code: {response}")
                    print("Falling back to generated API URL...")
                    fallback_url = self.create_api_url(model)
                    if fallback_url:
                        print(f"Retrying with fallback URL: {fallback_url}")
                        text, response = self.send_message(fallback_url, user_input, model)
                        if response != 200:
                            print("Fallback API also failed.")
                            logging.error(f"Fallback API failed with status code: {response}")
                        else:
                            print("Fallback API request successful.")
                            logging.info("Fallback API request successful.")
                    else:
                        print("Could not generate fallback API URL.")
                        logging.error("API fallback mechanism failed.")
                else:
                    print("Ollama API request successful.")
                    logging.info("Ollama API request successful.")
                
                # Check if the command involves Home Assistant automation
                if "turn on" in text or "turn off" in text or "toggle" in text:
                    self.process_home_command_with_ai(model)
                else:
                    print("No matching command. Forwarding to API.")
                    self.process_home_command_with_ai(model)
                
                # Check if the command had a weather query
                if "weather" in text:
                    self.handle_weather_query(user_input)

            except sr.UnknownValueError:
                print("Could not understand audio")
                logging.warning("Could not understand audio.")
            except sr.WaitTimeoutError:
                print("No speech detected within the timeout period.")
                logging.info("No speech detected within timeout.")
            except sr.RequestError as e:
                print("Could not request results;", e)
                logging.error(f"Speech Request Error: {e}")
            except Exception as e:
                print(f"Error during speech recognition: {e}")
                logging.error(f"Speech Recognition Error: {e}")
    
class HomeAssistantControl:
    def __init__(self, weather_label=None):
        self.token = os.getenv("HOME_ASSISTANT_TOKEN")
        self.url = os.getenv("HOME_ASSISTANT_URL")
        self.home_assistant_url = self.url
        self.weather_label = weather_label  # Store a reference to the label

    def home_assistant_control(self, entity_id, action="toggle"):
        url = f"{self.home_assistant_url}/api/services/light/{action}"
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
                    self.home_assistant_control(entity_id, action="turn_on")
                elif "turn off" in command:
                    self.home_assistant_control(entity_id, action="turn_off")
                else:
                    self.home_assistant_control(entity_id, action="toggle")
        elif "weather" in command:
            self.handle_weather_query("weather.your_weather_entity_id")  # Replace with the actual entity ID
        else:
            logging.warning(f"Unknown home command: {command}")

    def extract_entity_id(self, command):
        entity_map = {
            "light": "light.living_room",
            "fan": "fan.ceiling_fan",
        }

        for key, entity_id in entity_map.items():
            if key in command:
                return entity_id

        print(f"Entity ID not found for command: {command}")
        logging.warning(f"Entity ID not found in command: {command}")
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

class AuralInterface:
    def __init__(self):
        # Create the main window
        self.window = tk.Tk()
        self.window.title("Aural Interface")

        self.home = HomeAssistantControl(self.window)

        # Create a label for the logo
        logo_label = tk.Label(self.window, text="Aural", font=("Arial", 24))
        logo_label.pack(pady=10)

        # Create a label for the time
        self.hour = datetime.now().strftime("%I:%M %p")
        self.time_label = tk.Label(self.window, text=f"Current Time: {self.hour}", font=("Arial", 12))
        self.time_label.pack(pady=5)

        # Update the time label every second
        self.update_time()

        # Create a label for the date
        self.date_label = tk.Label(self.window, text=f"Current Date: {datetime.now().strftime('%A, %B %d, %Y')}", font=("Arial", 12))
        self.date_label.pack(pady=5)

        # Create a label for location
        self.location_label = tk.Label(self.window, text=f"Location: {self.get_geolocation()}", font=("Arial", 12))
        self.location_label.pack(pady=5)

        # Create a label for the weather
        self.weather_label = tk.Label(self.window, text=f"Weather: {self.check_weather()}", font=("Arial", 12))
        self.weather_label.pack(pady=5)

        # Button frame
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=10)

        # Create buttons and pack them side by side
        start_button = tk.Button(button_frame, text="Start Aural", command=self.start_aural)
        start_button.pack(side=tk.LEFT, padx=5)

        stop_button = tk.Button(button_frame, text="Stop Aural", command=self.stop_aural)
        stop_button.pack(side=tk.LEFT, padx=5)

        pause_button = tk.Button(button_frame, text="Pause Aural", command=self.pause_aural)
        pause_button.pack(side=tk.LEFT, padx=5)

        weather_button = tk.Button(button_frame, text="Check Weather", command=self.check_weather)
        weather_button.pack(side=tk.LEFT, padx=5)

        fan_button = tk.Button(button_frame, text="Turn on Fan", command=self.turn_on_fan)
        fan_button.pack(side=tk.LEFT, padx=5)

        fan_off_button = tk.Button(button_frame, text="Turn off Fan", command=self.turn_off_fan)
        fan_off_button.pack(side=tk.LEFT, padx=5)

        light_button = tk.Button(button_frame, text="Turn on Light", command=self.turn_on_light)
        light_button.pack(side=tk.LEFT, padx=5)

        light_off_button = tk.Button(button_frame, text="Turn off Light", command=self.turn_off_light)
        light_off_button.pack(side=tk.LEFT, padx=5)

        # Text widget for logs
        self.text_widget = tk.Text(self.window, wrap=tk.WORD, state=tk.NORMAL)
        self.text_widget.pack(expand=True, fill=tk.BOTH, pady=10)

        # Create a button to send the user input
        self.send_button = tk.Button(self.window, text="Send", command=self.send_input)
        self.send_button.pack(pady=10)

        # Create a text box for user input
        self.user_input = tk.Text(self.window, height=5, width=50)  # Adjusted height for better usability
        self.user_input.pack(pady=10)

        # Console redirection
        sys.stdout = ConsoleStream(self.text_widget)

        # Initialize Aural
        self.aural = Aural()
        self.hotwords = [
            "hey llama", "llama", "llama are you there",
            "hey dolphin", "dolphin", "dolphin are you there",
            "hey deepseek", "deepseek", "deepseek are you there",
            "deep",
        ]

        # Start hotword detection in a separate thread
        threading.Thread(
            target=self.aural.hotword_detection,
            args=(self.hotwords,),
            daemon=True
        ).start()

    def turn_on_light(self):
        entity_id = "light.living_room"  # Adjust as needed
        self.home.home_assistant_control(entity_id, action="turn_on")

    def turn_off_light(self):
        entity_id = "light.living_room"  # Adjust as needed
        self.home.home_assistant_control(entity_id, action="turn_off")

    def turn_on_fan(self):
        entity_id = "fan.ceiling_fan"  # Adjust as needed
        self.home.home_assistant_control(entity_id, action="turn_on")

    def turn_off_fan(self):
        entity_id = "fan.ceiling_fan"  # Adjust as needed
        self.home.home_assistant_control(entity_id, action="turn_off")

    def update_time(self):
        current_time = datetime.now().strftime("%I:%M %p")
        self.time_label.config(text=f"Current Time: {current_time}")
        self.window.after(1000, self.update_time)

    def update_time(self):
        current_time = datetime.now().strftime("%I:%M %p")
        self.time_label.config(text=f"Current Time: {current_time}")
        self.window.after(1000, self.update_time)

    def extract_city_state(self, location_string):
        # Attempt to extract city and state using regex
        pattern = r'City of ([^,]+),\s*([^,]+)$'
        match = re.search(pattern, location_string)
        
        if match:
            city = match.group(1).strip()  # City
            state = match.group(2).strip()  # State
            return f"{city}, {state}"
        else:
            print("No city and state found...")
            return None  # Default location if not found

    def extract_zip(self, location_string):
        # Regex to find the ZIP code
        match = re.search(r'(\d{5})', location_string)
        return match.group(1) if match else "13202"  # Default ZIP code

    async def async_check_weather(self):
        location_string = self.get_geolocation()
        city_state = self.extract_city_state(location_string)
        if not city_state:
            # Use zip code instead
            city_state = self.extract_zip(location_string)
                
        # Decide which to use based on preference
        print(f"Checking weather for city and state: {city_state}")  # Expected: "Syracuse, NY"
        print(f"Checking weather for ZIP code: {city_state}")  # Expected: "13202"
        
        async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
            try:
                weather = await client.get(city_state)  # or use city_state
                print(weather)  # Debug output
                temperature = weather.temperature
                self.aural.speak(f"The current temperature is {temperature} degrees.")
                print(f"The current temperature is {temperature} degrees.")
                self.weather_label.config(text=f"The current temperature is {temperature} degrees.")
                logging.info(f"The current temperature is {temperature} degrees.")

            except Exception as e:
                print(f"Error fetching weather data: {e}")
                logging.error(f"Error fetching weather data: {e}")

    def check_weather(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.async_check_weather())

    def run(self):
        """Run the GUI main loop."""
        self.window.mainloop()
        sys.stdout = sys.__stdout__

    def start_aural(self):
        """Start the hotword detection."""
        print("Starting Aural...")
        threading.Thread(
            target=self.aural.hotword_detection,
            args=(self.hotwords,),
            daemon=True
        ).start()

    def get_ip_location(self):
        # Get latitude and longitude from IP address
        geolocation = geocoder.ip("me")
        latlng = geolocation.latlng
        print(f"Retrieved latitude and longitude: {latlng}")
        return latlng  # Returns a list of [latitude, longitude]

    def get_geolocation(self):
        latlng = self.get_ip_location()
        if latlng:
            geolocator = Nominatim(user_agent="Aural")
            try:
                location = geolocator.reverse(latlng, exactly_one=True)
                if location:
                    print(f"Location found: {location}")
                    return location.address
                else:
                    return "weather.default_location"
            except Exception as e:
                print(f"Error during reverse geocoding: {e}, using default location.")
                return "weather.default_location"
        else:
            print("Unable to retrieve location, using default location.")
            return "weather.default_location"

    def send_input(self):
        """Send user input from the text box to the send_message function."""
        user_input = self.user_input.get("1.0", tk.END).strip()  # Retrieve and clean user input
        if user_input:
            print(f"User Input: {user_input}")  # Debug: Log the input
            try:
                # Use an if else statement to determine which model to use based on the hotwords
                if "hey llama" in user_input or "llama are you there" in user_input or "llama" in user_input:
                    model = "llama3.2"
                elif "hey dolphin" in user_input or "dolphin are you there" in user_input or "dolphin" in user_input:
                    model = "dolphin-mistral"
                elif "exit" in user_input:
                    self.stop_aural()
                else:
                    model = "deepseek-r1:8b" # Default to deepseek

                status_code = self.aural.send_message("http://localhost:11434/v1/chat/completions", user_input, model)
                if status_code != 200:
                    print("API request failed.")
                    print("Trying backup API...")
                    api_url = self.aural.create_api_url(model)
                    if api_url:
                        status_code = self.aural.send_message(api_url, user_input, model)
                        if status_code != 200:
                            print("Fallback API request failed.")
                            logging.error(f"Fallback API failed with status code: {status_code}")
                        else:
                            print("Fallback API request successful.")
                            logging.info("Fallback API request successful.")
                    else:
                        print("Could not generate fallback API URL.")
                        logging.error("API fallback mechanism failed.")
                else:
                    print("API request successful.")

            except Exception as e:
                print(f"Error processing user input: {e}")
            finally:
                # Clear the text box after sending
                self.user_input.delete("1.0", tk.END)

    def stop_aural(self):
        """Stop the hotword detection and close the application."""
        print("Stopping Aural...")
        self.aural.listening = False  # Signal the hotword detection loop to stop
        self.window.destroy()  # Close the GUI window

    def pause_aural(self):
        print("Pausing Aural...")
        # Use the existing threads to pause the hotword detection loop
        self.aural.listening = False

# Create and run the GUI
if __name__ == "__main__":
    aural_interface = AuralInterface()
    aural_interface.run()
