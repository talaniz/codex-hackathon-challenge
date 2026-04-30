from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RuleFile
from app.services.rule_engine import INACTIVE_DRAFT, RULES_DIR
from rules._base import RuleValidationError, validate_rule_file


TESTS_RULES_DIR = Path("tests/rules")
MAX_ATTEMPTS = 3
DEFAULT_MODEL = "gpt-5.1-codex-mini"


@dataclass(frozen=True)
class GeneratedRuleSources:
    rule_source: str
    test_source: str
    log: str


@dataclass(frozen=True)
class RuleGenerationResult:
    rule_file: RuleFile
    rule_source: str
    test_source: str
    pytest_output: str
    passed: bool


@dataclass(frozen=True)
class PytestRun:
    output: str
    returncode: int


def generate_rule_draft(session: Session, description: str) -> RuleGenerationResult:
    clean_description = description.strip()
    if not clean_description:
        raise ValueError("Rule description is required.")

    snake_name = _unique_rule_name(session, _snake_name(clean_description))
    rule_path = RULES_DIR / f"{snake_name}.py"
    test_path = TESTS_RULES_DIR / f"test_{snake_name}.py"

    previous_failure = ""
    latest_sources: GeneratedRuleSources | None = None
    pytest_output = ""
    passed = False
    for _ in range(MAX_ATTEMPTS):
        latest_sources = _request_rule_sources(clean_description, snake_name, previous_failure)
        _write_generated_files(rule_path, test_path, latest_sources)
        pytest_run = _run_generated_test(test_path)
        pytest_output = pytest_run.output
        if pytest_run.returncode == 0:
            try:
                validate_rule_file(rule_path)
            except RuleValidationError as exc:
                pytest_output = f"{pytest_output}\n\nRule validation failed: {exc}"
                previous_failure = pytest_output
            else:
                passed = True
                break
        else:
            previous_failure = pytest_output

    if latest_sources is None:
        raise RuntimeError("Codex did not return generated rule files.")

    record = RuleFile(
        filename=rule_path.name,
        test_filename=str(test_path),
        description=clean_description,
        status=INACTIVE_DRAFT,
        status_detail="Ready to activate." if passed else "Generated rule did not pass validation or tests.",
        generation_log=_generation_log(latest_sources.log, pytest_output),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return RuleGenerationResult(
        rule_file=record,
        rule_source=rule_path.read_text(),
        test_source=test_path.read_text(),
        pytest_output=pytest_output,
        passed=passed,
    )


def _request_rule_sources(description: str, snake_name: str, previous_failure: str) -> GeneratedRuleSources:
    prompt = _build_prompt(description, snake_name, previous_failure)
    client = OpenAI()
    response = client.responses.create(
        model=os.getenv("OPENAI_CODEX_MODEL", DEFAULT_MODEL),
        input=prompt,
    )
    text = response.output_text
    payload = _parse_json_payload(text)
    return GeneratedRuleSources(
        rule_source=str(payload["rule_source"]).strip() + "\n",
        test_source=str(payload["test_source"]).strip() + "\n",
        log=str(payload.get("log", "")).strip(),
    )


def _build_prompt(description: str, snake_name: str, previous_failure: str) -> str:
    failure_section = f"\nPrevious pytest/validation failure:\n{previous_failure}\n" if previous_failure else ""
    example_rule = (RULES_DIR / "example_clearance.py").read_text()
    example_test = Path("tests/rules/test_example_clearance.py").read_text()
    return f"""
Create a pure deterministic inventory rule and pytest test for this admin request:

{description}

Use rule module name: rules/{snake_name}.py
Use test module name: tests/rules/test_{snake_name}.py

Return JSON only with keys rule_source, test_source, and log.

Generated rule constraints:
- Import only from rules._base and the Python standard library.
- Expose RULE as a rules._base.Rule.
- Return only TagSku, SetVisibility, ShowBanner, or SendNotification actions.
- Use these exact action constructors:
  - TagSku(sku: str, tag: str)
  - SetVisibility(sku: str, state: "visible" | "low_stock_badge" | "hidden")
  - ShowBanner(text: str, severity: "info" | "warning")
  - SendNotification(channel: "admin", text: str)
- ShowBanner uses text= for its message content. Never use message= with ShowBanner.
- For product-type requests like hoodies, sweaters, tees, or denim, match against sku.name as well as sku.category.
  Seeded categories may be broad values like Men, Women, Basics, or Denim, while the product type may appear only in sku.name.
- For discount display requests, tag affected products with TagSku using a tag shaped like spring-wide-15-discount.
  The storefront derives strikethrough and discounted detail-page prices from tags ending in <percent>-discount.
- Do not access files, network, environment, database, current time, or Codex.
- Tests may import only rules._base, rules.{snake_name}, and the Python standard library.
- Keep tests focused and deterministic.

Reference rule:
```python
{example_rule}
```

Reference test:
```python
{example_test}
```
{failure_section}
""".strip()


def _parse_json_payload(text: str) -> dict[str, object]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fenced is not None:
        cleaned = fenced.group(1).strip()
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Codex response must be a JSON object.")
    if "rule_source" not in payload or "test_source" not in payload:
        raise ValueError("Codex response must include rule_source and test_source.")
    return payload


def _run_generated_test(test_path: Path) -> PytestRun:
    completed = subprocess.run(
        ["pytest", str(test_path), "-x", "-q"],
        check=False,
        capture_output=True,
        text=True,
    )
    return PytestRun(output=f"{completed.stdout}{completed.stderr}", returncode=completed.returncode)


def _write_generated_files(rule_path: Path, test_path: Path, sources: GeneratedRuleSources) -> None:
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.parent.mkdir(parents=True, exist_ok=True)
    rule_path.write_text(sources.rule_source)
    test_path.write_text(sources.test_source)


def _unique_rule_name(session: Session, base_name: str) -> str:
    existing_files = {path.stem for path in RULES_DIR.glob("*.py")} if RULES_DIR.exists() else set()
    existing_records = {Path(filename).stem for filename in session.scalars(select(RuleFile.filename)).all()}
    existing = existing_files | existing_records
    candidate = base_name
    index = 2
    while candidate in existing or (TESTS_RULES_DIR / f"test_{candidate}.py").exists():
        candidate = f"{base_name}_{index}"
        index += 1
    return candidate


def _snake_name(text: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    name = re.sub(r"_+", "_", name)
    if not name:
        return "generated_rule"
    if name[0].isdigit():
        return f"rule_{name}"
    return name[:80].strip("_") or "generated_rule"


def _generation_log(codex_log: str, pytest_output: str) -> str:
    parts = []
    if codex_log:
        parts.append(codex_log)
    if pytest_output:
        parts.append(pytest_output)
    return "\n\n".join(parts)
