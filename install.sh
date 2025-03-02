#!/bin/bash
sudo apt-get update
sudo apt-get install -y curl python3-pip portaudio19-dev
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
ollama pull dolphin-mistral
ollama pull fixt/home-3b-v3
ollama run deepseek-r1:8b
ollama serve
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
