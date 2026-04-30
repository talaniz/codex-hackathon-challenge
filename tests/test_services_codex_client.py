from app.services.codex_client import _build_prompt


def test_build_prompt_lists_exact_show_banner_constructor():
    prompt = _build_prompt(
        "Show a warning banner whenever hoodies are low stock.",
        "show_low_stock_hoodie_banner",
        "",
    )

    assert 'ShowBanner(text: str, severity: "info" | "warning")' in prompt
    assert "ShowBanner uses text= for its message content." in prompt
    assert "Never use message= with ShowBanner." in prompt
    assert "match against sku.name as well as sku.category" in prompt
    assert "spring-wide-15-discount" in prompt
    assert "strikethrough and discounted detail-page prices" in prompt
