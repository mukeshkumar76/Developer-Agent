import argparse
import ast
from pathlib import Path
from typing import Any

from brd_parser import BRDParser
from clarifications import ask_clarifying_questions
from code_generator import CodeGenerator
from security_analyser import SecurityAnalyzer
from test_generator import TestGenerator
from workspace import collect_project_context, validate_output_path, write_generated_files


def _validate_generated_files(files: dict[str, str], output_dir: str) -> None:
    if not files:
        raise ValueError("The agent did not generate any files.")
    for relative_path, content in files.items():
        validate_output_path(output_dir, relative_path)
        if not content.strip():
            raise ValueError(f"Generated file is empty: {relative_path}")
        if Path(relative_path).suffix.lower() == ".py":
            try:
                ast.parse(content, filename=relative_path)
            except SyntaxError as exc:
                raise ValueError(f"Generated Python file has a syntax error ({relative_path}): {exc}") from exc


def run_pipeline(
    requirements_path: str,
    project_dir: str = ".",
    output_dir: str = "./generated_project",
    max_retry_cycles: int = 3,
    overwrite: bool = False,
    interactive: bool = True,
) -> list[Path]:
    if not 1 <= max_retry_cycles <= 5:
        raise ValueError("max_retry_cycles must be between 1 and 5.")

    print(f"Reading requirements: {requirements_path}")
    parser = BRDParser()
    requirements: dict[str, Any] = parser.parse(requirements_path)
    if interactive:
        ask_clarifying_questions(requirements)
    elif requirements.get("open_questions"):
        print("Skipping requirement clarifications (--non-interactive); the generator will use assumptions.")

    print(f"Inspecting project context: {project_dir}")
    project_context = collect_project_context(project_dir)
    code_generator = CodeGenerator()
    test_generator = TestGenerator()
    security_analyzer = SecurityAnalyzer()

    for attempt in range(1, max_retry_cycles + 1):
        print(f"Generating project (attempt {attempt}/{max_retry_cycles})...")
        code_files = code_generator.generate(requirements, project_context)
        test_files = test_generator.generate_tests(code_files, requirements)
        duplicates = code_files.keys() & test_files.keys()
        if duplicates:
            raise ValueError(f"Generated source and test files use the same path: {', '.join(sorted(duplicates))}")
        generated_files = {**code_files, **test_files}
        _validate_generated_files(generated_files, output_dir)

        print("Reviewing generated files...")
        report = security_analyzer.analyze(generated_files)
        if report["is_secure"] and not report.get("vulnerabilities"):
            paths = write_generated_files(output_dir, generated_files, overwrite=overwrite)
            print("Model-based advisory review found no flagged issues.")
            for path in paths:
                print(f"Saved: {path}")
            print("Generated code was not executed. Run the generated test suite in a trusted environment.")
            return paths

        findings = report.get("vulnerabilities", [])
        remediation = report.get("remediation_advice", "")
        print(f"Security review found issues: {findings}")
        if attempt < max_retry_cycles:
            requirements["security_review_feedback"] = {
                "vulnerabilities": findings,
                "remediation_advice": remediation,
            }

    raise RuntimeError(
        f"Security review did not clear after {max_retry_cycles} generation attempts; no files were written."
    )


def main() -> None:
    cli_parser = argparse.ArgumentParser(
        description="Generate a project from BRD, SRS, PRD, and other specification documents."
    )
    cli_parser.add_argument("--requirements", "--brd", dest="requirements", required=True, help="Requirements/specification file")
    cli_parser.add_argument("--project-dir", default=".", help="Existing project to inspect for context (default: current directory)")
    cli_parser.add_argument("--output-dir", default="./generated_project", help="Directory for generated files")
    cli_parser.add_argument("--max-retries", type=int, default=3, help="Maximum generation attempts (1-5)")
    cli_parser.add_argument("--overwrite", action="store_true", help="Allow replacing files already in the output directory")
    cli_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip questions and let the generator document assumptions",
    )
    args = cli_parser.parse_args()

    try:
        run_pipeline(
            args.requirements,
            project_dir=args.project_dir,
            output_dir=args.output_dir,
            max_retry_cycles=args.max_retries,
            overwrite=args.overwrite,
            interactive=not args.non_interactive,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError, RuntimeError, OSError) as exc:
        cli_parser.error(str(exc))


if __name__ == "__main__":
    main()
