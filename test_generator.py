from config import config
from llm_client import chat_completion, parse_file_bundle


class TestGenerator:
    """Generates test source files for a generated project."""

    def generate_tests(self, code_files: dict[str, str], requirements: dict[str, object]) -> dict[str, str]:
        prompt = (
            "Create runnable unit tests for the supplied implementation. Use the project's target language and "
            "test framework. Cover normal behavior, boundary conditions, invalid input, and important failure "
            "cases. Return JSON only, in the form {\"files\":[{\"path\":\"relative/test/path\",\"content\":\"...\"}]}. "
            "If the supplied code cannot be tested as-is, make reasonable test assumptions explicit in the test "
            "file rather than claiming success.\n\n"
            f"Requirements: {requirements}\n\nGenerated source files:\n{code_files}"
        )
        response = chat_completion(
            config.TESTER_MODEL,
            "You are a QA engineer. Generate actual test files, not a prose report. Do not execute code.",
            prompt,
            json_mode=True,
        )
        return parse_file_bundle(response, stage="Test generator")
