from rules._base import InventorySnapshot, SetVisibility, Sku
from rules.mark_any_hoodie_with_fewer_than_10_units_in_stock_with_a_low_stock_badge_on_the import RULE


def test_marks_low_stock_hoodies_with_low_stock_badge():
    snapshot = InventorySnapshot(
        skus=(
            Sku(
                sku="low-stock-hoodie",
                name="Cozy Hoodie",
                category="Men",
                price_cents=5500,
                stock_count=9,
            ),
            Sku(
                sku="full-stock-hoodie",
                name="Cozy Hoodie",
                category="Men",
                price_cents=5500,
                stock_count=10,
            ),
            Sku(
                sku="low-stock-shirt",
                name="Low Stock Tee",
                category="Basics",
                price_cents=2500,
                stock_count=5,
            ),
        )
    )

    assert RULE.evaluate(snapshot) == [SetVisibility(sku="low-stock-hoodie", state="low_stock_badge")]
