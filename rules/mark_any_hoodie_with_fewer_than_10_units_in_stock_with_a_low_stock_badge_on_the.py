from rules._base import InventorySnapshot, Rule, SetVisibility

LOW_STOCK_THRESHOLD = 10


def _is_hoodie(sku):
    name = (sku.name or "").lower()
    category = (sku.category or "").lower()
    return "hoodie" in name or "hoodie" in category


def evaluate(snapshot: InventorySnapshot):
    actions = []
    for sku in snapshot.skus:
        if _is_hoodie(sku) and sku.stock_count < LOW_STOCK_THRESHOLD:
            actions.append(SetVisibility(sku=sku.sku, state="low_stock_badge"))
    return actions


RULE = Rule(
    name="Mark low-stock hoodies",
    description="Marks hoodies with fewer than ten units in stock with a low-stock badge on the storefront and product detail pages.",
    evaluate=evaluate,
)
