# AI Developer Agent

See [README.md](./README.md) for setup, supported requirements formats, and CLI usage.

The application accepts BRD, SRS, PRD, FRD/FSD, URS, API specifications, user stories, test plans, and related requirement material when saved in a supported file format. It extracts requirements, uses existing project files as bounded context, generates implementation and test files, checks Python syntax, and performs an advisory model-based security review.

Supported document extensions include `.brd`, `.srs`, `.prd`, `.frd`, `.fsd`, `.urs`, `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.csv`, `.md`, `.txt`, `.html`, `.json`, `.yaml`, `.yml`, `.xml`, `.proto`, `.puml`, and `.drawio`. Legacy `.doc`/`.xls` and image-only scanned documents require conversion or OCR before processing.

The agent writes generated files into a separate output directory, refuses to overwrite existing files unless `--overwrite` is specified, and does not execute generated code or tests.
