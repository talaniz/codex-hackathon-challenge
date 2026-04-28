from __future__ import annotations

import ast
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias


@dataclass(frozen=True)
class Sku:
    sku: str
    name: str
    category: str
    price_cents: int
    stock_count: int


@dataclass(frozen=True)
class InventorySnapshot:
    skus: tuple[Sku, ...]


@dataclass(frozen=True)
class TagSku:
    sku: str
    tag: str


@dataclass(frozen=True)
class SetVisibility:
    sku: str
    state: Literal["visible", "low_stock_badge", "hidden"]


@dataclass(frozen=True)
class ShowBanner:
    text: str
    severity: Literal["info", "warning"]


@dataclass(frozen=True)
class SendNotification:
    channel: Literal["admin"]
    text: str


Action: TypeAlias = TagSku | SetVisibility | ShowBanner | SendNotification


@dataclass(frozen=True)
class Rule:
    name: str
    description: str
    evaluate: Callable[[InventorySnapshot], list[Action]]


class RuleValidationError(ValueError):
    pass


ALLOWED_PROJECT_IMPORTS = {"rules._base"}
ALLOWED_STDLIB_IMPORTS = set(sys.stdlib_module_names) | {"__future__"}


def validate_rule_file(path: str | Path) -> None:
    rule_path = Path(path)
    try:
        tree = ast.parse(rule_path.read_text(), filename=str(rule_path))
    except SyntaxError as exc:
        raise RuleValidationError(f"{rule_path.name} has invalid Python syntax: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _validate_import(alias.name, rule_path)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None or node.level != 0:
                raise RuleValidationError(f"{rule_path.name} uses a relative import")
            _validate_import(node.module, rule_path)


def _validate_import(module_name: str, rule_path: Path) -> None:
    if module_name in ALLOWED_PROJECT_IMPORTS:
        return
    root_name = module_name.split(".", 1)[0]
    if root_name in ALLOWED_STDLIB_IMPORTS:
        return
    raise RuleValidationError(f"{rule_path.name} imports disallowed module '{module_name}'")
