from rules._base import InventorySnapshot, SetVisibility, Sku
from rules.example_clearance import LOW_STOCK_THRESHOLD, RULE


def test_example_clearance_marks_low_stock_skus():
    snapshot = InventorySnapshot(
        skus=(
            Sku(
                sku="low-stock-shirt",
                name="Low Stock Shirt",
                category="Basics",
                price_cents=2400,
                stock_count=LOW_STOCK_THRESHOLD,
            ),
            Sku(
                sku="stocked-shirt",
                name="Stocked Shirt",
                category="Basics",
                price_cents=2400,
                stock_count=LOW_STOCK_THRESHOLD + 1,
            ),
        )
    )

    assert RULE.evaluate(snapshot) == [SetVisibility(sku="low-stock-shirt", state="low_stock_badge")]
