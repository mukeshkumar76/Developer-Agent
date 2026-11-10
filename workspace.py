import os
import re
from pathlib import Path, PureWindowsPath

from config import config

CONTEXT_SUFFIXES = {
    ".c", ".cfg", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html", ".java", ".js", ".json",
    ".jsx", ".md", ".mjs", ".php", ".py", ".rb", ".rs", ".rst", ".sql", ".swift", ".toml", ".ts",
    ".tsx", ".txt", ".xml", ".yaml", ".yml",
}
CONTEXT_FILENAMES = {"Dockerfile", "Makefile", "requirements.txt", "pyproject.toml", "package.json"}
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__", "dist", "build",
    "coverage", ".next", ".cache", "generated_project",
}
SECRET_NAMES = {"secrets", "credentials", "id_rsa", "id_ed25519"}
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b[\w.-]*(?:api[_-]?key|secret|password|passwd|token|credential|private[_-]?key|access[_-]?key)[\w.-]*\b\s*['\"]?\s*[:=]\s*)"
    r"('[^']*'|\"[^\"]*\"|[^,\s}]+)"
)
BEARER_TOKEN = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/-]+=*")
KNOWN_TOKEN = re.compile(
    r"\b(?:sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b"
)
PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----"
)


def redact_sensitive_content(content: str) -> str:
    content = PRIVATE_KEY_BLOCK.sub("[REDACTED PRIVATE KEY]", content)
    content = SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", content)
    content = BEARER_TOKEN.sub(r"\1[REDACTED]", content)
    return KNOWN_TOKEN.sub("[REDACTED TOKEN]", content)


def collect_project_context(project_dir: str | Path) -> str:
    root = Path(project_dir).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Project directory does not exist: {root}")

    sections: list[str] = []
    total_chars = 0
    file_count = 0
    for current, dirs, filenames in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS and not name.startswith(".")]
        for filename in sorted(filenames):
            path = Path(current, filename)
            if filename.lower().startswith(".env") or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
                continue
            if path.stem.lower() in SECRET_NAMES or (
                path.suffix.lower() not in CONTEXT_SUFFIXES and filename not in CONTEXT_FILENAMES
            ):
                continue
            if path.is_symlink() or path.stat().st_size > 64_000:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            relative = path.relative_to(root).as_posix()
            section = f"### {relative}\n{redact_sensitive_content(content).strip()}"
            if file_count >= config.MAX_CONTEXT_FILES or total_chars + len(section) > config.MAX_CONTEXT_CHARS:
                return "\n\n".join(sections)
            sections.append(section)
            file_count += 1
            total_chars += len(section)
    return "\n\n".join(sections)


def validate_output_path(output_dir: str | Path, relative_path: str) -> Path:
    if not relative_path or "\0" in relative_path:
        raise ValueError("Generated file paths must be non-empty relative paths.")
    normalized = relative_path.replace("\\", "/")
    windows_path = PureWindowsPath(relative_path)
    candidate_path = Path(normalized)
    if candidate_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise ValueError(f"Generated file path must be relative: {relative_path!r}")
    if ".." in candidate_path.parts or ".." in windows_path.parts:
        raise ValueError(f"Generated file path cannot traverse parent directories: {relative_path!r}")
    filename = candidate_path.name.lower()
    if filename == ".env" or filename.startswith(".env.") and filename != ".env.example":
        raise ValueError("Generated output cannot contain environment secret files; use .env.example.")
    if candidate_path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
        raise ValueError(f"Generated output cannot contain private key files: {relative_path!r}")
    if candidate_path.parts == (".",):
        raise ValueError("Generated file path must name a file.")

    root = Path(output_dir).resolve()
    target = (root / candidate_path).resolve()
    if os.path.commonpath((str(root), str(target))) != str(root):
        raise ValueError(f"Generated file path escapes the output directory: {relative_path!r}")
    return target


def write_generated_files(
    output_dir: str | Path,
    files: dict[str, str],
    *,
    overwrite: bool = False,
) -> list[Path]:
    if not files:
        raise ValueError("The agent did not generate any files.")

    destinations = [(validate_output_path(output_dir, name), name, content) for name, content in files.items()]
    resolved_paths = [path for path, _, _ in destinations]
    if len(set(resolved_paths)) != len(resolved_paths):
        raise ValueError("Generated output contains duplicate file paths.")
    collisions = [path for path in resolved_paths if path.exists()]
    if collisions and not overwrite:
        names = ", ".join(str(path) for path in collisions)
        raise FileExistsError(f"Refusing to overwrite existing files (use --overwrite to replace): {names}")

    for path, _, content in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return resolved_paths
