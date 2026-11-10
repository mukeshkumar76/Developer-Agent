import csv
import html
import io
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable

from config import config


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _read_optional_module(module_name: str, package_name: str) -> object:
    try:
        return __import__(module_name, fromlist=["*"])
    except ImportError as exc:
        raise RuntimeError(
            f"Reading this document requires {package_name}. Install dependencies with: pip install -r requirements.txt"
        ) from exc


def _read_pdf(data: bytes) -> str:
    module = _read_optional_module("pypdf", "pypdf")
    reader = module.PdfReader(io.BytesIO(data))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(data: bytes) -> str:
    module = _read_optional_module("docx", "python-docx")
    document = module.Document(io.BytesIO(data))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        paragraphs.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows)
    return "\n".join(paragraphs)


def _read_xlsx(data: bytes) -> str:
    module = _read_optional_module("openpyxl", "openpyxl")
    workbook = module.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheets = []
    for sheet in workbook.worksheets:
        rows = [" | ".join("" if value is None else str(value) for value in row) for row in sheet.iter_rows(values_only=True)]
        sheets.append(f"## Sheet: {sheet.title}\n" + "\n".join(rows))
    return "\n\n".join(sheets)


def _read_pptx(data: bytes) -> str:
    module = _read_optional_module("pptx", "python-pptx")
    presentation = module.Presentation(io.BytesIO(data))
    slides = []
    for index, slide in enumerate(presentation.slides, start=1):
        text = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.text.strip():
                text.append(shape.text)
            elif getattr(shape, "has_table", False):
                text.extend(
                    " | ".join(cell.text for cell in row.cells)
                    for row in shape.table.rows
                )
        slides.append(f"## Slide {index}\n" + "\n".join(text))
    return "\n\n".join(slides)


def _read_csv(data: bytes) -> str:
    text = data.decode("utf-8-sig")
    return "\n".join(" | ".join(row) for row in csv.reader(io.StringIO(text)))


def read_document(file_path: str | Path) -> str:
    """Extract text from supported requirements and specification formats."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Requirements file not found: {path}")
    if path.stat().st_size > config.MAX_DOCUMENT_BYTES:
        raise ValueError(f"Requirements file exceeds the {config.MAX_DOCUMENT_BYTES // (1024 * 1024)} MB limit: {path}")

    suffix = path.suffix.lower()
    data = path.read_bytes()
    readers: dict[str, Callable[[bytes], str]] = {
        ".pdf": _read_pdf,
        ".docx": _read_docx,
        ".xlsx": _read_xlsx,
        ".pptx": _read_pptx,
        ".csv": _read_csv,
    }
    if suffix in readers:
        content = readers[suffix](data)
    elif suffix in {".brd", ".srs", ".prd", ".frd", ".fsd", ".urs", ".txt", ".md", ".rst", ".yaml", ".yml", ".json", ".xml", ".proto", ".puml", ".drawio", ".html", ".htm"}:
        content = data.decode("utf-8-sig")
        if suffix in {".html", ".htm"}:
            parser = _TextExtractor()
            parser.feed(content)
            content = html.unescape("\n".join(parser.parts))
        elif suffix == ".json":
            content = json.dumps(json.loads(content), ensure_ascii=False, indent=2)
    else:
        raise ValueError(f"Unsupported requirements format {suffix or '(no extension)'!r}: {path}")

    content = content.strip()
    if not content:
        raise ValueError(f"No readable text was extracted from requirements file: {path}")
    if len(content) > config.MAX_DOCUMENT_CHARS:
        raise ValueError(
            f"Extracted requirements exceed the {config.MAX_DOCUMENT_CHARS:,}-character limit: {path}"
        )
    return content
