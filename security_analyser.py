import json
from typing import Dict, Any
from groq import Groq
from config import config

class SecurityAnalyzer:
    """Evaluates code safety against vulnerabilities like OWASP Top 10."""
    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)

    def analyze(self, code: str) -> Dict[str, Any]:
        """Runs a predictive static review via LLM."""
        prompt = (
            "Analyze the following source code for vulnerabilities (OWASP Top 10, injections, leaks).\n"
            f"Source Code:\n{code}"
        )

        response = self.client.chat.completions.create(
            model=config.SECURITY_MODEL,
            temperature=0.0,  # Strict determinism for security checks
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "value": "Analyze code security. Output JSON with fields: 'is_secure' (boolean), 'vulnerabilities' (list of strings), and 'remediation_advice' (string)."},
                {"role": "user", "value": prompt}
            ]
        )
        
        return json.loads(response.choices[0].message.content)