# Rule Generation Contract

## Purity
Generated rules must be pure and deterministic. They must not:
- access the database directly
- make network calls
- read environment variables
- read or write files
- call Codex (no recursion)
- use `random` without a seeded `random.Random` instance
- depend on the current time except via `datetime` values passed in
  through the `InventorySnapshot`
- generated tests may import only from `rules._base`, the generated 
  rule file, and the Python standard library unless existing project 
  test helpers are required.

## Imports
Generated rules may only import from:
- `rules._base` (for `Rule`, `InventorySnapshot`, `Sku`, and the Action types)
- the Python standard library

No third-party imports. The rule loader runs a static AST check on
every rule file and rejects (quarantines) any file that violates this.

## Action types (closed set)
Rules return `list[Action]` where each Action is one of:
- `TagSku(sku: str, tag: str)`
- `SetVisibility(sku: str, state: Literal["visible", "low_stock_badge", "hidden"])`
- `ShowBanner(text: str, severity: Literal["info", "warning"])`
- `SendNotification(channel: Literal["admin"], text: str)`

## File naming
Generated rule names must be lowercase snake_case. Do not overwrite
existing rule or test files. If a name already exists, append `_2`, `_3`, etc.

## Test execution
After creating a rule and its test, run only:
    pytest tests/rules/test_<snake_name>.py -x -q

Iterate on failures until the test passes.

## Dependencies
No new dependencies during rule generation. No pip install, no edits
to pyproject.toml.
