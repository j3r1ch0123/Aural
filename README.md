# Aural
A Python program designed to let the user talk to their locally hosted AI and interact with home automation systems.

Now comes with a GUI.

Aural is a Python-based voice-interactive AI assistant that utilizes speech recognition, text-to-speech technologies, and local AI models (such as Dolphin Mistral) hosted via the Ollama API. The program allows you to speak to the assistant, which 

processes your input, responds with speech, and can interact with services like weather reports and home automation systems (via Home Assistant).

Features

Voice Input: The assistant listens for your speech using your microphone and recognizes hotwords (like "hey llama").

Text-to-Speech Output: The assistant converts its response to speech and plays it.

Home Automation Control: Interact with smart home devices (like lights, fans, thermostats, etc.) via Home Assistant.

Weather Queries: Ask the assistant about the current weather, and it will retrieve accurate weather data using OpenWeatherMap. (work in progress)

Multi-language Hotword Support: The assistant supports hotwords in multiple languages, making it more flexible for non-English speakers.

Installation

Clone the repository:

bash

Copy code

git clone https://github.com/j3r1ch0123/Aural.git

cd Aural

Create and activate a virtual environment (optional but recommended):

bash

Copy code

python -m venv venv

source venv/bin/activate  # For Linux/macOS

venv\Scripts\activate  # For Windows

Install the dependencies:

Alternatively:

bash install.sh

bash
Copy code

pip install -r requirements.txt

Make sure you have the Ollama API running locally with the Dolphin Mistral model available and Home Assistant set up (if you want to use home automation features).

Run the program:

bash
Copy code

bash run.sh

How to Use

When prompted, speak one of the hotwords (e.g. "hey llama")

Speak your command or question (e.g., ask about the weather or control your smart devices).

The assistant will respond with speech.

If the command involves home automation (e.g., turning on lights), the assistant will forward it to your Home Assistant setup.

If you ask about the weather, the assistant will fetch accurate weather data from OpenWeatherMap and provide you with a response.

Dependencies

speechrecognition - For speech-to-text functionality.

pygame - For audio playback.

gTTS - For text-to-speech functionality.

requests - For API interaction with the Ollama server and Home Assistant.

googletrans - For multi-language support of hotwords.

OpenWeatherMap API - For fetching real-time weather data.

Contributing

Feel free to fork this repository and contribute to improving the assistant. Pull requests are welcome!

License

This project is open-source and available under the MIT License.

Notes:

Make sure the Ollama API is running with the Dolphin Mistral or Llama3.2 models before using the program.

If you're using home automation features, ensure that Home Assistant is set up and accessible on your local network.

To use weather queries, you'll need to sign up for an OpenWeatherMap API key and update the script with your API key.

markdown

Notes:

Make sure the Ollama API is running with the Dolphin Mistral model before using the program.
