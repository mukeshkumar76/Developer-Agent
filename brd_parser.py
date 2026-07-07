import json
from typing import Dict, Any
from groq import Groq
from config import config

class BRDParser:
    """Extracts technical specifications and business rules from BRD files."""
    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)

    def read_file(self, file_path: str) -> str:
        """Reads raw text from the specified path."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def parse(self, file_path: str) -> Dict[str, Any]:
        """Uses LLM structured outputs to parse the input file."""
        raw_content = self.read_file(file_path)
        
        prompt = (
            "Analyze this Business Requirements Document (BRD). Extract core "
            "business logic, data models, functional requirements, and target language.\n"
            f"Document Content:\n{raw_content}"
        )

        response = self.client.chat.completions.create(
            model=config.PARSER_MODEL,
            temperature=config.TEMPERATURE,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "value": "You are an expert systems architect. Output a JSON object containing keys: 'target_language', 'core_logic', 'data_structures', and 'functional_requirements'."},
                {"role": "user", "value": prompt}
            ]
        )
        
        return json.loads(response.choices[0].message.content)