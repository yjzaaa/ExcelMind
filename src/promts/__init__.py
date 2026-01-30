from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langchain_core.prompts import PromptTemplate


@lru_cache(maxsize=None)
def _read_prompt(filename: str) -> str:
    prompt_path = Path(__file__).with_name(filename)
    return prompt_path.read_text(encoding="utf-8")


SYSTEM_PROMPT = _read_prompt("system_prompt.md")
INTENT_ANALYSIS_PROMPT = _read_prompt("intent_analysis_prompt.md")
SQL_GENERATION_PROMPT = _read_prompt("sql_generation_prompt.md")
SQL_VALIDATION_PROMPT = _read_prompt("sql_validation_prompt.md")
ANSWER_REFINEMENT_PROMPT = _read_prompt("answer_refinement_prompt.md")
JOIN_SUGGEST_PROMPT = _read_prompt("join_suggest_prompt.md")
RESULT_REVIEW_PROMPT = _read_prompt("result_review_prompt.md")


def render_prompt(template: str, **kwargs: str) -> str:
    prompt = PromptTemplate.from_template(template, template_format="jinja2")
    return prompt.format(**kwargs)

__all__ = [
    "SYSTEM_PROMPT",
    "INTENT_ANALYSIS_PROMPT",
    "SQL_GENERATION_PROMPT",
    "SQL_VALIDATION_PROMPT",
    "ANSWER_REFINEMENT_PROMPT",
    "JOIN_SUGGEST_PROMPT",
    "RESULT_REVIEW_PROMPT",
    "render_prompt",
]
