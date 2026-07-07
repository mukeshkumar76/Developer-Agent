# AI Developer Agent: Automated Code & Test Generator

This autonomous Developer Agent processes Business Requirement Documents (`.brd`), writes secure production code in any programming language, and generates comprehensive JUnit test cases. It includes an automated security scanner to ensure no vulnerabilities are introduced.

---

## 🏗️ Project Architecture & File Details

### 1. `main.py`
* **Purpose:** The main entry point and orchestrator of the agent.
* **Explanation:** It handles CLI arguments, coordinates the pipeline, loads the `.brd` file, and passes data between the agent modules.

### 2. `brd_parser.py`
* **Purpose:** Extracts requirements from the input document.
* **Explanation:** Reads `.brd` files (text, markdown, or PDF) and uses an LLM to extract technical specifications, target language, and core business logic.

### 3. `code_generator.py`
* **Purpose:** Core code generation engine.
* **Explanation:** Synthesizes the extracted business requirements into clean, well-commented code in the requested programming language using advanced prompting techniques.

### 4. `security_analyzer.py`
* **Purpose:** Vulnerability prevention guardrail.
* **Explanation:** Performs static analysis and LLM-based security reviews on the generated code. It checks for OWASP Top 10 vulnerabilities and triggers a rewrite if flaws are found.

### 5. `test_generator.py`
* **Purpose:** Quality assurance automation.
* **Explanation:** Analyzes the generated code and automatically structures a comprehensive suite of JUnit test cases (including edge cases, mock objects, and assertions).

### 6. `config.py`
* **Purpose:** Centralized settings and environment management.
* **Explanation:** Manages API keys, model selection parameters (e.g., GPT-4o, Claude 3.5 Sonnet), temperature controls, and file output paths.

### 7. `requirements.txt`
* **Purpose:** Dependency registry.
* **Explanation:** Lists all required Python libraries, including LLM frameworks (like LangChain or Groq), PDF parsers, and environment managers.

---

## 🚀 Step-by-Step Development Guide

Follow these steps to build the Developer Agent from scratch.

### Step 1: Environment Setup
Initialize your project folder and install the required AI SDKs.
1. Create a project directory: `mkdir dev-agent && cd dev-agent`.
2. Create `requirements.txt` and add:
   ```text
   openai>=1.0.0
   langchain>=0.1.0
   pydantic>=2.0.0
   python-dotenv>=1.0.0
   ```
3. Run `pip install -r requirements.txt`.
4. Create a `.env` file to store your API key safely: `OPENAI_API_KEY=your_key_here`.

### Step 2: Build the Configuration Layer (`config.py`)
Set up the central settings file to handle environment variables and model configurations.
* Import `os` and `dotenv`.
* Load variables using `load_dotenv()`.
* Create a configuration class or dictionary containing the Model Name, Temperature (set close to `0.0` for coding consistency), and default timeout rules.
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    """Centralized configuration and environment management."""
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    
    
    # Model Selections
    PARSER_MODEL: str = "gpt-4o-mini"
    CODER_MODEL: str = "claude-3-5-sonnet-20240620"
    SECURITY_MODEL: str = "gpt-4o"
    TESTER_MODEL: str = "gpt-4o-mini"
    
    # Hyperparameters
    TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 4000
    
    # Path Configurations
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")

config = Config()

### Step 3: Develop the BRD Parser (`brd_parser.py`)
Build the module that reads incoming business requirements.
* Write a function to read the raw text from a `.brd` file path.
* Construct an LLM prompt that instructs the model to output a structured JSON object.
* The JSON schema must extract: `target_language`, `features_list`, `input_outputs`, and `constraints`.

import json
from typing import Dict, Any
from openai import OpenAI
from config import config

class BRDParser:
    """Extracts technical specifications and business rules from BRD files."""
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

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

### Step 4: Build the Secure Code Generator (`code_generator.py`)
Program the engine that turns requirements into application source code.
* Feed the parsed JSON requirements into this module.
* Craft a system prompt instructing the LLM: *"You are an expert polyglot developer. Write code in the target language. Do not output markdown wrappers. Ensure modular architecture."*
* Return the raw source code string.

from typing import Dict, Any
from anthropic import Anthropic
from config import config

class CodeGenerator:
    """Synthesizes business requirements into clean, production-grade code."""
    def __init__(self):
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

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

###  app.py  code
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Sample route for the home page
@app.route('/')
def index():
    return render_template('index.html')

# Sample API endpoint that the frontend can call
@app.route('/api/data', methods=['GET'])
def get_data():
    # You can integrate your custom logic or third-party APIs here
    dummy_data = {
        "status": "success",
        "message": "Welcome to your Flask application!",
        "items": ["Item 1", "Item 2", "Item 3"]
    }
    return jsonify(dummy_data)

# Route to test an external API request (requires 'requests' library)
@app.route('/fetch-external-data', methods=['GET'])
def fetch_external():
    try:
        response = requests.get("https://api.github.com")
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

### Step 5: Implement the Security Guardrail (`security_analyzer.py`)
Prevent security flaws before the code is saved to disk.
* Design a prompt that acts as a Senior Security Engineer.
* Instruct the LLM to scan the code for vulnerabilities (SQL Injection, XSS, Hardcoded Secrets, Insecure Deserialization).
* Implement a validation loop: If vulnerabilities are found, automatically feed the code back to `code_generator.py` with the security error log for a rewrite.
import json
from typing import Dict, Any
from openai import OpenAI
from config import config

class SecurityAnalyzer:
    """Evaluates code safety against vulnerabilities like OWASP Top 10."""
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

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

### Step 6: Create the JUnit Test Generator (`test_generator.py`)
Automate the testing cycle.
* This module takes the final approved source code as input.
* Construct a prompt optimized for Java/JUnit: *"Generate a JUnit 5 test file covering normal flows, boundaries, and exceptional states for the following code."*
* Save the output as a standard `.java` test file.
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


### Step 7: Assemble the Orchestrator (`main.py`)
Tie all modules together into a sequential pipeline.
1. Load configuration.
2. Read and parse the target `.brd` file.
3. Generate the source code.
4. Scan code for vulnerabilities (loop until secure).
5. Generate matching JUnit tests.
6. Write both final outputs to your `output/` directory.

import os
import argparse
from brd_parser import BRDParser
from code_generator import CodeGenerator
from security_analyzer import SecurityAnalyzer
from test_generator import TestGenerator
from config import config

def write_output(filename: str, content: str):
    """Saves generated strings directly to disk destinations."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    target_path = os.path.join(config.OUTPUT_DIR, filename)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f" Saved: {target_path}")

def run_pipeline(brd_path: str, max_retry_cycles: int = 3):
    """Coordinates modules step-by-step to process incoming BRD files safely."""
    print(f" Starting agentic workspace context for: {brd_path}")
    
    # 1. Parse Requirements
    parser = BRDParser()
    requirements = parser.parse(brd_path)
    print(" Complete: Requirements extracted successfully.")

    # 2. Iterative Generation & Validation Cycle
    codegen = CodeGenerator()
    analyzer = SecurityAnalyzer()
    
    generated_code = ""
    attempts = 0
    is_safe = False

    while attempts < max_retry_cycles and not is_safe:
        attempts += 1
        print(f" Generation pass {attempts}/{max_retry_cycles}...")
        
        # Inject context rules if fixing previous failures
        generated_code = codegen.generate(requirements)
        
        print(" Analyzing source security guardrails...")
        security_report = analyzer.analyze(generated_code)
        
        is_safe = security_report.get("is_secure", False)
        if is_safe:
            print(" Success: Code passed security checks.")
            break
        else:
            print(f" Warning: Security flaws detected. Retrying... Issues: {security_report.get('vulnerabilities')}")
            # Optional: Append feedback to requirements dict for the next pass
            requirements["functional_requirements"] += f"\nFIX CODE FOR FLAWS: {security_report.get('remediation_advice')}"

    if not is_safe:
        print(" Error: Maximum generation cycles reached without clearing security compliance checks.")
        return

    # 3. Generate Asserts and Write Outputs
    tester = TestGenerator()
    test_suite = tester.generate_tests(generated_code)

    write_output("GeneratedSource.txt", generated_code)
    write_output("TestSuite.txt", test_suite)
    print(" Process pipeline executed cleanly.")

if __name__ == "__main__":
    cli_parser = argparse.ArgumentParser(description="Multi-Agent Automated Code Pipeline")
    cli_parser.add_argument("--brd", type=str, required=True, help="Path to input .brd configuration document")
    args = cli_parser.parse_args()

    run_pipeline(args.brd)

###  Web page as templates/index.html

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Developer Agent - Requirement Hub</title>
    <style>
        :root {
            --bg-color: #f4f7f6;
            --card-bg: #ffffff;
            --text-color: #333333;
            --border-color: #d1d5db;
            --accent-color: #2563eb;
            --accent-hover: #1d4ed8;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }

        .container {
            background-color: var(--card-bg);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            width: 100%;
            max-width: 600px;
        }

        h2 {
            margin-top: 0;
            margin-bottom: 20px;
            font-size: 1.5rem;
            color: #111827;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            font-weight: 500;
            margin-bottom: 8px;
            color: #374151;
        }

        textarea {
            width: 100%;
            height: 150px;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            resize: vertical;
            font-family: inherit;
            font-size: 14px;
            box-sizing: border-box;
            background-color: #f9fafb;
            transition: border-color 0.2s;
        }

        textarea:focus {
            outline: none;
            border-color: var(--accent-color);
            background-color: #ffffff;
        }

        .file-upload-wrapper {
            border: 2px dashed var(--border-color);
            border-radius: 6px;
            padding: 20px;
            text-align: center;
            background-color: #f9fafb;
            cursor: pointer;
            transition: border-color 0.2s;
        }

        .file-upload-wrapper:hover {
            border-color: var(--accent-color);
        }

        input[type="file"] {
            display: none;
        }

        .file-upload-label {
            display: block;
            color: var(--accent-color);
            font-weight: 500;
            cursor: pointer;
        }

        .file-name-display {
            margin-top: 10px;
            font-size: 13px;
            color: #6b7280;
            font-style: italic;
        }

        button {
            width: 100%;
            background-color: var(--accent-color);
            color: white;
            border: none;
            padding: 14px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        button:hover {
            background-color: var(--accent-hover);
        }
    </style>
</head>
<body>

    <div class="container">
        <h2>Developer Agent Input</h2>
        <form id="agentRequirementForm">
            <!-- Jira Story Text Area -->
            <div class="form-group">
                <label for="jiraText">Paste Jira Story / SubTask:</label>
                <textarea id="jiraText" placeholder="Paste your Jira description, acceptance criteria, or technical requirements here..."></textarea>
            </div>

            <!-- Browse File Requirement -->
            <div class="form-group">
                <label>Or Upload Requirement File (e.g., .txt, .pdf, .md):</label>
                <div class="file-upload-wrapper" onclick="document.getElementById('requirementFile').click()">
                    <span class="file-upload-label">Browse Files</span>
                    <input type="file" id="requirementFile" accept=".txt,.pdf,.md,.doc,.docx" onchange="displayFileName()">
                    <div id="fileNameDisplay" class="file-name-display">No file selected</div>
                </div>
            </div>

            <!-- Submit Button -->
            <button type="submit" id="submitBtn">Generate Code</button>
        </form>
    </div>

    <script>
        function displayFileName() {
            const input = document.getElementById('requirementFile');
            const display = document.getElementById('fileNameDisplay');
            if (input.files.length > 0) {
                display.textContent = `Selected file: ${input.files[0].name}`;
            } else {
                display.textContent = 'No file selected';
            }
        }

        document.getElementById('agentRequirementForm').addEventListener('submit', function(e) {
            e.preventDefault(); 
            
            const jiraData = document.getElementById('jiraText').value;
            const fileInput = document.getElementById('requirementFile').files[0];

            if (!jiraData && !fileInput) {
                alert("Please paste a Jira story or upload a requirement file before submitting.");
                return;
            }

            // Logic to send requirement payload to your backend/developer agent
            alert("Requirements received! Developer agent is processing the context and generating code. Check console for output.");
            console.log("Submitting Jira Text:", jiraData);
            console.log("Submitting File:", fileInput ? fileInput.name : "None");
        });
    </script>

</body>
</html>

## 💻 How to Run the Agent

Execute the agent via the terminal by passing the path to your requirement file:

```bash
python main.py --brd ./requirements/payment_processor.brd
```




=======================main.py using Flask library========================
import os
from flask import Flask, render_template, request, redirect, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for flash messages
UPLOAD_FOLDER = 'uploads'          # Folder to temporarily store uploaded files
ALLOWED_EXTENSIONS = {'brd'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Ensure upload directory exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Here, you call the function from your main script
        # process_brd_file(file_path)
        
        flash('File successfully uploaded and processed!')
        return redirect('/')
    else:
        flash('Allowed file type is only .brd')
        return redirect('/')

if __name__ == "__main__":
    app.run(debug=True, port=5000)
	======================================
	=======================main.py using FastApi library========================
	
	from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="My FastAPI Project",
    description="A modern, high-performance API",
    version="1.0.0"
)

# Define a Pydantic model for request validation
class Item(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None

# Sample data store (mock database)
fake_db = {}

@app.get("/")
def read_root():
    return {"message": "Welcome to my FastAPI backend!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id, "q": q, "data": fake_db.get(item_id)}

@app.post("/items/")
def create_item(item: Item):
    # Auto-generates a mock ID and stores the validated payload
    new_id = len(fake_db) + 1
    fake_db[new_id] = item
    return {"message": "Item successfully created", "item_id": new_id, "data": item}