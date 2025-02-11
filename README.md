# Aural

Aural is a Python-based voice-interactive AI assistant that utilizes speech recognition, text-to-speech technologies, and locally hosted AI models via the Ollama API. It features a graphical user interface (GUI) for easy interaction and supports both voice and text input. Aural integrates with Home Assistant to control smart devices and offers weather updates based on your location. Now uses deepseek too.

---

## Features

### AI Interaction
- **Voice Recognition:** Hotword-based interaction ("Hey Llama", "Hey Dolphin", etc.).
- **Text Input:** For situations where the microphone is unavailable.
- **Local AI Models:** Works with models like Llama3.2, Dolphin-Mistral, and Fixt/Home-3b-v3 via the Ollama API.

### GUI Interface
- **Interactive Dashboard:** Includes buttons for key actions (e.g., controlling lights, fans, checking the weather).
- **Dynamic Updates:** Displays current time, date, weather, and location in real-time.
- **Log Console:** View all interactions directly in the GUI.

### Home Automation
- **Control Smart Devices:** Manage lights, fans, and other appliances through Home Assistant with a single click or voice command.
- **Customizable Entities:** Easily configure smart devices by updating entity IDs.

### Weather Updates
- **Location-Based Weather:** Fetch real-time weather based on your geolocation.
- **Multiple Data Sources:** Automatically switches between city, state, or ZIP code as needed.

### Multi-Language Support
- **Hotwords Translation:** Recognizes hotwords in multiple languages using Google Translator.
- **Global Compatibility:** Ensures accessibility for non-English speakers.

### Extensible Design
- **Backup API Integration:** Automatically switches to a backup API if the primary one fails.
- **Custom Models:** Select and integrate models based on user preferences.

---

## Installation

### Prerequisites
- Python 3.11 or higher
- Pip
- Ollama API installed and running locally
- Home Assistant (optional, for smart home integration)

### Steps
#### For Linux/macOS
1. Clone the repository:
   ```bash
   git clone https://github.com/j3r1ch0123/Aural.git
   cd Aural
   bash install.sh
   bash run.sh
    ```

    <h2>How to Use</h2>
    <ol>
        <li>When prompted, speak one of the hotwords (e.g., "hey llama").</li>
        <li>Speak your command or question (e.g., ask about the weather or control your smart devices).</li>
        <li>The assistant will respond with speech or take the appropriate action.</li>
        <li>If the microphone is unavailable, you can use the provided text input box in the GUI to communicate with the assistant.</li>
    </ol>

    <h2>Dependencies</h2>
    <ul>
        <li><strong>speechrecognition:</strong> For speech-to-text functionality.</li>
        <li><strong>pygame:</strong> For audio playback.</li>
        <li><strong>gTTS:</strong> For text-to-speech functionality.</li>
        <li><strong>requests:</strong> For API interaction with the Ollama server and Home Assistant.</li>
        <li><strong>googletrans:</strong> For multi-language support of hotwords.</li>
        <li><strong>OpenWeatherMap API:</strong> For fetching real-time weather data.</li>
    </ul>

    <h2>For Windows</h2>
    Clone the repository:

   - bash

   - git clone https://github.com/j3r1ch0123/Aural.git

   - cd Aural

   - Create and activate a virtual environment:

   - bash

   - python -m venv venv

   - venv\Scripts\activate

   - Install dependencies:

   bash
   
   pip install -r requirements.txt
   
   Install the Ollama API for Windows and pull required models:
   
   bash
   ```
   
   ollama pull llama3.2
   
   ollama pull dolphin-mistral
   
   ollama pull fixt/home-3b-v3
   
   ollama serve
   ```
   
   Start the program:
   
   bash
   ```
   
   python aural.py

   ```
   
   How to Use
   
   Start Aural: Use the GUI or terminal to initiate the program.
   
   Hotword Detection: Speak one of the configured hotwords (e.g., "Hey Llama").
   
   Home Automation: Control smart devices using buttons in the GUI or voice commands.
   
   Weather Check: Use the "Check Weather" button or ask about the weather using voice/text input.
   
   Log Interaction: All interactions are displayed in the log console for transparency.
   
   Dependencies
   
   speechrecognition: Speech-to-text functionality.
   
   pygame: Audio playback.
   
   gTTS: Text-to-speech functionality.
   
   requests: API communication.
   
   googletrans: Multi-language hotword support.
   
   python-weather: Weather updates.
   
   geopy, geocoder: Location services.


    <h2>Contributing</h2>
    <p>Feel free to fork this repository and contribute to improving the assistant. Pull requests are welcome!</p>

    <h2>License</h2>
    <p>This project is open-source and available under the MIT License.</p>

    <h2>Notes</h2>
    <ul>
        <li>Make sure the Ollama API is running with the Dolphin Mistral or Llama3.2 models before using the program.</li>
        <li>If you're using home automation features, ensure that Home Assistant is set up and accessible on your local network.</li>
        <li>To use weather queries, you'll need to sign up for an OpenWeatherMap API key and update the script with your API key.</li>
    </ul>
</body>
</html>

