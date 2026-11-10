# Developer Agent

This command-line agent turns a requirements or specification document into a multi-file software project. It extracts requirements, inspects a bounded set of existing project files for conventions, generates source and test files, checks generated Python syntax, and requests an advisory model-based security review before writing output.

## Requirements document formats

Supported inputs:

- BRD/SRS/PRD/FRD/FSD/URS files and ordinary text or Markdown: `.brd`, `.srs`, `.prd`, `.frd`, `.fsd`, `.urs`, `.txt`, `.md`, `.rst`
- PDF, Word, spreadsheet, and presentation documents: `.pdf`, `.docx`, `.xlsx`, `.pptx`
- CSV and structured/text specifications: `.csv`, `.json`, `.yaml`, `.yml`, `.xml`, `.proto`, `.puml`, `.drawio`, `.html`, `.htm`
- API specifications such as OpenAPI/Swagger in YAML or JSON
- User stories, acceptance criteria, test plans, RFCs, and architecture documents when saved in a supported format

Legacy binary `.doc` and `.xls` files, scanned PDFs without extractable text, and image-only diagrams are not supported directly; convert them to a supported format or add OCR/document conversion first.

## Setup

1. Use Python 3.10 or later.
2. Install the packages: `python -m pip install -r requirements.txt`
3. Set `GROQ_API_KEY` in your environment or a local `.env` file. Do not commit credentials.

The model names can be overridden with `PARSER_MODEL`, `CODER_MODEL`, `SECURITY_MODEL`, and `TESTER_MODEL`. Requirement text and selected project source files are sent to the configured Groq API. Known secret assignments, common token forms, and private-key blocks are redacted; review documents and code before sending them to any external service.

LLM requests are kept below a conservative token budget: project context is prioritized and capped for code generation, and the requested output size is adjusted to leave room for the prompt. If the requirements alone exceed the budget, the agent reports that before sending the request.

## Run

```powershell
python main.py --requirements .\requirements\product.srs --project-dir . --output-dir .\generated_project
```

The previous `--brd` option remains an alias for `--requirements`. The project directory is read for context; generated files are written to the separate output directory. Existing files are not replaced unless `--overwrite` is explicitly supplied. Generation attempts are limited to 1-5 with `--max-retries`.

The requirements document does not have to specify a programming language: the agent infers it from the existing project when possible and otherwise asks the code generator to use Python and document that assumption.

Before generation, the agent asks about high-impact gaps reported by the requirements analyst and checks whether non-functional targets and measurable acceptance criteria are missing. For RAG requirements it also checks for agent roles/routing, ingestion and chunking, embeddings/vector storage, hybrid ranking, citations/no-evidence behavior, measurable quality targets, and scale targets. Answer a question or press Enter to let the generator make and document an assumption. Do not provide credentials or secrets. Use `--non-interactive` in scripts to skip questions and have assumptions documented instead.

Generated paths are restricted to the output directory. The agent does not execute generated code or tests. It checks generated Python files for syntax and asks the configured model for a security review; that review is advisory and is not a substitute for running project tests, static-analysis tools, or a professional security review.

## Modules

- `document_reader.py`: extracts text from supported requirement formats.
- `brd_parser.py`: converts extracted text into structured requirements.
- `workspace.py`: gathers bounded, secret-filtered project context and safely writes relative output paths.
- `code_generator.py`: generates implementation files.
- `test_generator.py`: generates test files.
- `security_analyser.py`: requests a model-based security review.
- `main.py`: CLI orchestration and Python syntax validation.
