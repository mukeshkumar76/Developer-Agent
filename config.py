import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    """Centralized configuration and environment management."""
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    
    # Updated Model Selections for Groq
    # GPT-OSS-20B is excellent for fast, lightweight tasks like parsing/testing
    PARSER_MODEL: str = "openai/gpt-oss-20b"
    
    # GPT-OSS-120B is the flagship reasoning model, ideal for complex coding
    CODER_MODEL: str = "openai/gpt-oss-120b"
    
    # GPT-OSS-Safeguard-20B is specifically optimized for security and policy tasks
    SECURITY_MODEL: str = "openai/gpt-oss-safeguard-20b"
    
    # GPT-OSS-20B provides efficient, low-latency performance for testing
    TESTER_MODEL: str = "openai/gpt-oss-20b"
    
    # Hyperparameters
    TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 4000
    
    # Path Configurations
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")

config = Config()