# Auralis
A python program designed to let the user talk to their locally hosted AI.

This is a Python-based voice-interactive AI assistant that utilizes speech recognition and text-to-speech technologies. The program allows you to interact with a local AI model (Dolphin Mistral) hosted via the Ollama API. You can speak to the assistant, and it will process your input and respond with speech.

## Features
- **Voice Input**: The assistant listens for your speech using your microphone.
- **Text-to-Speech Output**: The assistant converts its response to speech and plays it.
- **Wait for Enter Key**: The program waits for the Enter key to be pressed before starting speech recognition, allowing more control over when the assistant listens.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/voice-interactive-ai.git
   cd voice-interactive-ai
Create and activate a virtual environment (optional but recommended):

bash
```

python -m venv venv
source venv/bin/activate  # For Linux/macOS
venv\Scripts\activate  # For Windows
```
Install the dependencies:

bash
```
pip install -r requirements.txt
```

Make sure you have the Ollama API running locally with the Dolphin Mistral model available.

Run the program:

bash
```

python auralis.py
```
How to Use

Press Enter to start the program and allow the assistant to listen.

Speak your command or question.

Press Enter again when you’re done speaking to stop the recording and process the input.

The assistant will respond with speech.

Dependencies

speechrecognition - for speech-to-text functionality

pygame - for audio playback

gTTS - for text-to-speech functionality

requests - for API interaction with the Ollama server

Contributing

Feel free to fork this repository and contribute to improving the assistant. Pull requests are welcome!

License
This project is open-source and available under the MIT License.

markdown


### **requirements.txt**

Notes:
Make sure the Ollama API is running with the Dolphin Mistral model before using the program.
