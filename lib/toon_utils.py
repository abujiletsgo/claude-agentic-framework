"""TOON (Token-Oriented Object Notation) encoder/decoder.

TOON encodes uniform lists of flat objects as a header + CSV rows,
achieving ~40% token savings over JSON for 10+ uniform records.

Format:
    [N,{field1,field2,...}]
    value1,value2,...
    value1,value2,...

Falls back to compact JSON for non-eligible data (nested, mixed-schema, non-list).
"""
import csv
import io
import json
import re
from typing import Any


def is_toon_eligible(data: Any) -> bool:
    """Check if data can be TOON-encoded (uniform list of flat dicts)."""
    if not isinstance(data, list) or len(data) == 0:
        return False
    if not all(isinstance(item, dict) for item in data):
        return False
    # All dicts must have the same keys
    keys = set(data[0].keys())
    if not all(set(item.keys()) == keys for item in data):
        return False
    # All values must be scalar (not dict or list)
    for item in data:
        for value in item.values():
            if isinstance(value, (dict, list)):
                return False
    return True


def _csv_encode_row(values: list) -> str:
    """Encode a single row as CSV, handling commas and quotes."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="")
    writer.writerow([str(v) if v is not None else "" for v in values])
    return output.getvalue()


def _parse_csv_line(line: str) -> list[str]:
    """Parse a single CSV line, respecting quoting rules."""
    reader = csv.reader(io.StringIO(line))
    for row in reader:
        return row
    return []


def encode_results(data: Any) -> str:
    """Encode data as TOON (if eligible) or compact JSON (fallback).

    Args:
        data: Any serializable Python value. Typically a list of dicts.

    Returns:
        TOON-encoded string or compact JSON string.
    """
    if is_toon_eligible(data):
        keys = list(data[0].keys())
        header = f"[{len(data)},{{{','.join(keys)}}}]"
        rows = [_csv_encode_row([item[k] for k in keys]) for item in data]
        return header + "\n" + "\n".join(rows)
    return json.dumps(data, separators=(",", ":"))


def decode_results(toon_str: str) -> Any:
    """Decode a TOON string or JSON string back to Python objects.

    Args:
        toon_str: Either a TOON-encoded string or a JSON string.

    Returns:
        List of dicts (from TOON) or whatever the JSON decoded to.
    """
    toon_str = toon_str.strip()
    # Detect TOON: starts with [N,{...}]
    match = re.match(r"^\[(\d+),\{([^}]+)\}\]", toon_str)
    if match:
        count = int(match.group(1))
        keys = [k.strip() for k in match.group(2).split(",")]
        lines = toon_str.split("\n")[1:]  # skip header
        result = []
        for line in lines[:count]:
            if not line.strip():
                continue
            values = _parse_csv_line(line)
            # Convert types: int-only digits, booleans, empty→None, else string
            converted = []
            for v in values:
                if re.match(r'^-?\d+$', v):
                    converted.append(int(v))
                elif v.lower() == "true":
                    converted.append(True)
                elif v.lower() == "false":
                    converted.append(False)
                elif v == "":
                    converted.append(None)
                else:
                    converted.append(v)
            row_dict = dict(zip(keys, converted))
            result.append(row_dict)
        return result
    # Fallback: JSON
    return json.loads(toon_str)
