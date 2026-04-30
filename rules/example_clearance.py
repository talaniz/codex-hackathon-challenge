from rules._base import InventorySnapshot, Rule, SetVisibility


LOW_STOCK_THRESHOLD = 10


def evaluate(snapshot: InventorySnapshot):
    actions = []
    for sku in snapshot.skus:
        if sku.stock_count <= LOW_STOCK_THRESHOLD:
            actions.append(SetVisibility(sku=sku.sku, state="low_stock_badge"))
    return actions


RULE = Rule(
    name="Example low stock badge",
    description="Marks products at or below the low-stock threshold with a storefront badge.",
    evaluate=evaluate,
)