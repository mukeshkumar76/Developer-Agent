import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from brd_parser import BRDParser
from clarifications import ask_clarifying_questions, get_clarification_questions
from code_generator import CodeGenerator
from document_reader import read_document
from llm_client import chat_completion, parse_file_bundle
from main import _validate_generated_files, run_pipeline
from workspace import collect_project_context, redact_sensitive_content, validate_output_path, write_generated_files


class DocumentReaderTests(unittest.TestCase):
    def test_reads_brd_as_utf8_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "requirements.BRD")
            path.write_text("Build a reliable search service.", encoding="utf-8")
            self.assertEqual(read_document(path), "Build a reliable search service.")

    def test_reads_csv_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "requirements.csv")
            path.write_text("Feature,Priority\nSearch,High\n", encoding="utf-8")
            self.assertEqual(read_document(path), "Feature | Priority\nSearch | High")

    def test_rejects_unsupported_document_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "requirements.doc")
            path.write_bytes(b"legacy")
            with self.assertRaisesRegex(ValueError, "Unsupported requirements format"):
                read_document(path)

    def test_reads_docx_and_xlsx_documents(self) -> None:
        from docx import Document
        from openpyxl import Workbook

        with tempfile.TemporaryDirectory() as directory:
            docx_path = Path(directory, "requirements.docx")
            document = Document()
            document.add_paragraph("The service must support sign in.")
            document.save(docx_path)
            self.assertIn("support sign in", read_document(docx_path))

            xlsx_path = Path(directory, "requirements.xlsx")
            workbook = Workbook()
            workbook.active.append(["Feature", "Priority"])
            workbook.active.append(["Sign in", "High"])
            workbook.save(xlsx_path)
            self.assertIn("Sign in | High", read_document(xlsx_path))

    def test_reads_presentation_text_and_tables(self) -> None:
        from pptx import Presentation

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "requirements.pptx")
            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            textbox = slide.shapes.add_textbox(0, 0, 3000000, 500000)
            textbox.text = "Support mobile sign in"
            table = slide.shapes.add_table(1, 2, 0, 600000, 3000000, 500000).table
            table.cell(0, 0).text = "Availability"
            table.cell(0, 1).text = "99.9%"
            presentation.save(path)
            extracted = read_document(path)
            self.assertIn("Support mobile sign in", extracted)
            self.assertIn("Availability | 99.9%", extracted)

    def test_reads_project_pdf(self) -> None:
        pdf_path = Path(__file__).resolve().parents[1] / "BRDs" / "RAG_System.pdf"
        self.assertTrue(read_document(pdf_path))


class GeneratedProjectTests(unittest.TestCase):
    def test_questions_include_missing_quality_and_acceptance_targets(self) -> None:
        questions = get_clarification_questions(
            {
                "open_questions": [
                    {
                        "question": "Which vector store should be used?",
                        "reason": "No storage product is named.",
                        "suggested_default": "Choose one compatible with the deployment platform.",
                        "blocking": False,
                    }
                ],
                "non_functional_requirements": [],
                "acceptance_criteria": [],
            }
        )
        self.assertEqual(len(questions), 3)
        self.assertIn("vector store", questions[0]["question"])
        self.assertIn("non-functional", questions[1]["question"])
        self.assertIn("acceptance criteria", questions[2]["question"])

    def test_rag_brd_gaps_generate_domain_specific_questions(self) -> None:
        questions = get_clarification_questions(
            {
                "business_objectives": [
                    "Improve retrieval precision by 40%.",
                    "Reduce operational latency.",
                ],
                "functional_requirements": [
                    "Multi-agent orchestration for diverse domain tasks.",
                    "Hybrid indexing support (Vector + BM25).",
                ],
                "non_functional_requirements": [],
                "acceptance_criteria": [],
                "open_questions": [],
            }
        )
        question_text = "\n".join(item["question"].casefold() for item in questions)
        for expected_gap in (
            "agents",
            "knowledge sources",
            "embedding model",
            "bm25",
            "source citations",
            "baseline",
            "response-time targets",
        ):
            with self.subTest(gap=expected_gap):
                self.assertIn(expected_gap, question_text)

    def test_clarification_answers_are_added_to_requirements(self) -> None:
        requirements = {
            "open_questions": ["Which embedding model should be used?"],
            "non_functional_requirements": ["p95 under two seconds"],
            "acceptance_criteria": ["retrieved answers include sources"],
        }
        answers = ask_clarifying_questions(requirements, input_fn=lambda _: "Use the existing provider.")
        self.assertEqual(
            answers,
            [{"question": "Which embedding model should be used?", "answer": "Use the existing provider."}],
        )
        self.assertEqual(requirements["clarification_answers"], answers)

    def test_skipped_clarification_is_not_recorded_as_answer(self) -> None:
        requirements = {
            "open_questions": ["Which vector store should be used?"],
            "non_functional_requirements": ["secure"],
            "acceptance_criteria": ["works"],
        }
        answers = ask_clarifying_questions(requirements, input_fn=lambda _: "")
        self.assertEqual(answers, [])
        self.assertEqual(requirements["clarification_answers"], [])

    def test_requirements_parser_accepts_unspecified_target_language(self) -> None:
        response = '{"functional_requirements":["Build a search service"],"open_questions":[]}'
        with (
            patch.object(BRDParser, "read_file", return_value="Build a search service."),
            patch("brd_parser.chat_completion", return_value=response),
        ):
            requirements = BRDParser().parse("requirements.pdf")

        self.assertIsNone(requirements["target_language"])
        self.assertEqual(requirements["functional_requirements"], ["Build a search service"])

    def test_code_generator_infers_language_when_requirements_omit_it(self) -> None:
        response = '{"files":[{"path":"app.py","content":"print(1)"}]}'
        with patch("code_generator.chat_completion", return_value=response) as chat:
            CodeGenerator().generate({"functional_requirements": ["Build a service"]}, "### main.py")

        self.assertIn("Infer from the existing project context", chat.call_args.args[2])

    def test_code_generator_bounds_large_project_context(self) -> None:
        response = '{"files":[{"path":"app.py","content":"print(1)"}]}'
        context = "### README.md\n" + ("documentation " * 3000)
        context += "\n\n### main.py\nprint('existing project')"
        with patch("code_generator.chat_completion", return_value=response) as chat:
            CodeGenerator().generate(
                {"target_language": "Python", "functional_requirements": ["Build a service"]},
                context,
            )

        prompt = chat.call_args.args[2]
        self.assertLess(len(prompt), 10_000)
        self.assertIn("### main.py", prompt)

    def test_chat_completion_reduces_output_to_fit_request_token_budget(self) -> None:
        fake_config = SimpleNamespace(
            GROQ_API_KEY="test-key",
            TOKEN_ESTIMATE_CHARS_PER_TOKEN=2,
            TOKEN_ESTIMATE_OVERHEAD=256,
            MAX_REQUEST_TOKENS=7600,
            MIN_COMPLETION_TOKENS=256,
            MAX_TOKENS=2800,
            TEMPERATURE=0.2,
        )
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )
        with (
            patch("llm_client.config", fake_config),
            patch("groq.Groq") as groq_client,
        ):
            groq_client.return_value.chat.completions.create.return_value = fake_response
            result = chat_completion("model", "system", "x" * 10_000)

        self.assertEqual(result, "ok")
        options = groq_client.return_value.chat.completions.create.call_args.kwargs
        self.assertLess(options["max_tokens"], fake_config.MAX_TOKENS)
        estimated_input = ((10_006 + 1) // 2) + fake_config.TOKEN_ESTIMATE_OVERHEAD
        self.assertLessEqual(estimated_input + options["max_tokens"], fake_config.MAX_REQUEST_TOKENS)

    def test_chat_completion_rejects_prompt_before_sending_over_budget(self) -> None:
        fake_config = SimpleNamespace(
            GROQ_API_KEY="test-key",
            TOKEN_ESTIMATE_CHARS_PER_TOKEN=2,
            TOKEN_ESTIMATE_OVERHEAD=256,
            MAX_REQUEST_TOKENS=7600,
            MIN_COMPLETION_TOKENS=256,
            MAX_TOKENS=2800,
            TEMPERATURE=0.2,
        )
        with (
            patch("llm_client.config", fake_config),
            patch("groq.Groq") as groq_client,
        ):
            with self.assertRaisesRegex(ValueError, "prompt is too large"):
                chat_completion("model", "system", "x" * 30_000)
            groq_client.assert_not_called()

    def test_chat_completion_reports_groq_413_without_raw_traceback(self) -> None:
        import httpx
        from groq import APIStatusError

        fake_config = SimpleNamespace(
            GROQ_API_KEY="test-key",
            TOKEN_ESTIMATE_CHARS_PER_TOKEN=2,
            TOKEN_ESTIMATE_OVERHEAD=256,
            MAX_REQUEST_TOKENS=7600,
            MIN_COMPLETION_TOKENS=256,
            MAX_TOKENS=6000,
            TEMPERATURE=0.2,
        )
        response = httpx.Response(413, request=httpx.Request("POST", "https://api.groq.com"))
        api_error = APIStatusError("request too large", response=response, body=None)
        with (
            patch("llm_client.config", fake_config),
            patch("groq.Groq") as groq_client,
        ):
            groq_client.return_value.chat.completions.create.side_effect = api_error
            with self.assertRaisesRegex(RuntimeError, "exceeded the model's token limit"):
                chat_completion("model", "system", "short prompt")

    def test_parses_generated_file_bundle(self) -> None:
        files = parse_file_bundle(
            '{"files":[{"path":"src/app.py","content":"print(1)"}]}',
            stage="test",
        )
        self.assertEqual(files, {"src/app.py": "print(1)"})

    def test_rejects_invalid_generated_python(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "syntax error"):
                _validate_generated_files({"main.py": "def broken("}, directory)

    def test_refuses_parent_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "traverse parent"):
                validate_output_path(directory, "..\\outside.txt")

    def test_rejects_generated_environment_secret_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "environment secret files"):
                validate_output_path(directory, ".env")

    def test_does_not_overwrite_existing_files_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "main.py")
            target.write_text("original", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                write_generated_files(directory, {"main.py": "replacement"})
            self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_project_context_excludes_env_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Path(root, "main.py").write_text("print('hello')", encoding="utf-8")
            Path(root, ".env").write_text("TOKEN=do-not-share", encoding="utf-8")
            context = collect_project_context(root)
            self.assertIn("main.py", context)
            self.assertNotIn("do-not-share", context)

    def test_redacts_sensitive_assignments_and_bearer_tokens(self) -> None:
        content = (
            'API_KEY = "private-value"\n'
            "Authorization: Bearer abc123\n"
            '{"client_secret": "json-secret"}'
        )
        redacted = redact_sensitive_content(content)
        self.assertNotIn("private-value", redacted)
        self.assertNotIn("abc123", redacted)
        self.assertNotIn("json-secret", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_pipeline_writes_files_after_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory, "generated")
            with (
                patch("main.BRDParser.parse", return_value={"functional_requirements": ["A"]}),
                patch("main.collect_project_context", return_value="project context"),
                patch("main.CodeGenerator.generate", return_value={"src/app.py": "print('ok')"}),
                patch("main.TestGenerator.generate_tests", return_value={"tests/test_app.py": "assert True"}),
                patch("main.SecurityAnalyzer.analyze", return_value={"is_secure": True, "vulnerabilities": []}),
            ):
                paths = run_pipeline(
                    "requirements.srs",
                    project_dir=directory,
                    output_dir=str(output_dir),
                    interactive=False,
                )
            self.assertEqual(len(paths), 2)
            self.assertEqual(Path(output_dir, "src", "app.py").read_text(encoding="utf-8"), "print('ok')")

    def test_pipeline_does_not_write_if_security_review_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory, "generated")
            with (
                patch("main.BRDParser.parse", return_value={"functional_requirements": ["A"]}),
                patch("main.collect_project_context", return_value=""),
                patch("main.CodeGenerator.generate", return_value={"src/app.py": "print('ok')"}),
                patch("main.TestGenerator.generate_tests", return_value={"tests/test_app.py": "assert True"}),
                patch(
                    "main.SecurityAnalyzer.analyze",
                    return_value={"is_secure": False, "vulnerabilities": ["issue"], "remediation_advice": "fix it"},
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "no files were written"):
                    run_pipeline(
                        "requirements.srs",
                        project_dir=directory,
                        output_dir=str(output_dir),
                        max_retry_cycles=1,
                        interactive=False,
                    )
            self.assertFalse(output_dir.exists())

    def test_pipeline_passes_user_clarifications_to_generator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory, "generated")
            requirements = {
                "functional_requirements": ["Build a RAG service"],
                "open_questions": ["Which vector store should be used?"],
                "non_functional_requirements": ["Secure"],
                "acceptance_criteria": ["Answers cite sources"],
            }
            with (
                patch("main.BRDParser.parse", return_value=requirements),
                patch(
                    "builtins.input",
                    side_effect=["Use PostgreSQL with pgvector.", "", "", "", ""],
                ),
                patch("main.collect_project_context", return_value=""),
                patch(
                    "main.CodeGenerator.generate",
                    return_value={"app.py": "print('ok')"},
                ) as generate,
                patch("main.TestGenerator.generate_tests", return_value={"test_app.py": "assert True"}),
                patch("main.SecurityAnalyzer.analyze", return_value={"is_secure": True, "vulnerabilities": []}),
            ):
                run_pipeline("requirements.pdf", project_dir=directory, output_dir=str(output_dir))

            submitted_requirements = generate.call_args.args[0]
            self.assertEqual(
                submitted_requirements["clarification_answers"],
                [
                    {
                        "question": "Which vector store should be used?",
                        "answer": "Use PostgreSQL with pgvector.",
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
