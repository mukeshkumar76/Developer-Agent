from typing import Dict, Any
from groq import Groq
from config import config

class CodeGenerator:
    """Synthesizes business requirements into clean, production-grade code."""
    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)

    def generate(self, requirements: Dict[str, Any]) -> str:
        """Generates source code based on extracted technical requirements."""
        prompt = (
            f"Generate high-quality source code in {requirements.get('target_language', 'Java')}.\n"
            f"Core Logic: {requirements.get('core_logic')}\n"
            f"Data Structures: {requirements.get('data_structures')}\n"
            f"Functional Specs: {requirements.get('functional_requirements')}\n"
            "Provide ONLY the clean source code inside standard markdown blocks. Include comments."
        )

        message = self.client.messages.create(
            model=config.CODER_MODEL,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
            system="You are an elite software engineer. Write modular, robust, and clean code.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text