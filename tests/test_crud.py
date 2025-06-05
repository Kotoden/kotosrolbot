import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from database.models import Base
from database.crud import (
    get_or_create_user,
    get_all_categories,
    create_category,
    get_products,
    create_product,
    update_product,
    delete_product,
    create_order,
    add_item_to_order,
    get_orders_by_user,
    get_order_details,
    update_order_status,
)
from database.models import User, Category, Product, Order, OrderItem


class TestCRUD(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", echo=False, future=True)
        Base.metadata.create_all(bind=self.engine)
        self.db = Session(self.engine)
        self.user = get_or_create_user(self.db, telegram_id=12345, username="testuser", full_name="Test User",
                                       is_admin=False)
        self.category = create_category(self.db, name="Electronics")
        self.product = create_product(self.db, name="Laptop", description="Gaming laptop", price=1000.0, quantity=5,
                                      category_id=self.category.id)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_get_or_create_user_creates(self) -> None:
        user2 = get_or_create_user(self.db, telegram_id=54321, username="another", full_name="Another User",
                                   is_admin=True)
        self.assertIsNotNone(user2.id)
        self.assertEqual(user2.telegram_id, 54321)
        self.assertTrue(user2.is_admin)

    def test_get_or_create_user_updates(self) -> None:
        old_id = self.user.id
        user_updated = get_or_create_user(self.db, telegram_id=12345, username="newname", full_name="New Name")
        self.assertEqual(user_updated.id, old_id)
        self.assertEqual(user_updated.username, "newname")
        self.assertEqual(user_updated.full_name, "New Name")

    def test_create_and_get_all_categories(self) -> None:
        cat2 = create_category(self.db, name="Books")
        cats = get_all_categories(self.db)
        names = [c.name for c in cats]
        self.assertIn("Electronics", names)
        self.assertIn("Books", names)
        self.assertEqual(len(cats), 2)

    def test_create_category_exists(self) -> None:
        with self.assertRaises(ValueError):
            create_category(self.db, name="Electronics")

    def test_get_products_all_and_by_category(self) -> None:
        all_products = get_products(self.db)
        self.assertEqual(len(all_products), 1)
        by_cat = get_products(self.db, category_id=self.category.id)
        self.assertEqual(len(by_cat), 1)

    def test_create_product_invalid_category(self) -> None:
        with self.assertRaises(ValueError):
            create_product(self.db, name="Phone", description="Smartphone", price=500.0, quantity=10, category_id=999)

    def test_update_product(self) -> None:
        updated = update_product(self.db, self.product.id, name="Laptop Pro", price=1200.0)
        self.assertEqual(updated.name, "Laptop Pro")
        self.assertEqual(updated.price, 1200.0)

    def test_update_product_invalid(self) -> None:
        with self.assertRaises(Exception):
            update_product(self.db, product_id=999, name="No", price=1.0)

    def test_delete_product(self) -> None:
        delete_product(self.db, self.product.id)
        prod = self.db.query(Product).filter(Product.id == self.product.id).one_or_none()
        self.assertIsNone(prod)

    def test_order_workflow(self) -> None:
        order = create_order(self.db, self.user.id)
        self.assertIsNotNone(order.id)
        item = add_item_to_order(self.db, order.id, self.product.id, quantity=2)
        self.assertEqual(item.quantity, 2)
        prod_after = self.db.query(Product).filter(Product.id == self.product.id).one()
        self.assertEqual(prod_after.quantity, 3)
        orders = get_orders_by_user(self.db, self.user.id)
        self.assertEqual(len(orders), 1)
        order_db, total = get_order_details(self.db, order.id)
        self.assertAlmostEqual(total, 2 * item.unit_price)
        updated_order = update_order_status(self.db, order.id, new_status="paid")
        self.assertEqual(updated_order.status, "paid")

    def test_add_item_insufficient_quantity(self) -> None:
        order = create_order(self.db, self.user.id)
        with self.assertRaises(ValueError):
            add_item_to_order(self.db, order.id, self.product.id, quantity=999)

    def test_add_item_invalid_order_or_product(self) -> None:
        with self.assertRaises(Exception):
            add_item_to_order(self.db, order_id=999, product_id=self.product.id, quantity=1)
        order = create_order(self.db, self.user.id)
        with self.assertRaises(Exception):
            add_item_to_order(self.db, order_id=order.id, product_id=999, quantity=1)


if __name__ == "__main__":
    unittest.main()
