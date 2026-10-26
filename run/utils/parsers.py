# uutils/parsers.py
import re
import json
import logging

logger = logging.getLogger("avangarde.parsers")


def extract_json(text: str) -> dict:
    """Extract and parse a JSON object from text."""
    if not text:
        return {}

    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    candidate = match.group(1) if match else text

    try:
        result = json.loads(candidate)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for opening_brace in re.finditer(r"\{", candidate):
        try:
            result, _ = decoder.raw_decode(candidate[opening_brace.start():])
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            continue

    return {}
