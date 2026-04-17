import json
import re
from typing import Any


def _strip_code_fences(text: str) -> str:
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text.strip(), flags=re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text.strip()


def _try_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _normalize_common_llm_json_issues(text: str) -> str:
    # Replace smart quotes that frequently appear in model outputs.
    normalized = (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )

    # Escape literal newlines occurring inside JSON strings.
    chars = []
    in_string = False
    escaped = False
    for ch in normalized:
        if escaped:
            chars.append(ch)
            escaped = False
            continue

        if ch == "\\":
            chars.append(ch)
            escaped = True
            continue

        if ch == '"':
            chars.append(ch)
            in_string = not in_string
            continue

        if in_string and ch == "\n":
            chars.append("\\n")
            continue

        if in_string and ch == "\r":
            # Drop carriage return and keep normalized newlines as \n.
            continue

        chars.append(ch)

    return "".join(chars)


def _try_parse_nested_json(text: str, max_depth: int = 2) -> Any:
    current = text
    for _ in range(max_depth + 1):
        loaded = _try_json_loads(current)
        if loaded is None:
            loaded = _try_json_loads(_normalize_common_llm_json_issues(current))
        if loaded is None:
            return None
        if not isinstance(loaded, str):
            return loaded
        current = _strip_code_fences(loaded)
    return None


def parse_json_response(raw_text: str) -> Any:
    text = (raw_text or "").strip()
    if not text:
        return {}

    text = _strip_code_fences(text)

    nested = _try_parse_nested_json(text)
    if nested is not None:
        return nested

    object_match = re.search(r"\{[\s\S]*\}", text)
    if object_match:
        candidate = _strip_code_fences(object_match.group(0))
        nested = _try_parse_nested_json(candidate)
        if nested is not None:
            return nested

    array_match = re.search(r"\[[\s\S]*\]", text)
    if array_match:
        candidate = _strip_code_fences(array_match.group(0))
        nested = _try_parse_nested_json(candidate)
        if nested is not None:
            return nested

    return {"raw_output": text}
