from openai import OpenAI
from config import config

class TestGenerator:
    """Automates unit testing frameworks and mock profiles."""
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def generate_tests(self, code: str) -> str:
        """Generates comprehensive unit tests based on the source code."""
        prompt = (
            "Generate a comprehensive test suite (including happy paths, boundary constraints, and edge cases) "
            f"for this source code:\n\n{code}"
        )

        response = self.client.chat.completions.create(
            model=config.TESTER_MODEL,
            temperature=config.TEMPERATURE,
            messages=[
                {"role": "system", "value": "You are a QA automation expert. Output ONLY code for unit testing frameworks with standard assertions and mocks."},
                {"role": "user", "value": prompt}
            ]
        )
        
        return response.choices[0].message.content