import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    PARSER_MODEL: str = os.getenv("PARSER_MODEL", "openai/gpt-oss-20b")
    CODER_MODEL: str = os.getenv("CODER_MODEL", "openai/gpt-oss-120b")
    SECURITY_MODEL: str = os.getenv("SECURITY_MODEL", "openai/gpt-oss-safeguard-20b")
    TESTER_MODEL: str = os.getenv("TESTER_MODEL", "openai/gpt-oss-20b")
    TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 6000
    MAX_REQUEST_TOKENS: int = 7600
    MIN_COMPLETION_TOKENS: int = 256
    TOKEN_ESTIMATE_CHARS_PER_TOKEN: int = 2
    TOKEN_ESTIMATE_OVERHEAD: int = 256
    MAX_CODEGEN_CONTEXT_CHARS: int = 4000
    MAX_DOCUMENT_CHARS: int = 100_000
    MAX_DOCUMENT_BYTES: int = 20 * 1024 * 1024
    MAX_CONTEXT_CHARS: int = 100_000
    MAX_CONTEXT_FILES: int = 50


config = Config()
