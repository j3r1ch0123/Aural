<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <h1>Aural</h1>
    <p>A Python program designed to let the user talk to their locally hosted AI and interact with home automation systems.</p>
    <p><strong>Now comes with a GUI.</strong></p>
    <p>Aural is a Python-based voice-interactive AI assistant that utilizes speech recognition, text-to-speech technologies, and local AI models (such as Dolphin Mistral) hosted via the Ollama API. The program allows you to speak to the assistant, which processes your input, responds with speech, and can interact with services like weather reports and home automation systems (via Home Assistant).</p>

    <h2>Features</h2>
    <ul>
        <li><strong>Voice Input:</strong> The assistant listens for your speech using your microphone and recognizes hotwords (like "hey llama").</li>
        <li><strong>Text-to-Speech Output:</strong> The assistant converts its response to speech and plays it.</li>
        <li><strong>Home Automation Control:</strong> Interact with smart home devices (like lights, fans, thermostats, etc.) via Home Assistant.</li>
        <li><strong>Weather Queries:</strong> Ask the assistant about the current weather, and it will retrieve accurate weather data using OpenWeatherMap. <em>(Work in progress)</em></li>
        <li><strong>Multi-language Hotword Support:</strong> The assistant supports hotwords in multiple languages, making it more flexible for non-English speakers.</li>
        <li><strong>GUI:</strong> A user-friendly graphical interface for easy interaction.</li>
    </ul>

    <h2>Installation</h2>
    <h3>For Linux/macOS</h3>
    <ol>
        <li>Clone the repository:
            <pre><code>git clone https://github.com/j3r1ch0123/Aural.git
cd Aural</code></pre>
        </li>
        <li>Create and activate a virtual environment:
            <pre><code>python3 -m venv venv
source venv/bin/activate</code></pre>
        </li>
        <li>Install the dependencies:
            <pre><code>pip install -r requirements.txt</code></pre>
        </li>
        <li>Alternatively, run the provided install script:
            <pre><code>bash install.sh</code></pre>
        </li>
        <li>Ensure the Ollama API is running locally, and the required models are installed:
            <pre><code>ollama serve</code></pre>
        </li>
        <li>Run the program:
            <pre><code>python aural.py</code></pre>
        </li>
    </ol>

    <h3>For Windows</h3>
    <ol>
        <li>Clone the repository:
            <pre><code>git clone https://github.com/j3r1ch0123/Aural.git
cd Aural</code></pre>
        </li>
        <li>Create and activate a virtual environment:
            <pre><code>python -m venv venv
venv\Scripts\activate</code></pre>
        </li>
        <li>Install the dependencies:
            <pre><code>pip install -r requirements.txt</code></pre>
        </li>
        <li>Download and install the Ollama API for Windows from <a href="https://ollama.com" target="_blank">https://ollama.com</a>.</li>
        <li>Pull the required models:
            <pre><code>ollama pull llama3.2
ollama pull dolphin-mistral
ollama pull fixt/home-3b-v3</code></pre>
        </li>
        <li>Start the Ollama API:
            <pre><code>ollama serve</code></pre>
        </li>
        <li>Run the program:
            <pre><code>python aural.py</code></pre>
        </li>
    </ol>

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

