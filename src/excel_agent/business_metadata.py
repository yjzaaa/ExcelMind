from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional


_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _metadata_path() -> Path:
    return _project_root() / "business" / "metadata.md"


def _extract_json_block(text: str) -> Dict[str, Any]:
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


@lru_cache(maxsize=1)
def load_business_metadata() -> Dict[str, Any]:
    path = _metadata_path()
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    return _extract_json_block(content)


def _parse_intent_type(intent_analysis: Any) -> Optional[str]:
    if intent_analysis is None:
        return None

    if hasattr(intent_analysis, "intent_type"):
        return str(getattr(intent_analysis, "intent_type") or "").strip() or None

    if isinstance(intent_analysis, dict):
        intent = intent_analysis.get("intent_type") or intent_analysis.get("intent")
        return str(intent).strip() if intent else None

    content = getattr(intent_analysis, "content", None)
    if not content and isinstance(intent_analysis, str):
        content = intent_analysis

    if not content:
        return None

    match = _JSON_BLOCK_RE.search(content)
    raw = match.group(1) if match else content
    try:
        data = json.loads(raw)
        intent = data.get("intent_type") or data.get("intent")
        return str(intent).strip() if intent else None
    except json.JSONDecodeError:
        pass

    m = re.search(r"intent_type\s*[:=]\s*['\"]?([A-Za-z0-9_\-]+)", content)
    if m:
        return m.group(1)
    return None


def resolve_table_names(user_query: str, intent_analysis: Any = None) -> List[str]:
    metadata = load_business_metadata()
    if not metadata:
        return []

    tables_map = metadata.get("tables", {})
    intent_map = metadata.get("intent_table_map", {})
    keyword_map = metadata.get("keyword_table_map", {})
    default_tables = metadata.get("default_tables", [])

    resolved_keys: List[str] = []
    intent_type = _parse_intent_type(intent_analysis)
    if intent_type and intent_type in intent_map:
        resolved_keys.extend(intent_map[intent_type])

    query_lower = (user_query or "").lower()
    for keyword, table_keys in keyword_map.items():
        if keyword.lower() in query_lower:
            resolved_keys.extend(table_keys)

    if not resolved_keys and default_tables:
        resolved_keys.extend(default_tables)

    resolved: List[str] = []
    for key in resolved_keys:
        if key in tables_map:
            resolved.append(tables_map[key])
        elif key in tables_map.values():
            resolved.append(key)

    seen = set()
    deduped = []
    for t in resolved:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped