from typing import Any
import json

from config import config


def _estimate_tokens(text: str) -> int:
    return (
        (len(text) + config.TOKEN_ESTIMATE_CHARS_PER_TOKEN - 1)
        // config.TOKEN_ESTIMATE_CHARS_PER_TOKEN
    ) + config.TOKEN_ESTIMATE_OVERHEAD


def chat_completion(
    model: str,
    system_prompt: str,
    user_prompt: str,
    *,
    json_mode: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to the environment or .env file.")

    try:
        from groq import APIStatusError, Groq
    except ImportError as exc:
        raise RuntimeError("The Groq SDK is missing. Install dependencies with: pip install -r requirements.txt") from exc

    requested_output_tokens = config.MAX_TOKENS if max_tokens is None else max_tokens
    estimated_input_tokens = _estimate_tokens(system_prompt + user_prompt)
    available_output_tokens = config.MAX_REQUEST_TOKENS - estimated_input_tokens
    if available_output_tokens < config.MIN_COMPLETION_TOKENS:
        raise ValueError(
            "The prompt is too large for the configured Groq token budget. Reduce the requirements or project "
            "context and try again."
        )

    options: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": config.TEMPERATURE if temperature is None else temperature,
        "max_tokens": min(requested_output_tokens, available_output_tokens),
    }
    if json_mode:
        options["response_format"] = {"type": "json_object"}

    try:
        response = Groq(api_key=config.GROQ_API_KEY).chat.completions.create(**options)
    except APIStatusError as exc:
        if exc.status_code == 413:
            raise RuntimeError(
                "Groq rejected the request because it exceeded the model's token limit. Reduce the requirements "
                "or project context, or lower MAX_TOKENS in config.py."
            ) from exc
        raise
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"The model {model!r} returned an empty response.")
    return content


def parse_file_bundle(response: str, *, stage: str) -> dict[str, str]:
    try:
        payload = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{stage} response was not valid JSON: {exc}") from exc

    raw_files = payload.get("files") if isinstance(payload, dict) else None
    if isinstance(raw_files, dict):
        files = raw_files
    elif isinstance(raw_files, list):
        files = {}
        for item in raw_files:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise ValueError(f"{stage} response contains a file without a string path.")
            if item["path"] in files:
                raise ValueError(f"{stage} response contains a duplicate path: {item['path']!r}")
            files[item["path"]] = item.get("content")
    else:
        raise ValueError(f"{stage} response must contain a 'files' object or list.")

    if not files or any(not isinstance(path, str) or not isinstance(content, str) for path, content in files.items()):
        raise ValueError(f"{stage} response must contain at least one file with string paths and contents.")
    return files
