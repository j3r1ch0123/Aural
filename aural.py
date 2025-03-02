#!/usr/bin/env python3.11

# Standard library imports
import asyncio
import json
import queue
import logging
import os
import re
import sys
import tempfile
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party imports
import geocoder
import pygame
import python_weather
import requests
import queue
import speech_recognition as sr
import tkinter as tk
from tkinter import ttk
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from geopy.geocoders import Nominatim
from googlesearch import search
from ollama_python.endpoints import GenerateAPI, ModelManagementAPI
from database import ResearchDatabase
import gtts
import wikipediaapi
import newsapi
import markdown

# Local imports
from dataclasses import dataclass

class Config:
    def __init__(self):
        self.db = ResearchDatabase()
        self.db.migrate()
        try:
            with open('config.json') as f:
                config = json.load(f)
            self.SPEECH_TIMEOUT = config['SPEECH_TIMEOUT']
            self.PHRASE_TIME_LIMIT = config['PHRASE_TIME_LIMIT']
            self.HOTWORDS = config['HOTWORDS']
            self.SUPPORTED_MODELS = config['SUPPORTED_MODELS']
        except json.JSONDecodeError as e:
            print(f"Error parsing config.json: {e}")
            print("Please check your config file for syntax errors")
            self._load_defaults()
        except KeyError as e:
            print(f"Missing required config key: {e}")
            self._load_defaults()
            
    def _load_defaults(self):
        """Load default configuration values"""
        self.SPEECH_TIMEOUT = 5
        self.PHRASE_TIME_LIMIT = 10
        self.HOTWORDS = {}
        self.SUPPORTED_MODELS = {}

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
        self.system_prompt = "You are Aural, an AI voice assistant. You are helpful, friendly, and concise. You maintain context from previous messages and can engage in natural conversations."
        self.conversation_history = [{"role": "system", "content": self.system_prompt}]
        self.listening: bool = True
        self.lock: threading.Lock = threading.Lock()
        self.relationship_context = {}

        # Change these values if you want to use the home assistant control
        self.home_assistant_token: Optional[str] = None
        self.home_assistant_url: Optional[str] = None
        
        # Initialize audio
        pygame.mixer.init()
        self.audio_enabled = True

        # Configure logging
        self._setup_logging()

        # Hotword detection configuration
        self.config = config

        self.home_assistant_control = HomeAssistantControl()
    
    def update_context(self, relationship: str, value: str) -> None:
        """Update the relationship context with the given relationship and value."""
        self.relationship_context[relationship] = value
    
    def get_context(self, relationship: str) -> dict:
        """Get the context for the given relationship."""
        return self.relationship_context.get(relationship, {})
        
    def _setup_logging(self) -> None:
        """Configure logging settings for the application.

        Logs are written to './aural.log' with a timestamp, log level, and message.
        """
        logging.basicConfig(
            filename='./aural.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Aural initialized.")

    def hotword_detection(self, hotwords: List[str]) -> None:
        """Listen for hotwords and trigger appropriate model responses."""
        recognizer = sr.Recognizer()
        print("Starting hotword detection...")

        try:
            with sr.Microphone() as source:  # Automatically selects system default mic
                print("Adjusting for ambient noise...")
                recognizer.adjust_for_ambient_noise(source)
                print("Listening for hotwords...")

                while self.listening:
                    with self.lock:
                        try:
                            audio = recognizer.listen(
                                source, 
                                timeout=config.SPEECH_TIMEOUT, 
                                phrase_time_limit=config.PHRASE_TIME_LIMIT
                            )
                            text = recognizer.recognize_google(audio).lower()

                            if not text:
                                print("No speech detected")
                                continue

                            if any(hotword in text for hotword in hotwords):
                                print("Hotword detected!")
                                # Choose the model based on the hotword
                                if "dolphin" in text:
                                    model_name = "dolphin-mistral"
                                elif "deepseek" in text:
                                    model_name = "deepseek-r1:8b"
                                else:
                                    model_name = "llama3.2"
                                selected_model = config.SUPPORTED_MODELS.get(model_name, model_name)
                                print(f"Using model: {selected_model} for recognized text: {text}")
                                logging.info(f"Using model: {selected_model} for recognized text: {text}")
                                if not selected_model:
                                    selected_model = config.SUPPORTED_MODELS.get("llama3.2", "llama3.2:latest")
                                print(f"Using model: {selected_model} for recognized text: {text}")
                                logging.info(f"Using model: {selected_model} for recognized text: {text}")
                                self.talk(selected_model)
                                return

                        except sr.WaitTimeoutError:
                            print("Listening timed out, no speech detected.")
                        except sr.UnknownValueError:
                            print("Could not understand the audio. Please try again.")
                        except sr.RequestError as e:
                            print(f"Error during speech recognition: {e}")
                        except Exception as e:
                            print(f"Error during hotword detection: {e}")
                            time.sleep(0.1)
        except Exception as e:
            print(f"Error with microphone: {e}")

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
        if not message or message.isspace():
            print("Warning: No message to send")
            return None

        self.conversation_history.append({"role": "user", "content": message})

        try:
            # Ensure the model name is correctly formatted
            if not model.endswith(":latest") and not model.startswith("deepseek"):
                model += ":latest"
            elif model.startswith("deepseek"):
                model = "deepseek-r1:14b"

            payload = {
                "model": model,
                "prompt": message,
                "stream": True
            }

            response = requests.post(url, json=payload)

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    self.process_response(response_data["response"], model)
                    return response.status_code
                except json.JSONDecodeError:
                    # Handle streaming response
                    response_text = response.text.strip()
                    if response_text:
                        try:
                            # Try parsing each line as separate JSON
                            responses = [json.loads(line) for line in response_text.split('\n') if line]
                            combined_response = ''.join(r.get('response', '') for r in responses)
                            self.process_response(combined_response, model)
                            return response.status_code
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse streaming response: {str(e)}")
                            return None
            else:
                print(f"API request failed with status code: {response.status_code}")
                return None
        except Exception as e:
            print(f"API request failed: {str(e)}")
            return None

    def process_response(self, response: str, model: str) -> None:
        """Process the response from the AI model.

        Args:
            response: The response from the AI model
            model: The AI model name
        """
        try:
            if model == "deepseek-r1:8b":
                response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
                response = response.strip()
            
            # Add AI response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            print(response)
            self.speak(response)
            
            home_command = HomeAssistantControl()
            home_command.process_home_command(response)
        except Exception as e:
            print(f"Error processing response: {str(e)}")
            logging.error(f"Error processing response: {str(e)}")

    def clear_conversation(self) -> None:
        """Clear the conversation history but keep the system prompt."""
        self.conversation_history = [{"role": "system", "content": self.system_prompt}]
        print("Conversation history cleared.")
        return self.conversation_history

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the full conversation history.
        
        Returns:
            List[Dict[str, str]]: List of conversation messages with roles and content
        """
        history = self.conversation_history
        print("\nConversation History:")
        for msg in history:
            print(f"{msg['role'].capitalize()}: {msg['content']}")
        return history

    def save_conversation(self, filename: str = "conversation_history.json") -> None:
        """Save the conversation history to a file.
        
        Args:
            filename: Name of the file to save the conversation history to
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.conversation_history, f, indent=2)
            print(f"Conversation saved to {filename}")
        except Exception as e:
            print(f"Error saving conversation: {str(e)}")
            logging.error(f"Error saving conversation: {str(e)}")

    def load_conversation(self, filename: str = "conversation_history.json") -> None:
        """Load conversation history from a file.
        
        Args:
            filename: Name of the file to load the conversation history from
        """
        try:
            with open(filename, 'r') as f:
                self.conversation_history = json.load(f)
            print(f"Conversation loaded from {filename}")
        except Exception as e:
            print(f"Error loading conversation: {str(e)}")
            logging.error(f"Error loading conversation: {str(e)}")

    def speak(self, text: str) -> None:
        """Convert text to speech and play it.

        Uses Google Text-to-Speech (gTTS) to convert the text to audio
        and pygame to play the audio. The audio file is temporarily stored
        and automatically cleaned up after playback.

        Args:
            text: The text to convert to speech
        """
        if not text or text.isspace():
            print("Warning: No text to speak")
            return
        try:
            # Convert text to speech
            tts = gtts.gTTS(text)
            
            # Create and use a temporary file
            with tempfile.NamedTemporaryFile(delete=True) as fp:
                tts.save(f"{fp.name}.mp3")
                pygame.mixer.music.load(f"{fp.name}.mp3")
                pygame.mixer.music.play()
                
                # Wait for playback to finish
                clock = pygame.time.Clock()
                while pygame.mixer.music.get_busy():
                    clock.tick(10)
        except gtts.tts.gTTSError as e:
            print(f"Failed to speak text: {str(e)}")
            logging.error(f"Error in speech synthesis: {e}")
        except pygame.error as e:
            print(f"Failed to play audio: {str(e)}")
            logging.error(f"Error playing audio: {e}")
        except Exception as e:
            print(f"Failed to speak text: {str(e)}")
            logging.error(f"Error in speech synthesis: {e}")
                    
    def create_api_url(self, model: str) -> str:
        if not model.endswith(":latest"):
            model += ":latest"  # Ensure correct model format

        return "http://localhost:11434/api/generate"  # Update if model-specific URLs are needed

    def talk(self, model: str) -> None:
        """Start a conversation with the AI model."""
        recognizer = sr.Recognizer()
        logging.info(f"Starting conversation with model: {model}")

        try:
            with sr.Microphone() as source:
                print("Listening for a command...")
                logging.info("Listening for a command...")
                recognizer.adjust_for_ambient_noise(source)

                try:
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)
                    logging.info("Audio captured successfully.")
                    user_input = recognizer.recognize_google(audio)
                    logging.info(f"You said: {user_input}")
                    print("You said:", user_input)

                    if user_input and not user_input.isspace():
                        api_response = self.send_message("http://localhost:11434/api/generate", user_input, model)
                        if api_response is None:
                            logging.error("API request failed. No response received.")
                            print("API request failed. Please try again.")
                    else:
                        print("No valid input detected")
                        logging.warning("No valid input detected")

                except sr.UnknownValueError:
                    print("Could not understand audio")
                    logging.warning("Speech recognition could not understand audio")
                except sr.WaitTimeoutError:
                    print("No speech detected within the timeout period.")
                    logging.warning("No speech detected within timeout period")
                except sr.RequestError as e:
                    print(f"Could not request results: {e}")
                    logging.error(f"Speech recognition request error: {e}")
                except Exception as e:
                    print(f"Error during speech recognition: {e}")
                    logging.error(f"Speech recognition error: {e}")

        except OSError as e:
            print(f"Microphone error: {e}")
            logging.error(f"Microphone error: {e}")
        except Exception as e:
            print(f"Error starting conversation: {e}")
            logging.error(f"Error starting conversation: {e}")

class DeepResearch:
    def __init__(self):
        self.search_engines = ['google', 'wikipedia', 'news']
        self.max_results = 5
        self.newsapi = newsapi.NewsApiClient(api_key='YOUR_NEWSAPI_KEY')
        self.wiki = wikipediaapi.Wikipedia('en')
        
    def web_search(self, query):
        results = []
        results.extend(self._google_search(query))
        results.extend(self._wikipedia_search(query))
        results.extend(self._news_search(query))
        return results
        
    def _google_search(self, query):
        try:
            for url in search(query, num=self.max_results, stop=self.max_results, pause=2):
                results.append(self._process_url(url))
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []
            
    def _process_url(self, url):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            return {
                'title': soup.title.string if soup.title else 'Untitled',
                'url': url,
                'content': soup.get_text()[:500] + '...'
            }
        except Exception as e:
            print(f"URL processing error: {e}")
            return None

    def _wikipedia_search(self, query):
        page = self.wiki.page(query)
        if page.exists():
            return [{
                'title': page.title,
                'url': page.fullurl,
                'content': page.summary[:500] + '...',
                'source': 'Wikipedia'
            }]
        return []
        
    def _news_search(self, query):
        articles = self.newsapi.get_everything(q=query, language='en', page_size=self.max_results)
        return [{
            'title': article['title'],
            'url': article['url'],
            'content': article['description'][:500] + '...',
            'source': article['source']['name'],
            'published_at': article['publishedAt']
        } for article in articles['articles']]
        
    def save_results(self, results, format='json'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if format == 'json':
            with open(f'research_results_{timestamp}.json', 'w') as f:
                json.dump(results, f, indent=2)
        elif format == 'md':
            with open(f'research_results_{timestamp}.md', 'w') as f:
                for result in results:
                    f.write(f"## {result['title']}\n")
                    f.write(f"**Source:** {result['source']}\n")
                    f.write(f"**URL:** {result['url']}\n")
                    f.write(f"{result['content']}\n\n")

class HomeAssistantControl:
    def __init__(self, weather_label=None):
        self.token = os.getenv("HOME_ASSISTANT_TOKEN")
        self.url = os.getenv("HOME_ASSISTANT_URL")
        self.home_assistant_url = self.url
        self.weather_label = weather_label  # Store a reference to the label

    def home_assistant_control(self, entity_id: str, action: str = "toggle") -> None:
        """Control a Home Assistant device.

        Args:
            entity_id: The ID of the device to control
            action: The action to perform (e.g., "toggle", "turn_on", "turn_off")
        """
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
    
    def process_home_command(self, command: str) -> None:
        """Process a Home Assistant command.

        Args:
            command: The command to process
        """
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
        elif "research" in command or "look up" in command:
            self.start_research(command)
        else:
            logging.warning(f"Unknown home command: {command}")

    def extract_entity_id(self, command: str) -> Optional[str]:
        """Extract the entity ID from a command.

        Args:
            command: The command to extract the entity ID from

        Returns:
            Optional[str]: The extracted entity ID or None if not found
        """
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

    def start_research(self, query):
        research = DeepResearch()
        results = research.web_search(query)
        self.display_results(results)

    def display_results(self, results):
        for result in results:
            print(f"Title: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Content: {result['content']}")
            print("\n")

    def handle_weather_query(self, entity_id: str) -> None:
        """Handle a weather query.

        Args:
            entity_id: The entity ID of the weather device
        """
        # Replace with actual weather query logic
        pass

class AuralThread:
    def __init__(self, hotwords: List[str], token: str, home_assistant_url: str):
        super().__init__()
        self.hotwords = hotwords
        self.token = token
        self.home_assistant_url = home_assistant_url

    def run(self) -> None:
        aural = Aural()
        aural.home_assistant_token = self.token
        aural.home_assistant_url = self.home_assistant_url
        self.log_signal.emit("Initializing Aural...")
        # Make sure the hotword detection loop is active
        aural.hotword_detection(hotwords=self.hotwords)
        self.log_signal.emit("Hotword detection stopped.")

class ConsoleStream:
    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.update_pending = False

    def write(self, text: str) -> None:
        self.queue.put(text)
        if not self.update_pending:
            try:
                self.text_widget.after(10, self._process_queue)
                self.update_pending = True
            except tk.TclError:
                # Main loop not running yet, just ignore output
                pass

    def _process_queue(self) -> None:
        self.update_pending = False
        try:
            while True:
                text = self.queue.get_nowait()
                self.text_widget.insert(tk.END, text + "\n")
                self.text_widget.see(tk.END)
                self.queue.task_done()
        except queue.Empty:
            pass
        
    def flush(self) -> None:
        # Required by Python's IO system
        pass

class AuralInterface:
    def __init__(self):
        print("Initializing Aural Interface...")
        # Create the main window
        self.window = tk.Tk()
        self.aural = None  # Will be set by set_aural
        self.window.title("Aural Interface")
        print("Window created successfully")

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

        # Create a label for the weather - will update after Aural is initialized
        self.weather_label = tk.Label(self.window, text="Weather: Checking...", font=("Arial", 12))
        self.weather_label.pack(pady=5)

        # Button frame
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=10)

        # Create microphone selection dropdown
        self.mic_var = tk.StringVar()
        mics = sr.Microphone.list_microphone_names()
        mic_frame = tk.Frame(self.window)
        mic_frame.pack(pady=5)
        
        tk.Label(mic_frame, text="Select Microphone:").pack(side=tk.LEFT, padx=5)
        mic_menu = ttk.Combobox(mic_frame, textvariable=self.mic_var)
        mic_menu['values'] = mics
        mic_menu.set(mics[0] if mics else "No microphones found")
        mic_menu.pack(side=tk.LEFT, padx=5)
        
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

        clear_conversation_button = tk.Button(button_frame, text="Clear Conversation", command=self.clear_conversation)
        clear_conversation_button.pack(side=tk.LEFT, padx=5)

        get_conversation_history_button = tk.Button(button_frame, text="Get Conversation History", command=self.get_conversation_history)
        get_conversation_history_button.pack(side=tk.LEFT, padx=5)

        save_conversation_button = tk.Button(button_frame, text="Save Conversation", command=self.save_conversation)
        save_conversation_button.pack(side=tk.LEFT, padx=5)

        load_conversation_button = tk.Button(button_frame, text="Load Conversation", command=self.load_conversation)
        load_conversation_button.pack(side=tk.LEFT, padx=5)

        self.research_button = tk.Button(button_frame, text="Deep Research", command=self.start_research)
        self.research_button.pack(side=tk.LEFT, padx=5)

        # Text widget for logs
        self.text_widget = tk.Text(self.window, wrap=tk.WORD, state=tk.NORMAL)
        self.text_widget.pack(expand=True, fill=tk.BOTH, pady=10)
        
        # Add scrollbar
        scrollbar = tk.Scrollbar(self.window, command=self.text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.config(yscrollcommand=scrollbar.set)

        # Create a button to send the user input
        self.send_button = tk.Button(self.window, text="Send", command=self.send_input)
        self.send_button.pack(pady=10)

        # Create a text box for user input
        self.user_input = tk.Text(self.window, height=5, width=50)  # Adjusted height for better usability
        self.user_input.pack(pady=10)

        # Console redirection
        sys.stdout = ConsoleStream(self.text_widget)

        # Initialize Aural with reference to interface
        self.aural = Aural()
        self.aural.interface = self
        self.hotwords = [
            "hey llama", "llama", "llama are you there",
            "hey dolphin", "dolphin", "dolphin are you there",
            "hey deepseek", "deepseek", "deepseek are you there",
            "deep",
        ]
        
        # Schedule weather update after main loop starts
        self.window.after(100, self._initialize_after_mainloop)
    
    def _initialize_after_mainloop(self) -> None:
        """Initialize components that require the main loop to be running"""
        # Start hotword detection in a separate thread
        threading.Thread(
            target=self.aural.hotword_detection,
            args=(self.hotwords,),
            daemon=True
        ).start()
    
    def run(self) -> None:
        """Run the Aural assistant."""
        print("Starting Aural Interface...")
        try:
            self.window.mainloop()
        except Exception as e:
            print(f"Error in GUI mainloop: {e}")
            raise
    
    def start_aural(self):
        # Start the Aural assistant
        self.aural.listening = True

    def control_device(self, device: str, action: str) -> None:
        """Control a device (e.g., light, fan) with a specific action (e.g., on, off).

        Args:
            device: The device to control (e.g., 'light', 'fan').
            action: The action to perform (e.g., 'on', 'off').
        """
        entity_id = f'switch.{device}'
        self.home.home_assistant_control(entity_id, action)
        logging.info(f'Turned {action} {device}')

    def turn_on_light(self) -> None:
        self.control_device('light', 'on')

    def turn_off_light(self) -> None:
        self.control_device('light', 'off')

    def turn_on_fan(self) -> None:
        self.control_device('fan', 'on')

    def turn_off_fan(self) -> None:
        self.control_device('fan', 'off')

    def update_time(self) -> None:
        current_time = datetime.now().strftime("%I:%M %p")
        self.time_label.config(text=f"Current Time: {current_time}")
        self.window.after(1000, self.update_time)

    def get_ip_location(self) -> List[float]:
        # Get latitude and longitude from IP address
        geolocation = geocoder.ip("me")
        latlng = geolocation.latlng
        print(f"Retrieved latitude and longitude: {latlng}")
        return latlng  # Returns a list of [latitude, longitude]

    def get_geolocation(self) -> str:
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

    def send_input(self) -> None:
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
                elif "hey deepseek" in user_input or "deepseek are you there" in user_input or "deepseek" in user_input:
                    model = "deepseek-r1:8b"
                elif "exit" in user_input:
                    self.stop_aural()
                else:
                    model = "deepseek-r1:8b" # Default to deepseek

                status_code = self.aural.send_message("http://localhost:11434/api/generate", user_input, model)
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

    def stop_aural(self) -> None:
        """Stop the hotword detection and close the application."""
        print("Stopping Aural...")
        self.aural.listening = False  # Signal the hotword detection loop to stop
        self.window.destroy()  # Close the GUI window

    def pause_aural(self) -> None:
        print("Pausing Aural...")
        # Use the existing threads to pause the hotword detection loop
        self.aural.listening = False

    def extract_city_state(self, location_string: str) -> str:
        # Extract city and state from the location string
        city_state = location_string.split(",")[0].strip()
        return city_state

    def check_weather(self) -> str:
        """Check the current weather and update the weather label.

        Returns:
            str: A string describing the current weather
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.async_check_weather())
        return self.date_label['text']

    def append_text(self, text: str, clear: bool = False) -> None:
        """Append text to the text widget."""
        self.text_widget.configure(state=tk.NORMAL)
        if clear:
            self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(tk.END, text + '\n')
        self.text_widget.configure(state=tk.DISABLED)
        self.text_widget.see(tk.END)

    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        if self.aural:
            self.aural.clear_conversation()
            self.append_text("Conversation history cleared.", clear=True)

    def get_conversation_history(self) -> None:
        """Display the conversation history."""
        if self.aural:
            history = self.aural.get_conversation_history()
            self.append_text("\nConversation History:", clear=True)
            for msg in history:
                if msg['role'] != 'system':  # Don't show system prompt
                    self.append_text(f"{msg['role'].capitalize()}: {msg['content']}")

    def save_conversation(self) -> None:
        """Save the conversation history."""
        if self.aural:
            self.aural.save_conversation()
            self.append_text("Conversation saved to conversation_history.json")

    def load_conversation(self) -> None:
        """Load a conversation history."""
        if self.aural:
            self.aural.load_conversation()
            self.append_text("Conversation loaded from conversation_history.json")
            self.get_conversation_history()

    async def async_check_weather(self) -> None:
        """Asynchronously check the weather using the Python Weather API."""
        location_string = self.get_geolocation()
        city_state = self.extract_city_state(location_string)
        if not city_state:
            # Use zip code instead
            city_state = self.extract_zip(location_string)

        async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
            try:
                weather = await client.get(city_state)
                temperature = weather.temperature
                # print(f"The current temperature is {temperature} degrees.")
                # self.aural.speak(f'The current temperature is {temperature} degrees.')
                # self.weather_label.config(text=f'The current temperature is {temperature} degrees.')
                # logging.info(f'The current temperature is {temperature} degrees.')
            except Exception as e:
                print(f'Error fetching weather data: {e}')
                logging.error(f'Error fetching weather data: {e}')

    def start_research(self):
        query = self.user_input.get("1.0", tk.END).strip()
        if query:
            research = DeepResearch()
            results = research.web_search(query)
            self.display_results(results)

    def display_results(self, results):
        for result in results:
            print(f"Title: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Content: {result['content']}")
            print("\n")

# Create and run the GUI
if __name__ == "__main__":
    aural_interface = AuralInterface()
    aural_interface.run()