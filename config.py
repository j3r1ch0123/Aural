"""Configuration settings for the Aural AI Assistant."""

from typing import Dict, List
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ModelConfig:
    """Configuration for AI models."""
    name: str
    base_url: str = "http://localhost:11434/v1/chat/completions"
    fallback_url: str = "http://localhost:8000"
    requires_cleanup: bool = False
    cleanup_pattern: str = ""

@dataclass
class LogConfig:
    """Configuration for logging."""
    filename: str = "./aural.log"
    level: str = "INFO"
    format: str = "%(asctime)s - %(levelname)s - %(message)s"

@dataclass
class AuralConfig:
    """Main configuration class for Aural."""
    # AI Models configuration
    SUPPORTED_MODELS: Dict[str, ModelConfig] = None
    
    # Hotwords for wake detection
    HOTWORDS: Dict[str, List[str]] = None
    
    # Home Assistant configuration
    HOME_ASSISTANT_DEFAULT_URL: str = "http://localhost:8123"
    
    # Speech recognition settings
    SPEECH_TIMEOUT: int = 10
    PHRASE_TIME_LIMIT: int = 20
    
    # GUI settings
    GUI_TITLE: str = "Aural Interface"
    GUI_FONT_FAMILY: str = "Arial"
    GUI_TITLE_SIZE: int = 24
    GUI_TEXT_SIZE: int = 12
    
    def __post_init__(self):
        if self.SUPPORTED_MODELS is None:
            self.SUPPORTED_MODELS = {
                "llama3.2": ModelConfig(
                    name="llama3.2"
                ),
                "dolphin-mistral": ModelConfig(
                    name="dolphin-mistral"
                ),
                "deepseek-r1:14b": ModelConfig(
                    name="deepseek-r1:14b",
                    requires_cleanup=True,
                    cleanup_pattern=r"<think>(.*?)</think>"
                )
            }
        
        if self.HOTWORDS is None:
            self.HOTWORDS = {
                "llama": ["hey llama", "llama", "llama are you there"],
                "dolphin": ["hey dolphin", "dolphin", "dolphin are you there"],
                "deepseek": ["hey deepseek", "deepseek", "deepseek are you there", "deep"]
            }

# Create default configuration
config = AuralConfig()

# Logging configuration
log_config = LogConfig()
