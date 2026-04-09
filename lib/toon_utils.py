"""
TOON (Token-Oriented Object Notation) encoder/decoder for CAF inter-agent data.
Only use for uniform arrays of objects. Falls back to JSON for everything else.

Usage:
    from lib.toon_utils import encode_results, decode_results

    # Encode search results for passing to orchestrator
    toon_str = encode_results(papers_list)

    # Decode back to Python dicts
    papers = decode_results(toon_str)
"""
import json
from typing import Any


def is_toon_eligible(data: list[dict]) -> bool:
    """Check if data is a uniform array of flat objects (TOON sweet spot)."""
    if not data or not isinstance(data, list):
        return False
    if not all(isinstance(item, dict) for item in data):
        return False
    keys = set(data[0].keys())
    if not all(set(item.keys()) == keys for item in data):
        return False
    # Check all values are primitives (no nesting)
    for item in data:
        for v in item.values():
            if isinstance(v, (dict, list)):
                return False
    return True


def encode_results(data: list[dict]) -> str:
    """Encode uniform list of dicts as TOON. Falls back to compact JSON."""
    if not is_toon_eligible(data):
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    keys = list(data[0].keys())
    header = f"[{len(data)},{{{','.join(keys)}}}]"
    rows = []
    for item in data:
        vals = []
        for k in keys:
            v = item[k]
            if v is None:
                vals.append("")
            elif isinstance(v, bool):
                vals.append("true" if v else "false")
            elif isinstance(v, str):
                # Escape commas in values
                if "," in v or "\n" in v:
                    vals.append(f'"{v}"')
                else:
                    vals.append(v)
            else:
                vals.append(str(v))
        rows.append(",".join(vals))

    return header + "\n" + "\n".join(rows)


def decode_results(toon_str: str) -> list[dict]:
    """Decode TOON back to list of dicts. Handles JSON fallback."""
    toon_str = toon_str.strip()
    if toon_str.startswith("[{") or toon_str.startswith('["'):
        return json.loads(toon_str)

    lines = toon_str.split("\n")
    header = lines[0]

    # Parse header: [N,{field1,field2,...}]
    inner = header.strip("[]")
    count_str, fields_str = inner.split(",{", 1)
    fields_str = fields_str.rstrip("}")
    fields = fields_str.split(",")

    results = []
    for line in lines[1:]:
        if not line.strip():
            continue
        # Simple CSV parse (handles quoted values)
        vals = _parse_csv_line(line)
        item = {}
        for i, field in enumerate(fields):
            if i < len(vals):
                item[field] = vals[i] if vals[i] != "" else None
            else:
                item[field] = None
        results.append(item)

    return results


def _parse_csv_line(line: str) -> list[str]:
    """Parse a CSV line handling quoted values."""
    vals = []
    current = ""
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            vals.append(current)
            current = ""
        else:
            current += ch
    vals.append(current)
    return vals
