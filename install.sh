#!/bin/bash
sudo apt-get install -y curl python3-pip portaudio19-dev
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
ollama pull dolphin-mistral
ollama pull fixt/home-3b-v3
ollama run deepseek-r1:8b
ollama serve
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
