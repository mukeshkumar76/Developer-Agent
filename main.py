import os
import argparse
from brd_parser import BRDParser
from code_generator import CodeGenerator
from security_analyser import SecurityAnalyzer
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
    cli_parser.add_argument("--brd", type=str, required=True, help="Path to input .pdf configuration document")
    args = cli_parser.parse_args()

    run_pipeline(args.pdf)